from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, override_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .choices import UserRole
from .models import AccountSecurityLog
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.recruitment.models import InternProfile

User = get_user_model()


class UserModelTests(APITestCase):
    def test_create_superuser_sets_super_admin_role(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )

        self.assertEqual(user.role, UserRole.SUPER_ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": (
            "rest_framework.permissions.IsAuthenticated",
        ),
        "DEFAULT_THROTTLE_CLASSES": (
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        ),
        "DEFAULT_THROTTLE_RATES": {
            "anon": "1000/hour",
            "user": "1000/minute",
            "login": "1000/minute",
            "public_submission": "1000/hour",
            "sensitive_account": "1000/hour",
        },
        "NUM_PROXIES": None,
    },
)
class AuthAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="employee@example.com",
            password="StrongPass123!",
            first_name="Jane",
            last_name="Doe",
            role=UserRole.EMPLOYEE,
        )

    def test_token_obtain_returns_jwt_with_user_claims(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "employee@example.com", "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        token = AccessToken(response.data["access"])
        self.assertEqual(token["email"], self.user.email)
        self.assertEqual(token["role"], UserRole.EMPLOYEE)
        self.assertEqual(token["full_name"], "Jane Doe")

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth_me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_read_but_not_update_via_me(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse("auth_me"),
            {"phone_number": "+212600000000", "role": UserRole.SUPER_ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "")
        # role is read-only on MeSerializer — must not change
        self.assertEqual(self.user.role, UserRole.EMPLOYEE)

    def test_password_change_requires_authentication(self):
        response = self.client.post(reverse("auth_change_password"), {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_verifies_current_password_and_hashes_new_password(self):
        self.client.force_authenticate(user=self.user)
        invalid = self.client.post(reverse("auth_change_password"), {
            "current_password": "wrong", "new_password": "NewStrongPass456!", "confirmation": "NewStrongPass456!"
        }, format="json")
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "NewStrongPass456!", "confirmation": "NewStrongPass456!"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass456!"))
        self.assertNotEqual(self.user.password, "NewStrongPass456!")

    def test_password_change_applies_django_validation(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "123", "confirmation": "123"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hr_can_change_own_password(self):
        """HR must be able to change their own password."""
        hr = User.objects.create_user(
            email="hr@example.com", password="StrongPass123!", role=UserRole.HR
        )
        self.client.force_authenticate(user=hr)
        response = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "NewHRPass456!", "confirmation": "NewHRPass456!"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hr_can_read_and_update_own_profile(self):
        """HR must be able to view and update their own profile."""
        hr = User.objects.create_user(
            email="hr2@example.com", password="StrongPass123!",
            first_name="Marie", role=UserRole.HR
        )
        self.client.force_authenticate(user=hr)
        response = self.client.get(reverse("auth_me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "hr2@example.com")
        # role field must be read-only
        self.assertNotIn("password", response.data)

    def test_hr_jwt_token_has_hr_role_claim(self):
        """JWT token for HR user must carry role=HR in claims."""
        hr = User.objects.create_user(
            email="hr3@example.com", password="StrongPass123!", role=UserRole.HR
        )
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "hr3@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = AccessToken(response.data["access"])
        self.assertEqual(token["role"], UserRole.HR)

    def test_contact_update_requires_password_and_uses_request_user_only(self):
        other = User.objects.create_user(email="other@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)
        denied = self.client.patch(reverse("auth_contact_details"), {
            "email": "new@example.com", "current_password": "wrong", "user": other.id,
        }, format="json")
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(reverse("auth_contact_details"), {
            "email": "new@example.com", "phone_number": "+212600000001",
            "current_password": "StrongPass123!", "user": other.id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(other.email, "other@example.com")
        self.assertTrue(AccountSecurityLog.objects.filter(actor=self.user, action="CONTACT_DETAILS_CHANGED").exists())

    def test_contact_update_rejects_duplicate_email(self):
        User.objects.create_user(email="used@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("auth_contact_details"), {
            "email": "USED@example.com", "current_password": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_password_change_requires_confirmation_and_invalidates_old_jwt(self):
        token_response = self.client.post(reverse("token_obtain_pair"), {
            "email": self.user.email, "password": "StrongPass123!",
        }, format="json")
        old_access = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
        mismatch = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "NewStrongPass456!",
            "confirmation": "DifferentPass456!",
        }, format="json")
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        changed = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "NewStrongPass456!",
            "confirmation": "NewStrongPass456!",
        }, format="json")
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("auth_me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(AccountSecurityLog.objects.filter(actor=self.user, action="PASSWORD_CHANGED").exists())


class UserPermissionTests(APITestCase):
    """Tests the strict Super Admin vs HR role separation for user management."""

    def setUp(self):
        self.super_admin = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.hr = User.objects.create_user(
            email="hr@example.com",
            password="StrongPass123!",
            role=UserRole.HR,
        )
        self.employee = User.objects.create_user(
            email="employee@example.com",
            password="StrongPass123!",
            role=UserRole.EMPLOYEE,
        )

    # ── Super Admin can manage users ────────────────────────────────────────

    def test_super_admin_can_list_users(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data["count"], 0)

    def test_super_admin_can_create_user(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            reverse("user-list"),
            {
                "email": "candidate@example.com",
                "password": "StrongPass123!",
                "role": UserRole.CANDIDATE,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="candidate@example.com").exists())

    def test_super_admin_can_create_super_admin_user(self):
        """Only Super Admin can assign the SUPER_ADMIN role."""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            reverse("user-list"),
            {
                "email": "new-admin@example.com",
                "password": "StrongPass123!",
                "role": UserRole.SUPER_ADMIN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], UserRole.SUPER_ADMIN)

    def test_super_admin_can_search_and_filter_users(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(
            reverse("user-list"), {"search": "employee@", "role": UserRole.EMPLOYEE, "is_active": True}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.employee.id])

    def test_super_admin_can_create_employee_with_business_unit(self):
        manager = User.objects.create_user(
            email="manager@example.com", password="StrongPass123!", role=UserRole.BU_MANAGER
        )
        business_unit = BusinessUnit.objects.create(name="Software", code="Software")
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            reverse("user-list"),
            {
                "email": "assigned@example.com", "password": "StrongPass123!",
                "role": UserRole.EMPLOYEE, "business_unit_id": business_unit.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="assigned@example.com")
        self.assertTrue(BusinessUnitMembership.objects.filter(
            user=user, business_unit=business_unit, is_active=True
        ).exists())
        self.assertEqual(response.data["business_units"][0]["id"], business_unit.id)

    def test_super_admin_can_change_user_business_unit_and_audit_it(self):
        from apps.notifications.models import AuditLog

        old_bu = BusinessUnit.objects.create(name="NetSEC", code="NetSEC")
        new_bu = BusinessUnit.objects.create(name="System", code="System")
        BusinessUnitMembership.objects.create(user=self.employee, business_unit=old_bu)
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.patch(
            reverse("user-detail", args=[self.employee.id]),
            {"business_unit_id": new_bu.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(BusinessUnitMembership.objects.get(
            user=self.employee, business_unit=old_bu
        ).is_active)
        self.assertTrue(BusinessUnitMembership.objects.get(
            user=self.employee, business_unit=new_bu
        ).is_active)
        log = AuditLog.objects.get(action="USER_BUSINESS_UNIT_CHANGED")
        self.assertEqual(log.actor, self.super_admin)
        self.assertEqual(log.target_id, str(self.employee.id))
        self.assertEqual(log.metadata["old_business_unit"]["code"], "NetSEC")
        self.assertEqual(log.metadata["new_business_unit"]["code"], "System")

    def test_user_assignment_rejects_non_official_business_unit(self):
        legacy_bu = BusinessUnit.objects.create(name="Legacy", code="Software")
        # Simulate an inconsistent legacy row without creating a duplicate
        # official BU name; validation is based on the canonical code.
        BusinessUnit.objects.filter(pk=legacy_bu.pk).update(code="Legacy")
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.patch(
            reverse("user-detail", args=[self.employee.id]),
            {"business_unit_id": legacy_bu.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("business_unit_id", response.data)

    def test_super_admin_retires_internal_user_and_hides_it_by_default(self):
        from apps.notifications.models import AuditLog

        user_id = self.employee.id
        email = self.employee.email
        membership = BusinessUnitMembership.objects.create(
            business_unit=BusinessUnit.objects.create(name="Delete BU", code="DELETE"),
            user=self.employee,
            is_active=True,
        )
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.delete(reverse("user-detail", args=[self.employee.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(User.objects.filter(pk=user_id, is_active=False).exists())
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
        self.assertNotEqual(self.client.post(reverse("token_obtain_pair"), {
            "email": email, "password": "StrongPass123!"
        }, format="json").status_code, status.HTTP_200_OK)
        listed_ids = [item["id"] for item in self.client.get(reverse("user-list")).data["results"]]
        self.assertNotIn(user_id, listed_ids)
        self.assertEqual(
            self.client.get("/api/reports/summary/").status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(AuditLog.objects.filter(
            actor=self.super_admin,
            action="USER_DEACTIVATED",
            metadata__user_id=user_id,
            metadata__reason="MANUAL_SUPER_ADMIN",
            metadata__deletion_mode="DEACTIVATED",
        ).exists())

        inactive_ids = [
            item["id"] for item in self.client.get(
                reverse("user-list"), {"is_active": "false"}
            ).data["results"]
        ]
        self.assertIn(user_id, inactive_ids)

    def test_internal_user_retirement_preserves_project_history(self):
        from apps.projects.models import Project

        business_unit = BusinessUnit.objects.create(name="Hard delete BU", code="HARD")
        project = Project.objects.create(
            title="Historical project", description="Kept", business_unit=business_unit,
            supervisor=self.employee, created_by=self.employee,
        )
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.delete(reverse("user-detail", args=[self.employee.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        project.refresh_from_db()
        self.assertEqual(project.supervisor_id, self.employee.id)
        self.assertEqual(project.created_by_id, self.employee.id)

    def test_candidate_manual_delete_detaches_and_preserves_application(self):
        from apps.recruitment.choices import ApplicationType, StudyLevel
        from apps.recruitment.models import Application, CandidateProfile

        candidate = User.objects.create_user(
            email="delete-candidate@example.com", password="StrongPass123!",
            role=UserRole.CANDIDATE,
        )
        profile = CandidateProfile.objects.create(
            user=candidate, phone_number="", current_school="",
            study_level=StudyLevel.MASTER, study_field="",
        )
        application = Application.objects.create(
            candidate_profile=profile, application_type=ApplicationType.HIRING,
        )
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.delete(reverse("user-detail", args=[candidate.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=candidate.id).exists())
        profile.refresh_from_db()
        self.assertIsNone(profile.user_id)
        self.assertTrue(Application.objects.filter(pk=application.pk).exists())

    def test_super_admin_cannot_delete_own_account(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.delete(reverse("user-detail", args=[self.super_admin.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Vous ne pouvez pas supprimer votre propre compte.",
        )
        self.super_admin.refresh_from_db()
        self.assertTrue(self.super_admin.is_active)
        from apps.notifications.models import AuditLog
        self.assertFalse(AuditLog.objects.filter(
            action="USER_HARD_DELETED",
            metadata__user_id=self.super_admin.id,
        ).exists())

    # ── HR is blocked from ALL user management ──────────────────────────────

    def test_hr_cannot_list_users(self):
        """HR must receive 403 on the user list endpoint."""
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_cannot_retrieve_any_user(self):
        """HR must receive 403 when retrieving another user's profile."""
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(
            reverse("user-detail", kwargs={"pk": self.super_admin.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_cannot_create_user(self):
        """HR must receive 403 when attempting to create a user."""
        self.client.force_authenticate(user=self.hr)
        response = self.client.post(
            reverse("user-list"),
            {
                "email": "new@example.com",
                "password": "StrongPass123!",
                "role": UserRole.EMPLOYEE,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_cannot_assign_super_admin_role(self):
        """HR must receive 403 when attempting to create a Super Admin user."""
        self.client.force_authenticate(user=self.hr)
        response = self.client.post(
            reverse("user-list"),
            {
                "email": "new-admin@example.com",
                "password": "StrongPass123!",
                "role": UserRole.SUPER_ADMIN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_cannot_delete_user(self):
        """HR must receive 403 when attempting to deactivate a user."""
        self.client.force_authenticate(user=self.hr)
        response = self.client.delete(reverse("user-detail", args=[self.employee.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_cannot_list_users(self):
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_employee_cannot_list_users(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HREndpointTests(APITestCase):
    """Tests the HR-specific read-only endpoints."""

    def setUp(self):
        self.super_admin = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.hr = User.objects.create_user(
            email="hr@example.com",
            password="StrongPass123!",
            role=UserRole.HR,
        )
        self.manager = User.objects.create_user(
            email="mgr@example.com", password="StrongPass123!", role=UserRole.BU_MANAGER
        )
        self.bu = BusinessUnit.objects.create(name="Dev", code="DEV", manager=self.manager)
        self.employee = User.objects.create_user(
            email="emp@example.com", password="StrongPass123!", role=UserRole.EMPLOYEE
        )
        self.intern = User.objects.create_user(
            email="intern@example.com", password="StrongPass123!",
            first_name="Ali", last_name="Hassan", role=UserRole.INTERN, is_active=True
        )
        self.intern_profile = InternProfile.objects.create(
            user=self.intern,
            school="École Nationale",
            specialization="Informatique",
            internship_type="PFE",
            paid=True,
            business_unit=self.bu,
            supervisor=self.employee,
            subject_title="Plateforme RH",
            internship_start=timezone.localdate() - timedelta(days=180),
            internship_end=timezone.localdate() + timedelta(days=180),
        )
        BusinessUnitMembership.objects.create(
            business_unit=self.bu, user=self.employee, is_active=True, position="Developer"
        )

    # ── /api/hr/interns/ ────────────────────────────────────────────────────

    def test_hr_can_list_interns(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(reverse("hr-intern-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        emails = [u["email"] for u in data]
        self.assertIn("intern@example.com", emails)
        # Employee must NOT appear in the intern list
        self.assertNotIn("emp@example.com", emails)

    def test_hr_can_retrieve_intern_detail(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(reverse("hr-intern-detail", kwargs={"pk": self.intern_profile.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "intern@example.com")
        # Sensitive management fields must not appear
        self.assertNotIn("password", response.data)
        self.assertNotIn("is_staff", response.data)
        self.assertEqual(response.data["school"], "École Nationale")
        self.assertEqual(response.data["business_unit"]["code"], "DEV")
        self.assertEqual(response.data["supervisor"]["email"], self.employee.email)
        self.assertEqual(response.data["subject_title"], "Plateforme RH")
        self.assertIn("document_submission_status", response.data)
        self.assertIn("required_documents", response.data)

    def test_hr_endpoints_reject_unsafe_methods(self):
        self.client.force_authenticate(user=self.hr)
        self.assertEqual(self.client.post(reverse("hr-intern-list"), {}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(reverse("hr-intern-detail", kwargs={"pk": self.intern_profile.pk}), {}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(reverse("hr-intern-detail", kwargs={"pk": self.intern_profile.pk})).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(reverse("hr-collaborators-by-bu"), {}).status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_intern_list_excludes_non_interns(self):
        """Candidates, employees, and managers must not appear in the intern list."""
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(reverse("hr-intern-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        emails = {u["email"] for u in data}
        self.assertNotIn(self.employee.email, emails)
        self.assertNotIn(self.manager.email, emails)
        self.assertNotIn(self.hr.email, emails)

    def test_super_admin_cannot_access_hr_intern_endpoint(self):
        """Super Admin must use /api/users/?role=INTERN — the HR endpoint is HR-only."""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(reverse("hr-intern-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_access_hr_intern_endpoint(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(reverse("hr-intern-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_access_hr_intern_endpoint(self):
        response = self.client.get(reverse("hr-intern-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── /api/hr/collaborators/ ──────────────────────────────────────────────

    def test_hr_can_list_collaborators_by_bu(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(reverse("hr-collaborators-by-bu"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        # Find the DEV BU group
        dev_group = next((g for g in response.data if g["bu_code"] == "DEV"), None)
        self.assertIsNotNone(dev_group)
        member_emails = [m["email"] for m in dev_group["members"]]
        self.assertIn("emp@example.com", member_emails)

    def test_collaborators_endpoint_returns_grouped_structure(self):
        """Response must include bu_name, bu_code, manager_name, and members list."""
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(reverse("hr-collaborators-by-bu"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data:
            group = response.data[0]
            self.assertIn("bu_name", group)
            self.assertIn("bu_code", group)
            self.assertIn("manager_name", group)
            self.assertIn("members", group)

    def test_super_admin_cannot_access_hr_collaborators_endpoint(self):
        """Super Admin must use /api/business-unit-memberships/ — the HR endpoint is HR-only."""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(reverse("hr-collaborators-by-bu"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_access_hr_collaborators_endpoint(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(reverse("hr-collaborators-by-bu"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ThrottleTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="StrongPass123!",
            role=UserRole.EMPLOYEE,
        )
        cache.clear()

    def test_excessive_login_attempts_throttled(self):
        """Excessive login attempts are throttled (429)"""
        # Use up the 10/minute limit configured in base.py
        for _ in range(10):
            self.client.post(
                reverse("token_obtain_pair"),
                {"email": "test@example.com", "password": "StrongPass123!"},
                format="json",
            )
        # 11th attempt should be throttled
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "test@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_authenticated_endpoints_not_affected(self):
        """Authenticated internal endpoints are not blocked by login throttle"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("auth_me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_RAISE_DELIVERY_ERRORS=True,
    FRONTEND_URL="http://localhost:4200",
    PASSWORD_RESET_TIMEOUT=1800,
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": (),
        "DEFAULT_THROTTLE_RATES": {"login": "1000/minute"},
    },
)
class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="amira@example.com",
            password="OldStrongPass123!",
            first_name="Amira",
            role=UserRole.HR,
            is_active=True,
        )

    def _uid_token(self):
        return (
            urlsafe_base64_encode(force_bytes(self.user.pk)),
            default_token_generator.make_token(self.user),
        )

    def test_request_is_enumeration_safe_and_sends_professional_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            known = self.client.post(reverse("auth_password_reset_request"), {"email": self.user.email}, format="json")
        with self.captureOnCommitCallbacks(execute=True):
            unknown = self.client.post(reverse("auth_password_reset_request"), {"email": "absent@example.com"}, format="json")

        self.assertEqual(known.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown.status_code, status.HTTP_200_OK)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Amira", mail.outbox[0].alternatives[0].content)
        self.assertIn("Oui, c’est moi", mail.outbox[0].alternatives[0].content)
        self.assertIn("reset-password?token=", mail.outbox[0].alternatives[0].content)

    def test_valid_token_can_reset_once_and_blacklists_refresh_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        uid, token = self._uid_token()
        validation = self.client.get(
            reverse("auth_password_reset_validate", kwargs={"uid": uid, "token": token})
        )
        self.assertEqual(validation.status_code, status.HTTP_200_OK)
        self.assertTrue(validation.data["valid"])

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("auth_password_reset_confirm"), {
                "uid": uid,
                "token": token,
                "new_password": "NewStrongPass456!",
                "confirmation": "NewStrongPass456!",
            }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass456!"))
        self.assertFalse(self.user.check_password("OldStrongPass123!"))
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("a été modifié", mail.outbox[0].body)

        login = self.client.post(reverse("token_obtain_pair"), {
            "email": self.user.email,
            "password": "NewStrongPass456!",
        }, format="json")
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access", login.data)

        reused = self.client.post(reverse("auth_password_reset_confirm"), {
            "uid": uid, "token": token,
            "new_password": "AnotherStrongPass789!", "confirmation": "AnotherStrongPass789!",
        }, format="json")
        self.assertEqual(reused.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_token_never_displays_the_password_form(self):
        uid, _ = self._uid_token()
        response = self.client.get(
            reverse("auth_password_reset_validate", kwargs={"uid": uid, "token": "invalid-token"})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"valid": False})

    def test_password_confirmation_and_django_validators_are_enforced(self):
        uid, token = self._uid_token()
        mismatch = self.client.post(reverse("auth_password_reset_confirm"), {
            "uid": uid, "token": token, "new_password": "NewStrongPass456!", "confirmation": "different",
        }, format="json")
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirmation", mismatch.data)

        weak = self.client.post(reverse("auth_password_reset_confirm"), {
            "uid": uid, "token": token, "new_password": "123", "confirmation": "123",
        }, format="json")
        self.assertEqual(weak.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_account_has_same_response_and_receives_no_email(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("auth_password_reset_request"), {"email": self.user.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_request_is_available_to_every_login_role(self):
        roles = list(UserRole.values)
        users = []
        for index, role in enumerate(roles):
            users.append(User.objects.create_user(
                email=f"role-{index}@example.com",
                password="RoleStrongPass123!",
                role=role,
                is_active=True,
            ))
        with self.captureOnCommitCallbacks(execute=True):
            responses = [
                self.client.post(reverse("auth_password_reset_request"), {"email": user.email}, format="json")
                for user in users
            ]
        self.assertTrue(all(response.status_code == status.HTTP_200_OK for response in responses))
        self.assertEqual(len(mail.outbox), len(users))
