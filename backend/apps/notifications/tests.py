from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.choices import UserRole
from apps.accounts.models import User
from .models import AuditLog, Notification, NotificationCategory
from .services import notify

class NotificationAuditTests(APITestCase):
    def setUp(self):
        self.admin=User.objects.create_user(email="audit-admin@test.com",password="pwd",role=UserRole.SUPER_ADMIN)
        self.hr=User.objects.create_user(email="audit-hr@test.com",password="pwd",role=UserRole.HR)
        self.user=User.objects.create_user(email="notify-user@test.com",password="pwd",role=UserRole.EMPLOYEE)
        self.other=User.objects.create_user(email="notify-other@test.com",password="pwd",role=UserRole.EMPLOYEE)

    def test_notifications_are_private_and_support_read_state(self):
        item=notify(self.user,NotificationCategory.ASSIGNMENT,"Assigned","New project","/projects/1")
        notify(self.other,NotificationCategory.SESSION,"Session","Changed")
        self.client.force_authenticate(self.user)
        response=self.client.get("/api/notifications/?unread=true")
        self.assertEqual(response.data["count"],1)
        marked=self.client.post(f"/api/notifications/{item.id}/mark_read/",{})
        self.assertTrue(marked.data["is_read"])
        self.assertEqual(self.client.get("/api/notifications/?unread=true").data["count"],0)

    def test_mark_all_read_only_changes_current_user(self):
        notify(self.user,NotificationCategory.DOCUMENT,"Document","Uploaded")
        other=notify(self.other,NotificationCategory.DOCUMENT,"Document","Uploaded")
        self.client.force_authenticate(self.user)
        response=self.client.post("/api/notifications/mark_all_read/",{})
        self.assertEqual(response.data["updated"],1)
        other.refresh_from_db(); self.assertIsNone(other.read_at)

    def test_preferences_suppress_disabled_category(self):
        self.client.force_authenticate(self.user)
        current=self.client.get("/api/notification-preferences/1/")
        self.assertTrue(current.data["certificates"])
        self.client.patch("/api/notification-preferences/1/",{"certificates":False})
        self.assertIsNone(notify(self.user,NotificationCategory.CERTIFICATE,"Certificate","Ready"))

    def test_authenticated_mutation_creates_redacted_audit_entry(self):
        self.client.force_authenticate(self.user)
        self.client.post("/api/notifications/mark_all_read/?source=test",{"secret":"must-not-be-logged"},format="json")
        log=AuditLog.objects.filter(actor=self.user,path="/api/notifications/mark_all_read/").latest("created_at")
        self.assertEqual(log.method,"POST"); self.assertNotIn("secret",str(log.metadata)); self.assertEqual(log.metadata["query"],"source=test")

    def test_audit_interface_is_admin_hr_read_only(self):
        AuditLog.objects.create(actor=self.user,actor_email=self.user.email,method="PATCH",path="/api/projects/1/",action="PATCH projects",status_code=200)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/audit-logs/").status_code,status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.get("/api/audit-logs/").status_code,status.HTTP_200_OK)
        self.assertEqual(self.client.post("/api/audit-logs/",{}).status_code,status.HTTP_405_METHOD_NOT_ALLOWED)
        self.client.force_authenticate(self.admin)
        self.assertGreaterEqual(self.client.get("/api/audit-logs/").data["count"],1)
