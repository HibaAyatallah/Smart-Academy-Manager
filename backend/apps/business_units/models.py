from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.accounts.choices import UserRole
from .choices import (
    NeedPriority,
    NeedRequiredLevel,
    NeedStatus,
    NeedType,
    TrainingAudience,
)


class BusinessUnit(models.Model):
    name = models.CharField("Nom", max_length=255, unique=True)
    code = models.CharField("Code", max_length=50, unique=True)
    description = models.TextField("Description", blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Manager",
        related_name="managed_business_units",
        limit_choices_to={"role": UserRole.BU_MANAGER},
    )
    is_active = models.BooleanField("Actif", default=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis à jour le", auto_now=True)

    class Meta:
        verbose_name = "Business Unit"
        verbose_name_plural = "Business Units"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        # manager is optional (BU can exist without an assigned manager initially)
        if self.manager_id and (not self.manager.is_active or self.manager.role != UserRole.BU_MANAGER):
            raise ValidationError(
                {"manager": "Le manager assigné doit avoir le rôle BU_MANAGER."}
            )

        if self.manager_id and BusinessUnit.objects.filter(manager_id=self.manager_id, is_active=True).exclude(pk=self.pk).exists():
            raise ValidationError({"manager": "Ce manager possède déjà une BU active. Effectuez un transfert depuis la gestion utilisateur."})


class BusinessUnitMembership(models.Model):
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Business Unit",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bu_memberships",
        verbose_name="Utilisateur",
    )
    position = models.CharField("Poste", max_length=255, blank=True)
    joined_at = models.DateField("Date de rejoindre", default=timezone.localdate)
    is_active = models.BooleanField("Actif", default=True)
    active_uniqueness_key = models.GeneratedField(
        expression=models.Case(
            models.When(is_active=True, then=models.Value(1)),
            default=models.Value(None),
        ),
        output_field=models.IntegerField(null=True),
        db_persist=True,
    )

    class Meta:
        verbose_name = "Membre de Business Unit"
        verbose_name_plural = "Membres de Business Unit"
        constraints = [
            models.UniqueConstraint(
                fields=["business_unit", "user", "active_uniqueness_key"],
                name="unique_active_bu_membership",
            ),
        ]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user.email} - {self.business_unit.code}"

    def clean(self):
        if self.is_active and self.user_id and self.user.role == UserRole.BU_MANAGER:
            raise ValidationError({"user": "Le manager est affecté via BusinessUnit.manager, pas via une appartenance classique."})
        if self.is_active and self.business_unit_id and self.user_id:
            if not self.business_unit.is_active:
                raise ValidationError({"business_unit": "La Business Unit doit être active."})
            if BusinessUnitMembership.objects.filter(user_id=self.user_id, is_active=True).exclude(pk=self.pk).exists():
                raise ValidationError({"user": "Cet utilisateur possède déjà une appartenance active."})
            # Check for duplicate active membership in the same Business Unit
            if BusinessUnitMembership.objects.filter(
                business_unit_id=self.business_unit_id,
                user_id=self.user_id,
                is_active=True,
            ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    "Cet utilisateur est déjà membre actif de cette Business Unit."
                )


class BusinessUnitNeed(models.Model):
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        related_name="needs",
        verbose_name="Business Unit",
    )
    title = models.CharField("Titre du besoin", max_length=255)
    description = models.TextField("Description")
    need_type = models.CharField(
        "Type de besoin",
        max_length=50,
        choices=NeedType.choices,
        default=NeedType.RECRUITMENT_INTERNSHIP,
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_business_unit_needs",
        verbose_name="Demandeur",
    )
    training_audience = models.CharField(
        "Public cible",
        max_length=20,
        choices=TrainingAudience.choices,
        default=TrainingAudience.ALL,
    )
    training_recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="targeted_bu_trainings",
        verbose_name="Collaborateurs ciblés",
    )
    required_skills = models.TextField("Compétences requises", blank=True)
    required_level = models.CharField(
        "Niveau requis",
        max_length=50,
        choices=NeedRequiredLevel.choices,
        default=NeedRequiredLevel.MID,
    )
    number_of_profiles = models.PositiveIntegerField("Nombre de profils", default=1)
    priority = models.CharField(
        "Priorité",
        max_length=50,
        choices=NeedPriority.choices,
        default=NeedPriority.MEDIUM,
    )
    expected_date = models.DateField("Date attendue", null=True, blank=True)
    training_start_date = models.DateField("Début de la formation", null=True, blank=True)
    training_end_date = models.DateField("Fin de la formation", null=True, blank=True)
    training_link = models.URLField("Lien de la formation", blank=True)
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_bu_trainings",
        limit_choices_to={"role": UserRole.TRAINER_TUTOR},
        verbose_name="Formateur",
    )
    status = models.CharField(
        "Statut",
        max_length=50,
        choices=NeedStatus.choices,
        default=NeedStatus.SUBMITTED,
    )
    decision_comment = models.TextField("Commentaire de décision", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_bu_needs",
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis à jour le", auto_now=True)

    class Meta:
        verbose_name = "Besoin de Business Unit"
        verbose_name_plural = "Besoins de Business Unit"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.business_unit.code}] {self.title} - {self.get_status_display()}"


class BusinessUnitNeedHistory(models.Model):
    need = models.ForeignKey(
        BusinessUnitNeed,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="Besoin",
    )
    from_status = models.CharField("Statut précédent", max_length=50, blank=True)
    to_status = models.CharField("Nouveau statut", max_length=50)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Modifié par",
    )
    comment = models.TextField("Commentaire", blank=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        verbose_name = "Historique du besoin"
        verbose_name_plural = "Historiques des besoins"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.need.title}: {self.from_status} -> {self.to_status}"
