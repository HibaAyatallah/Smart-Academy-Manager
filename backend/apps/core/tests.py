from django.contrib import admin
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.choices import UserRole
from apps.accounts.models import User

from .models import ContactMessage, ContactMessageStatus
from .views import ContactSubmissionRateThrottle


class ContactMessageTests(APITestCase):
    payload = {
        "full_name": "Ahmed Benjelloun",
        "email": "ahmed@example.com",
        "request_type": "Formation",
        "subject": "Demande de formation",
        "message": "Je souhaite recevoir davantage d'informations.",
    }

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="contact-admin@test.com", password="pwd", role=UserRole.SUPER_ADMIN
        )
        self.employee = User.objects.create_user(
            email="contact-employee@test.com", password="pwd", role=UserRole.EMPLOYEE
        )

    def test_anonymous_submission_is_validated_and_persisted(self):
        response = self.client.post("/api/contact-messages/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        item = ContactMessage.objects.get()
        self.assertEqual(item.status, ContactMessageStatus.NEW)
        self.assertEqual(item.email, self.payload["email"])

    def test_invalid_submission_is_rejected(self):
        response = self.client.post(
            "/api/contact-messages/",
            {**self.payload, "email": "invalid", "message": "court"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ContactMessage.objects.exists())

    def test_public_submission_is_throttled(self):
        original_rate = getattr(ContactSubmissionRateThrottle, "rate", None)
        ContactSubmissionRateThrottle.rate = "1/hour"
        cache.clear()
        try:
            self.client.post("/api/contact-messages/", self.payload, format="json")
            response = self.client.post("/api/contact-messages/", self.payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            if original_rate is None:
                delattr(ContactSubmissionRateThrottle, "rate")
            else:
                ContactSubmissionRateThrottle.rate = original_rate
            cache.clear()

    def test_only_super_admin_can_consult_and_update_status(self):
        item = ContactMessage.objects.create(**self.payload)
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get("/api/contact-messages/").status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin_user)
        self.assertEqual(self.client.get("/api/contact-messages/").data["count"], 1)
        response = self.client.patch(
            f"/api/contact-messages/{item.id}/", {"status": ContactMessageStatus.RESOLVED}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.status, ContactMessageStatus.RESOLVED)

    def test_django_admin_is_registered_and_super_admin_only(self):
        self.assertIn(ContactMessage, admin.site._registry)
        model_admin = admin.site._registry[ContactMessage]
        request = type("Request", (), {"user": self.employee})()
        self.assertFalse(model_admin.has_module_permission(request))
