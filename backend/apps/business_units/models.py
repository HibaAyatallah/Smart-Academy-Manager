from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.accounts.choices import UserRole
from .choices import NeedPriority, NeedRequiredLevel, NeedStatus, NeedType, TrainingAudience


class BusinessUnit(models.Model):
    name = models.CharField("Nom", max_length=255, unique=True)
    code = models.CharField("Code", max_length=50, unique=True)
    description = models.TextField("Description", blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
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
        if self.manager_id and self.manager.role != UserRole.BU_MANAGER:
            raise ValidationError(
                {"manager": "Le manager assigné doit avoir le rôle BU_MANAGER."}
            )


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
    joined_at = models.DateField("Date de rejoindre", default=timezone.now)
    is_active = models.BooleanField("Actif", default=True)

    class Meta:
        verbose_name = "Membre de Business Unit"
        verbose_name_plural = "Membres de Business Unit"
        constraints = [
            models.UniqueConstraint(
                fields=["business_unit", "user"],
                condition=models.Q(is_active=True),
                name="unique_active_bu_membership",
            ),
        ]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user.email} - {self.business_unit.code}"

    def clean(self):
        if self.is_active and self.business_unit_id and self.user_id:
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
        on_delete=models.PROTECT,
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
