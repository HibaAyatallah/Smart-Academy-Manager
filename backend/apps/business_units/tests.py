from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.business_units.choices import NeedType, NeedPriority, NeedStatus

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

    def test_superadmin_can_see_all_bus(self):
        """SuperAdmin can see all BUs"""
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get(reverse("business-unit-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_hr_can_see_bu_list_and_is_read_only(self):
        """HR has read-only access to standard BU endpoints"""
        self.client.force_authenticate(user=self.hr)
        # HR can GET list
        response = self.client.get(reverse("business-unit-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # HR is blocked from creating
        create_response = self.client.post(
            reverse("business-unit-list"),
            {"name": "HR Created BU", "code": "HRC", "manager": self.manager1.id},
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

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

    def test_hr_is_read_only_on_bu_endpoints(self):
        """HR can retrieve BU details but cannot update or delete them"""
        self.client.force_authenticate(user=self.hr)
        detail_url = reverse("business-unit-detail", args=[self.bu1.id])
        # Can read detail
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Cannot update
        patch_response = self.client.patch(detail_url, {"name": "HR Mod BU"})
        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)
        # Cannot delete
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

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

    # === BU Manager Protection Tests ===

    def test_hr_cannot_reassign_manager(self):
        """HR cannot reassign a Business Unit manager"""
        self.client.force_authenticate(user=self.hr)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"manager": self.manager2.id},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.bu1.refresh_from_db()
        self.assertEqual(self.bu1.manager, self.manager1)

    def test_super_admin_can_reassign_manager(self):
        """Super Admin can reassign a Business Unit manager"""
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"manager": self.manager2.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bu1.refresh_from_db()
        self.assertEqual(self.bu1.manager, self.manager2)

    def test_manager_cannot_reassign_own_bu_to_another_manager(self):
        """BU Manager cannot reassign their own BU to a different manager"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"manager": self.manager2.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.bu1.refresh_from_db()
        self.assertEqual(self.bu1.manager, self.manager1)

    def test_manager_cannot_remove_manager_from_own_bu(self):
        """BU Manager cannot remove or nullify the manager field"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"manager": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.bu1.refresh_from_db()
        self.assertEqual(self.bu1.manager, self.manager1)

    def test_manager_cannot_change_code(self):
        """BU Manager cannot change the code of their own BU"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"code": "HACKED"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.bu1.refresh_from_db()
        self.assertEqual(self.bu1.code, "BU1")

    def test_manager_cannot_deactivate_own_bu(self):
        """BU Manager cannot deactivate their own BU"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"is_active": False},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.bu1.refresh_from_db()
        self.assertTrue(self.bu1.is_active)

    def test_manager_cannot_modify_other_bu(self):
        """BU Manager cannot modify another BU's data"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu2.id]),
            {"name": "Hacked BU"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_update_own_bu_description(self):
        """BU Manager can update allowed fields on their own BU"""
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-detail", args=[self.bu1.id]),
            {"description": "Nouvelle description"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bu1.refresh_from_db()
        self.assertEqual(self.bu1.description, "Nouvelle description")

    def test_manager_can_create_training_request_for_own_member(self):
        self.client.force_authenticate(user=self.manager1)
        response = self.client.post(
            reverse("business-unit-need-list"),
            {
                "business_unit": self.bu1.id,
                "title": "Formation Angular",
                "description": "Perfectionnement",
                "need_type": NeedType.TRAINING,
                "requester": self.employee1.id,
                "priority": NeedPriority.HIGH,
                "expected_date": "2026-09-01",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], NeedStatus.SUBMITTED)

    def test_manager_cannot_select_collaborator_from_another_bu(self):
        outsider = User.objects.create_user(
            email="outsider@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        BusinessUnitMembership.objects.create(business_unit=self.bu2, user=outsider)
        self.client.force_authenticate(user=self.manager1)
        response = self.client.post(
            reverse("business-unit-need-list"),
            {
                "business_unit": self.bu1.id,
                "title": "Formation",
                "description": "Test",
                "need_type": NeedType.TRAINING,
                "requester": outsider.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_cannot_complete_training_organization(self):
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            reverse("business-unit-need-detail", args=[self.need1.id]),
            {"training_link": "https://example.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test manager cannot transition via accept endpoint
        response = self.client.post(
            f"/api/business-unit-needs/{self.need1.id}/accept/", {}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_can_complete_and_validate_training(self):
        trainer = User.objects.create_user(
            email="trainer@test.com", password="pwd", role=UserRole.TRAINER_TUTOR
        )
        training = BusinessUnitNeed.objects.create(
            business_unit=self.bu1,
            title="Formation Python",
            description="Demande manager",
            need_type=NeedType.TRAINING,
            status=NeedStatus.SUBMITTED,
            created_by=self.manager1,
        )
        self.client.force_authenticate(user=self.superadmin)
        # Patch the details
        patch_response = self.client.patch(
            reverse("business-unit-need-detail", args=[training.id]),
            {
                "training_start_date": "2026-09-10",
                "training_end_date": "2026-09-12",
                "training_link": "https://example.com/training",
                "trainer": trainer.id,
            },
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        
        # Transition via accept endpoint
        response = self.client.post(
            f"/api/business-unit-needs/{training.id}/accept/",
            {"comment": "Formation approuvée."},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["trainer"], trainer.id)
        self.assertEqual(response.data["status"], NeedStatus.ACCEPTED)

    def test_employee_sees_only_validated_training_from_own_bu(self):
        visible = BusinessUnitNeed.objects.create(
            business_unit=self.bu1,
            title="Formation validée",
            description="Visible",
            need_type=NeedType.TRAINING,
            status=NeedStatus.ACCEPTED,
            created_by=self.superadmin,
        )
        BusinessUnitNeed.objects.create(
            business_unit=self.bu1,
            title="Formation brouillon",
            description="Masquée",
            need_type=NeedType.TRAINING,
            status=NeedStatus.SUBMITTED,
            created_by=self.superadmin,
        )
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get(reverse("business-unit-need-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data["results"]], [visible.id])

    def test_manager_can_add_and_remove_existing_employee_from_own_bu(self):
        employee = User.objects.create_user(
            email="new-member@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        self.client.force_authenticate(user=self.manager1)
        create_response = self.client.post(
            reverse("business-unit-membership-list"),
            {"business_unit": self.bu1.id, "member_email": employee.email, "position": "QA"},
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)
        membership = BusinessUnitMembership.objects.get(
            business_unit=self.bu1, user=employee
        )

        delete_response = self.client.delete(
            reverse("business-unit-membership-detail", args=[membership.id])
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)

    def test_manager_cannot_add_member_to_another_bu(self):
        employee = User.objects.create_user(
            email="other-member@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        self.client.force_authenticate(user=self.manager1)
        response = self.client.post(
            reverse("business-unit-membership-list"),
            {"business_unit": self.bu2.id, "member_email": employee.email},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(BusinessUnitMembership.objects.filter(user=employee).exists())

    def test_manager_cannot_add_non_employee_account(self):
        self.client.force_authenticate(user=self.manager1)
        response = self.client.post(
            reverse("business-unit-membership-list"),
            {"business_unit": self.bu1.id, "member_email": self.candidate.email},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_specific_training_is_visible_only_to_selected_members(self):
        employee2 = User.objects.create_user(
            email="emp2-visible@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        BusinessUnitMembership.objects.create(business_unit=self.bu1, user=employee2)
        training = BusinessUnitNeed.objects.create(
            business_unit=self.bu1,
            title="Formation ciblée",
            description="Ciblée",
            need_type=NeedType.TRAINING,
            training_audience="SPECIFIC",
            status=NeedStatus.ACCEPTED,
            created_by=self.superadmin,
        )
        training.training_recipients.add(self.employee1)

        self.client.force_authenticate(user=self.employee1)
        selected_response = self.client.get(reverse("business-unit-need-list"))
        self.assertIn(training.id, [item["id"] for item in selected_response.data["results"]])

        self.client.force_authenticate(user=employee2)
        other_response = self.client.get(reverse("business-unit-need-list"))
        self.assertNotIn(training.id, [item["id"] for item in other_response.data["results"]])

    def test_specific_training_rejects_email_outside_business_unit(self):
        self.client.force_authenticate(user=self.manager1)
        response = self.client.post(
            reverse("business-unit-need-list"),
            {
                "business_unit": self.bu1.id,
                "title": "Formation ciblée",
                "description": "Test",
                "need_type": NeedType.TRAINING,
                "training_audience": "SPECIFIC",
                "specific_recipient_emails": ["outsider@example.com"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_superadmin_refusal_is_supported_via_reject_endpoint(self):
        self.client.force_authenticate(user=self.superadmin)
        training = BusinessUnitNeed.objects.create(
            business_unit=self.bu1,
            title="Formation Refused",
            description="Demande",
            need_type=NeedType.TRAINING,
            status=NeedStatus.SUBMITTED,
            created_by=self.manager1,
        )
        response = self.client.post(
            f"/api/business-unit-needs/{training.id}/reject/",
            {"comment": "Refusé pour l'instant"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], NeedStatus.REJECTED)


class BusinessUnitMembershipTests(APITestCase):
    """Tests for membership history constraint changes"""

    def setUp(self):
        self.hr = User.objects.create_user(
            email="hr@test.com", password="pwd", role=UserRole.HR
        )
        self.manager = User.objects.create_user(
            email="mgr@test.com", password="pwd", role=UserRole.BU_MANAGER
        )
        self.employee = User.objects.create_user(
            email="emp@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        self.bu = BusinessUnit.objects.create(
            name="Test BU", code="TBU", manager=self.manager
        )

    def test_duplicate_active_membership_rejected(self):
        """Creating a second active membership for the same user/BU is rejected"""
        BusinessUnitMembership.objects.create(
            business_unit=self.bu, user=self.employee, is_active=True
        )
        with self.assertRaises(Exception):
            BusinessUnitMembership.objects.create(
                business_unit=self.bu, user=self.employee, is_active=True
            )

    def test_inactive_historical_membership_preserved(self):
        """Creating an inactive membership does not affect existing inactive history"""
        membership = BusinessUnitMembership.objects.create(
            business_unit=self.bu, user=self.employee, is_active=True
        )
        membership.is_active = False
        membership.save()
        # Still one membership record
        self.assertEqual(BusinessUnitMembership.objects.count(), 1)
        self.assertEqual(BusinessUnitMembership.objects.first().is_active, False)

    def test_user_can_rejoin_after_inactive(self):
        """A user can rejoin a BU after their previous membership becomes inactive"""
        membership = BusinessUnitMembership.objects.create(
            business_unit=self.bu, user=self.employee, is_active=True
        )
        membership.is_active = False
        membership.save()

        # Rejoin
        new_membership = BusinessUnitMembership.objects.create(
            business_unit=self.bu, user=self.employee, is_active=True
        )
        self.assertTrue(new_membership.is_active)
        self.assertEqual(BusinessUnitMembership.objects.count(), 2)

    def test_unrelated_memberships_unaffected(self):
        """Creating memberships for different BUs or users works normally"""
        bu2 = BusinessUnit.objects.create(
            name="BU 2", code="BU2", manager=self.manager
        )
        employee2 = User.objects.create_user(
            email="emp2@test.com", password="pwd", role=UserRole.EMPLOYEE
        )

        m1 = BusinessUnitMembership.objects.create(
            business_unit=self.bu, user=self.employee, is_active=True
        )
        m2 = BusinessUnitMembership.objects.create(
            business_unit=bu2, user=self.employee, is_active=True
        )
        m3 = BusinessUnitMembership.objects.create(
            business_unit=self.bu, user=employee2, is_active=True
        )

        self.assertTrue(m1.is_active)
        self.assertTrue(m2.is_active)
        self.assertTrue(m3.is_active)
