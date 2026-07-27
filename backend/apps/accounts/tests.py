from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from .choices import UserRole
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

    def test_authenticated_user_can_read_and_update_own_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse("auth_me"),
            {"phone_number": "+212600000000", "role": UserRole.SUPER_ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "+212600000000")
        # role is read-only on MeSerializer — must not change
        self.assertEqual(self.user.role, UserRole.EMPLOYEE)

    def test_password_change_requires_authentication(self):
        response = self.client.post(reverse("auth_change_password"), {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_verifies_current_password_and_hashes_new_password(self):
        self.client.force_authenticate(user=self.user)
        invalid = self.client.post(reverse("auth_change_password"), {
            "current_password": "wrong", "new_password": "NewStrongPass456!"
        }, format="json")
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "NewStrongPass456!"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass456!"))
        self.assertNotEqual(self.user.password, "NewStrongPass456!")

    def test_password_change_applies_django_validation(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "123"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hr_can_change_own_password(self):
        """HR must be able to change their own password."""
        hr = User.objects.create_user(
            email="hr@example.com", password="StrongPass123!", role=UserRole.HR
        )
        self.client.force_authenticate(user=hr)
        response = self.client.post(reverse("auth_change_password"), {
            "current_password": "StrongPass123!", "new_password": "NewHRPass456!"
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
        business_unit = BusinessUnit.objects.create(name="Data", code="DATA", manager=manager)
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

    def test_super_admin_delete_only_deactivates_user(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.delete(reverse("user-detail", args=[self.employee.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertTrue(User.objects.filter(pk=self.employee.id).exists())

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
            internship_start="2026-02-01",
            internship_end="2026-07-31",
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
