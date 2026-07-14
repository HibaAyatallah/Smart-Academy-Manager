from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.business_units.choices import NeedType, NeedRequiredLevel, NeedPriority, NeedStatus

User = get_user_model()


class BusinessUnitTests(APITestCase):
    def setUp(self):
        self.superadmin = User.objects.create_user(
            email="super@test.com", password="pwd", role=UserRole.SUPER_ADMIN
        )
        self.hr = User.objects.create_user(
            email="hr@test.com", password="pwd", role=UserRole.HR
        )
        self.manager1 = User.objects.create_user(
            email="mgr1@test.com", password="pwd", role=UserRole.BU_MANAGER
        )
        self.manager2 = User.objects.create_user(
            email="mgr2@test.com", password="pwd", role=UserRole.BU_MANAGER
        )
        self.employee1 = User.objects.create_user(
            email="emp1@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        self.candidate = User.objects.create_user(
            email="cand@test.com", password="pwd", role=UserRole.CANDIDATE
        )

        self.bu1 = BusinessUnit.objects.create(name="BU 1", code="BU1", manager=self.manager1)
        self.bu2 = BusinessUnit.objects.create(name="BU 2", code="BU2", manager=self.manager2)

        self.membership1 = BusinessUnitMembership.objects.create(
            business_unit=self.bu1, user=self.employee1, position="Developer"
        )
        self.need1 = BusinessUnitNeed.objects.create(
            business_unit=self.bu1,
            title="Need Dev",
            description="Dev desc",
            created_by=self.manager1,
        )

    def test_manager_must_have_bu_manager_role(self):
        """Test model validation for manager role"""
        bu_invalid = BusinessUnit(name="BU Invalid", code="BU_INV", manager=self.employee1)
        with self.assertRaises(ValidationError):
            bu_invalid.clean()

    def test_unique_name_and_code(self):
        """Test unique constraints for BU"""
        with self.assertRaises(Exception):
            BusinessUnit.objects.create(name="BU 1", code="BU3", manager=self.manager1)
        with self.assertRaises(Exception):
            BusinessUnit.objects.create(name="BU 3", code="BU1", manager=self.manager1)

    def test_hr_can_see_all_bus(self):
        """HR/SuperAdmin can see all BUs"""
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(reverse("business-unit-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_manager_can_see_only_own_bu(self):
        """Manager can only see their own BU"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.get(reverse("business-unit-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["code"], "BU1")

    def test_employee_can_see_own_bu_memberships(self):
        """Collaborator can see BUs they are members of"""
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get(reverse("business-unit-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["code"], "BU1")

    def test_candidate_cannot_access_bu(self):
        """Candidate has no access to BU data"""
        self.client.force_authenticate(user=self.candidate)
        response = self.client.get(reverse("business-unit-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_edit_other_bu(self):
        """Manager cannot edit BU they don't own"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu2.id]),
            {"name": "Hacked BU"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Because of get_queryset filtering

    def test_manager_cannot_reassign_own_bu(self):
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"manager": self.manager2.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.bu1.refresh_from_db()
        self.assertEqual(self.bu1.manager, self.manager1)

    def test_manager_cannot_create_or_delete_business_units(self):
        self.client.force_authenticate(user=self.manager1)
        create_response = self.client.post(
            reverse("business-unit-list"),
            {"name": "Unauthorized", "code": "NOPE", "manager": self.manager1.id},
        )
        delete_response = self.client.delete(
            reverse("business-unit-detail", args=[self.bu1.id])
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_and_super_admin_have_equivalent_bu_access(self):
        self.client.force_authenticate(user=self.hr)
        hr_response = self.client.get(reverse("business-unit-list"))
        self.client.force_authenticate(user=self.superadmin)
        admin_response = self.client.get(reverse("business-unit-list"))
        self.assertEqual(hr_response.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(hr_response.data, admin_response.data)

    def test_create_bu_need(self):
        """Test creating a BU Need"""
        self.client.force_authenticate(user=self.manager1)
        data = {
            "business_unit": self.bu1.id,
            "title": "New Need",
            "description": "Desc",
        }
        response = self.client.post(reverse("business-unit-need-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BusinessUnitNeed.objects.count(), 2)
        self.assertEqual(BusinessUnitNeed.objects.get(id=response.data["id"]).created_by, self.manager1)

    def test_manager_cannot_create_need_for_other_bu(self):
        """Test manager cannot create need for another BU"""
        self.client.force_authenticate(user=self.manager1)
        data = {
            "business_unit": self.bu2.id,
            "title": "Hack Need",
            "description": "Desc",
        }
        response = self.client.post(reverse("business-unit-need-list"), data)
        # Should be forbidden/validation error because bu2 is not in their queryset
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
