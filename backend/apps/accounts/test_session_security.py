from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .choices import UserRole


User = get_user_model()


class SessionSecurityTests(APITestCase):
    def login(self, user, password):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def authenticate(self, access):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_blacklisted_refresh_token_cannot_be_reused(self):
        user = User.objects.create_user(
            email="logout@test.com",
            password="StrongPass123!",
            role=UserRole.EMPLOYEE,
        )
        tokens = self.login(user, "StrongPass123!")

        response = self.client.post(
            reverse("token_blacklist"),
            {"refresh": tokens["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reused = self.client.post(
            reverse("token_refresh"),
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_temporary_password_account_is_limited_to_required_auth_endpoints(self):
        user = User.objects.create_user(
            email="temporary@test.com",
            password="TemporaryPass123!",
            role=UserRole.EMPLOYEE,
            must_change_password=True,
        )
        tokens = self.login(user, "TemporaryPass123!")
        self.authenticate(tokens["access"])

        profile = self.client.get(reverse("auth_me"))
        business_api = self.client.get(reverse("notification-list"))
        contact_update = self.client.patch(
            reverse("auth_contact_details"),
            {"phone_number": "+212600000000", "current_password": "TemporaryPass123!"},
            format="json",
        )

        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertTrue(profile.data["must_change_password"])
        self.assertEqual(business_api.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(business_api.data["detail"].code, "password_change_required")
        self.assertEqual(contact_update.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_change_rotates_tokens_and_unlocks_business_apis(self):
        user = User.objects.create_user(
            email="unlock@test.com",
            password="TemporaryPass123!",
            role=UserRole.EMPLOYEE,
            must_change_password=True,
        )
        old_tokens = self.login(user, "TemporaryPass123!")
        self.authenticate(old_tokens["access"])

        changed = self.client.post(
            reverse("auth_change_password"),
            {
                "current_password": "TemporaryPass123!",
                "new_password": "PermanentPass456!",
                "confirmation": "PermanentPass456!",
            },
            format="json",
        )

        self.assertEqual(changed.status_code, status.HTTP_200_OK, changed.data)
        self.assertIn("access", changed.data)
        self.assertIn("refresh", changed.data)
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)
        self.assertFalse(user.check_password("TemporaryPass123!"))
        self.assertTrue(user.check_password("PermanentPass456!"))

        self.client.credentials()
        old_refresh = self.client.post(
            reverse("token_refresh"),
            {"refresh": old_tokens["refresh"]},
            format="json",
        )
        self.assertEqual(old_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

        self.authenticate(changed.data["access"])
        profile = self.client.get(reverse("auth_me"))
        business_api = self.client.get(reverse("notification-list"))
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertFalse(profile.data["must_change_password"])
        self.assertEqual(business_api.status_code, status.HTTP_200_OK)
