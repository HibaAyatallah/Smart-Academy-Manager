from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership


User = get_user_model()


class BusinessUnitAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@test.com", password="pwd", role=UserRole.SUPER_ADMIN
        )
        self.manager = User.objects.create_user(
            email="manager@test.com", password="pwd", role=UserRole.BU_MANAGER
        )
        self.employee = User.objects.create_user(
            email="employee@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        self.client.force_login(self.admin_user)

    @staticmethod
    def _inline_management_data():
        return {
            "memberships-TOTAL_FORMS": "0",
            "memberships-INITIAL_FORMS": "0",
            "memberships-MIN_NUM_FORMS": "0",
            "memberships-MAX_NUM_FORMS": "1000",
            "needs-TOTAL_FORMS": "0",
            "needs-INITIAL_FORMS": "0",
            "needs-MIN_NUM_FORMS": "0",
            "needs-MAX_NUM_FORMS": "1000",
        }

    def _business_unit_data(self, **overrides):
        data = {
            "name": "Admin BU",
            "code": "ADMIN_BU",
            "description": "Created from Django Admin",
            "manager": str(self.manager.pk),
            "is_active": "on",
            **self._inline_management_data(),
        }
        data.update(overrides)
        return data

    def test_admin_can_create_business_unit_with_manager(self):
        response = self.client.post(
            reverse("admin:business_units_businessunit_add"),
            self._business_unit_data(),
        )

        self.assertEqual(response.status_code, 302)
        business_unit = BusinessUnit.objects.get(code="ADMIN_BU")
        self.assertEqual(business_unit.manager, self.manager)

    def test_admin_can_update_business_unit(self):
        business_unit = BusinessUnit.objects.create(
            name="Existing BU", code="EXISTING", manager=self.manager
        )

        response = self.client.post(
            reverse(
                "admin:business_units_businessunit_change", args=[business_unit.pk]
            ),
            self._business_unit_data(name="Updated BU", code=business_unit.code),
        )

        self.assertEqual(response.status_code, 302)
        business_unit.refresh_from_db()
        self.assertEqual(business_unit.name, "Updated BU")

    def test_admin_creation_without_manager_returns_form_error(self):
        response = self.client.post(
            reverse("admin:business_units_businessunit_add"),
            self._business_unit_data(manager=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("manager", response.context["adminform"].form.errors)
        self.assertFalse(BusinessUnit.objects.filter(code="ADMIN_BU").exists())

    def test_admin_inline_creates_one_active_membership(self):
        data = self._business_unit_data(
            **{
                "memberships-0-user": str(self.employee.pk),
                "memberships-TOTAL_FORMS": "1",
                "memberships-0-position": "Developer",
                "memberships-0-joined_at": "2026-07-15",
                "memberships-0-is_active": "on",
            }
        )
        response = self.client.post(
            reverse("admin:business_units_businessunit_add"), data
        )

        self.assertEqual(response.status_code, 302)
        business_unit = BusinessUnit.objects.get(code="ADMIN_BU")
        self.assertEqual(
            BusinessUnitMembership.objects.filter(
                business_unit=business_unit,
                user=self.employee,
                is_active=True,
            ).count(),
            1,
        )
