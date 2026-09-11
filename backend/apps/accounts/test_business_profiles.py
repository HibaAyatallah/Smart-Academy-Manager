from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.notifications.models import AuditLog
from apps.recruitment.models import InternProfile, EmployeeProfile, CandidateProfile
from apps.trainings.models import ClientProfile


class BusinessProfileConsistencyTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="bu-admin@test.com", role="SUPER_ADMIN")
        self.a = BusinessUnit.objects.create(name="NetSEC", code="NetSEC")
        self.b = BusinessUnit.objects.create(name="Software", code="Software")
        self.supervisor = User.objects.create_user(email="supervisor@test.com", role="EMPLOYEE")
        BusinessUnitMembership.objects.create(user=self.supervisor, business_unit=self.a)
        self.other = User.objects.create_user(email="other-supervisor@test.com", role="TRAINER_TUTOR")
        BusinessUnitMembership.objects.create(user=self.other, business_unit=self.b)
        self.intern = User.objects.create_user(email="intern@test.com", role="INTERN")
        self.profile = InternProfile.objects.create(user=self.intern, business_unit=self.a, supervisor=self.supervisor)
        self.membership = BusinessUnitMembership.objects.create(user=self.intern, business_unit=self.a)
        self.client.force_authenticate(self.admin)

    def patch_user(self, user, data):
        return self.client.patch(f"/api/users/{user.pk}/", data, format="json")

    def patch_intern(self, data):
        return self.client.patch(f"/api/interns/{self.profile.pk}/", data, format="json")

    def assert_intern_bu(self, unit, supervisor):
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.business_unit_id, getattr(unit, "pk", None))
        self.assertEqual(self.profile.supervisor_id, getattr(supervisor, "pk", None))
        self.assertEqual(list(self.intern.bu_memberships.filter(is_active=True).values_list("business_unit_id", flat=True)), [unit.pk] if unit else [])

    def test_user_transfer_rejects_foreign_supervisor_without_partial_changes(self):
        response = self.patch_user(self.intern, {"business_unit_id": self.b.pk, "first_name": "Must rollback"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("supervisor", response.data)
        self.assert_intern_bu(self.a, self.supervisor)
        self.intern.refresh_from_db()
        self.assertEqual(self.intern.first_name, "")
        self.assertFalse(AuditLog.objects.filter(action="USER_BUSINESS_UNIT_CHANGED").exists())

    def test_user_transfer_without_supervisor_and_audit(self):
        self.profile.supervisor = None
        self.profile.save(update_fields=["supervisor"])
        response = self.patch_user(self.intern, {"business_unit_id": self.b.pk})
        self.assertEqual(response.status_code, 200)
        self.assert_intern_bu(self.b, None)
        log = AuditLog.objects.get(action="USER_BUSINESS_UNIT_CHANGED")
        self.assertEqual(log.actor_id, self.admin.pk)
        self.assertEqual(log.target_id, str(self.intern.pk))
        self.assertEqual(log.metadata["old_business_unit"]["id"], self.a.pk)
        self.assertEqual(log.metadata["new_business_unit"]["id"], self.b.pk)

    def test_intern_endpoint_transfer_synchronizes_membership_and_history(self):
        original_date = self.membership.joined_at
        response = self.patch_intern({"business_unit": self.b.pk, "supervisor": self.other.pk})
        self.assertEqual(response.status_code, 200)
        self.assert_intern_bu(self.b, self.other)
        self.membership.refresh_from_db()
        self.assertFalse(self.membership.is_active)
        self.assertEqual(self.membership.joined_at, original_date)
        self.assertEqual(self.membership.business_unit_id, self.a.pk)
        self.assertEqual(AuditLog.objects.get(action="USER_BUSINESS_UNIT_CHANGED").target_id, str(self.intern.pk))

    def test_intern_transfer_without_replacement_is_rejected(self):
        self.assertEqual(self.patch_intern({"business_unit": self.b.pk}).status_code, 400)
        self.assert_intern_bu(self.a, self.supervisor)

    def test_absent_bu_and_unchanged_role_preserve_assignment(self):
        self.assertEqual(self.patch_user(self.intern, {"role": "INTERN"}).status_code, 200)
        self.assert_intern_bu(self.a, self.supervisor)
        self.assertFalse(AuditLog.objects.filter(action="USER_BUSINESS_UNIT_CHANGED").exists())

    def test_explicit_null_requires_detached_supervisor(self):
        self.assertEqual(self.patch_user(self.intern, {"business_unit_id": None}).status_code, 400)
        self.assertEqual(self.patch_intern({"supervisor": None}).status_code, 200)
        self.assertEqual(self.patch_user(self.intern, {"business_unit_id": None}).status_code, 200)
        self.assert_intern_bu(None, None)

    def test_rejoin_preserves_inactive_periods(self):
        self.patch_intern({"business_unit": self.b.pk, "supervisor": self.other.pk})
        response = self.patch_intern({"business_unit": self.a.pk, "supervisor": self.supervisor.pk})
        self.assertEqual(response.status_code, 200)
        self.assert_intern_bu(self.a, self.supervisor)
        self.membership.refresh_from_db()
        self.assertFalse(self.membership.is_active)
        self.assertEqual(self.intern.bu_memberships.count(), 3)

    def test_supervisor_role_change_and_deactivation_are_rejected(self):
        for payload in [{"role": "HR"}, {"is_active": False}, {"business_unit_id": self.b.pk}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.patch_user(self.supervisor, payload).status_code, 400)
        self.supervisor.refresh_from_db()
        self.assertTrue(self.supervisor.is_active)
        self.assertEqual(self.supervisor.role, "EMPLOYEE")

    def test_supervisor_api_rejects_inactive_wrong_role_and_other_bu(self):
        inactive = User.objects.create_user(email="inactive-supervisor@test.com", role="EMPLOYEE", is_active=False)
        BusinessUnitMembership.objects.create(user=inactive, business_unit=self.a)
        for user in [inactive, self.admin, self.other]:
            with self.subTest(user=user.email):
                self.assertEqual(self.patch_intern({"supervisor": user.pk}).status_code, 400)
        self.assert_intern_bu(self.a, self.supervisor)

    def test_manager_transfer_uses_manager_relation_without_membership(self):
        manager = User.objects.create_user(email="manager@test.com", role="BU_MANAGER")
        self.a.manager = manager
        self.a.save()
        self.assertEqual(self.patch_user(manager, {"business_unit_id": self.b.pk}).status_code, 200)
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertIsNone(self.a.manager_id)
        self.assertEqual(self.b.manager_id, manager.pk)
        self.assertFalse(manager.bu_memberships.filter(is_active=True).exists())
        self.assertEqual(BusinessUnit.objects.filter(manager=manager).count(), 1)

    def test_manager_assignment_from_bu_endpoint_also_transfers(self):
        manager = User.objects.create_user(email="direct-manager@test.com", role="BU_MANAGER")
        self.a.manager = manager; self.a.save()
        response = self.client.patch(f"/api/business-units/{self.b.pk}/", {"manager": manager.pk}, format="json")
        self.assertEqual(response.status_code, 200)
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertIsNone(self.a.manager_id)
        self.assertEqual(self.b.manager_id, manager.pk)

    def test_role_change_preserves_bu_and_moves_operational_relation(self):
        employee = User.objects.create_user(email="promoted@test.com", role="EMPLOYEE")
        BusinessUnitMembership.objects.create(user=employee, business_unit=self.b)
        self.assertEqual(self.patch_user(employee, {"role": "BU_MANAGER"}).status_code, 200)
        self.b.refresh_from_db()
        self.assertEqual(self.b.manager_id, employee.pk)
        self.assertFalse(employee.bu_memberships.filter(is_active=True).exists())
        self.assertEqual(self.patch_user(employee, {"role": "TRAINER_TUTOR"}).status_code, 200)
        self.b.refresh_from_db()
        self.assertIsNone(self.b.manager_id)
        self.assertEqual(employee.bu_memberships.filter(is_active=True).get().business_unit_id, self.b.pk)

    def test_membership_endpoint_refuses_second_bu(self):
        response = self.client.post("/api/business-unit-memberships/", {"user": self.supervisor.pk, "business_unit": self.b.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.supervisor.bu_memberships.filter(is_active=True).count(), 1)

    def test_removing_supervisor_membership_is_rejected(self):
        membership = self.supervisor.bu_memberships.get()
        self.assertEqual(self.client.delete(f"/api/business-unit-memberships/{membership.pk}/").status_code, 400)
        membership.refresh_from_db()
        self.assertTrue(membership.is_active)

    def test_client_creation_creates_usable_minimal_profile(self):
        response = self.client.post("/api/users/", {"email": "new-client@test.com", "password": "StrongPass123!", "role": "CLIENT"}, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(pk=response.data["id"])
        self.assertTrue(ClientProfile.objects.filter(user=user).exists())
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/client/trainings/").status_code, 200)

    def test_client_role_change_requires_explicit_bu_detachment(self):
        self.assertEqual(self.patch_user(self.other, {"role": "CLIENT"}).status_code, 400)
        self.assertFalse(ClientProfile.objects.filter(user=self.other).exists())
        self.assertEqual(self.patch_user(self.other, {"role": "CLIENT", "business_unit_id": None}).status_code, 200)
        self.assertTrue(ClientProfile.objects.filter(user=self.other).exists())
        self.assertFalse(self.other.bu_memberships.filter(is_active=True).exists())

    def test_direct_intern_creation_and_role_change_without_profile_are_refused(self):
        response = self.client.post("/api/users/", {"email": "invalid-intern@test.com", "password": "StrongPass123!", "role": "INTERN"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("role", response.data)
        self.assertFalse(User.objects.filter(email="invalid-intern@test.com").exists())
        self.assertEqual(self.patch_user(self.other, {"role": "INTERN"}).status_code, 400)
        self.assertFalse(InternProfile.objects.filter(user=self.other).exists())

    def test_standard_accounts_get_their_business_profiles(self):
        for role, model in [("EMPLOYEE", EmployeeProfile), ("TRAINER_TUTOR", EmployeeProfile), ("BU_MANAGER", EmployeeProfile), ("CANDIDATE", CandidateProfile)]:
            response = self.client.post("/api/users/", {"email": f"profile-{role}@test.com", "password": "StrongPass123!", "role": role}, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertTrue(model.objects.filter(user_id=response.data["id"]).exists())
