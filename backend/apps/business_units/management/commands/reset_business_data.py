from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.projects.models import Project, ProjectAssignment
from apps.recruitment.models import Application


class Command(BaseCommand):
    help = "Affiche ou supprime les données métier réinitialisables sans toucher aux Super Admin."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Exécute réellement la suppression. Sans cette option, seul un aperçu est affiché.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        target_roles = [UserRole.EMPLOYEE, UserRole.BU_MANAGER, UserRole.CANDIDATE]
        users = User.objects.filter(role__in=target_roles, is_superuser=False).exclude(role=UserRole.SUPER_ADMIN)
        business_units = BusinessUnit.objects.all()
        applications = Application.objects.filter(
            Q(candidate_profile__user__in=users) | Q(offer__business_unit__in=business_units)
        ).distinct()
        projects = Project.objects.filter(business_unit__in=business_units)

        preview = {
            "Utilisateurs": users.count(),
            "Business Units": business_units.count(),
            "Adhésions": BusinessUnitMembership.objects.filter(business_unit__in=business_units).count(),
            "Besoins": BusinessUnitNeed.objects.filter(business_unit__in=business_units).count(),
            "Candidatures": applications.count(),
            "Projets": projects.count(),
            "Affectations": ProjectAssignment.objects.filter(project__in=projects).count(),
        }

        self.stdout.write(self.style.WARNING("Aperçu de la réinitialisation métier :"))
        for label, count in preview.items():
            self.stdout.write(f"- {label} : {count}")

        if not options["confirm"]:
            self.stdout.write(self.style.WARNING("Aucune donnée supprimée. Relancez avec --confirm pour confirmer."))
            return

        protected_ids = set(
            User.objects.filter(Q(is_superuser=True) | Q(role=UserRole.SUPER_ADMIN)).values_list("pk", flat=True)
        )

        with transaction.atomic():
            applications.delete()
            projects.delete()
            business_units.delete()
            users.delete()

            missing_protected = protected_ids.difference(User.objects.filter(pk__in=protected_ids).values_list("pk", flat=True))
            if missing_protected:
                raise CommandError("Protection des Super Admin violée ; transaction annulée.")

        self.stdout.write(self.style.SUCCESS("Réinitialisation métier terminée :"))
        for label, count in preview.items():
            self.stdout.write(f"- {label} supprimé(s) : {count}")
