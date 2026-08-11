from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.projects.models import Project, ProjectAssignment
from apps.recruitment.choices import ApplicationType
from apps.recruitment.models import Application, CandidateProfile, Offer


User = get_user_model()


class ResetBusinessDataCommandTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(email="root-reset@test.com", password="test")
        self.role_admin = User.objects.create_user(
            email="admin-reset@test.com", password="test", role=UserRole.SUPER_ADMIN
        )
        self.manager = User.objects.create_user(
            email="manager-reset@test.com", password="test", role=UserRole.BU_MANAGER
        )
        self.employee = User.objects.create_user(
            email="employee-reset@test.com", password="test", role=UserRole.EMPLOYEE
        )
        self.candidate = User.objects.create_user(
            email="candidate-reset@test.com", password="test", role=UserRole.CANDIDATE
        )
        self.business_unit = BusinessUnit.objects.create(
            name="BU à réinitialiser", code="RESET", manager=self.manager
        )
        BusinessUnitMembership.objects.create(business_unit=self.business_unit, user=self.employee)
        BusinessUnitNeed.objects.create(
            business_unit=self.business_unit,
            title="Besoin test",
            description="À supprimer",
            created_by=self.manager,
        )
        offer = Offer.objects.create(
            title="Offre test",
            description="À supprimer",
            business_unit=self.business_unit,
            application_type=ApplicationType.HIRING,
            created_by=self.role_admin,
        )
        profile = CandidateProfile.objects.create(user=self.candidate)
        Application.objects.create(
            candidate_profile=profile,
            offer=offer,
            application_type=ApplicationType.HIRING,
        )
        project = Project.objects.create(
            title="Projet test",
            description="À supprimer",
            business_unit=self.business_unit,
            supervisor=self.manager,
            created_by=self.role_admin,
        )
        ProjectAssignment.objects.create(project=project, user=self.employee)

    def test_default_mode_only_displays_preview(self):
        output = StringIO()

        call_command("reset_business_data", stdout=output)

        self.assertIn("Aucune donnée supprimée", output.getvalue())
        self.assertTrue(BusinessUnit.objects.filter(pk=self.business_unit.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.employee.pk).exists())

    def test_confirm_deletes_business_data_and_preserves_all_super_admins(self):
        output = StringIO()

        call_command("reset_business_data", confirm=True, stdout=output)

        self.assertFalse(BusinessUnit.objects.exists())
        self.assertFalse(User.objects.filter(pk__in=[self.manager.pk, self.employee.pk, self.candidate.pk]).exists())
        self.assertFalse(Application.objects.exists())
        self.assertFalse(ProjectAssignment.objects.exists())
        self.assertTrue(User.objects.filter(pk=self.superuser.pk, is_superuser=True).exists())
        self.assertTrue(User.objects.filter(pk=self.role_admin.pk, role=UserRole.SUPER_ADMIN).exists())
        self.assertIn("Utilisateurs supprimé(s) : 3", output.getvalue())
