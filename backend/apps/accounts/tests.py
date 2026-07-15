from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from .choices import UserRole

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


class UserPermissionTests(APITestCase):
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

    def test_anonymous_user_cannot_list_users(self):
        response = self.client.get(reverse("user-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_hr_and_super_admin_receive_equivalent_user_lists(self):
        self.client.force_authenticate(user=self.hr)
        hr_response = self.client.get(reverse("user-list"))
        self.client.force_authenticate(user=self.super_admin)
        admin_response = self.client.get(reverse("user-list"))

        self.assertEqual(hr_response.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        emails = {user["email"] for user in hr_response.data["results"]}
        self.assertIn(self.employee.email, emails)
        self.assertIn(self.super_admin.email, emails)
        self.assertEqual(hr_response.data["count"], admin_response.data["count"])

    def test_hr_can_retrieve_super_admin_profile(self):
        self.client.force_authenticate(user=self.hr)

        response = self.client.get(
            reverse("user-detail", kwargs={"pk": self.super_admin.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.super_admin.id)

    def test_hr_can_create_super_admin_role(self):
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], UserRole.SUPER_ADMIN)

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


from django.core.cache import cache

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
