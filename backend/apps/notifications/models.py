from django.conf import settings
from django.db import models

class NotificationCategory(models.TextChoices):
    APPROVAL = "APPROVAL", "Approval"
    ASSIGNMENT = "ASSIGNMENT", "Assignment"
    SESSION = "SESSION", "Session"
    EVALUATION = "EVALUATION", "Evaluation"
    DOCUMENT = "DOCUMENT", "Document"
    CERTIFICATE = "CERTIFICATE", "Certificate"

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read_at", "created_at"])]

class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    approvals = models.BooleanField(default=True)
    assignments = models.BooleanField(default=True)
    sessions = models.BooleanField(default=True)
    evaluations = models.BooleanField(default=True)
    documents = models.BooleanField(default=True)
    certificates = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="platform_audit_logs")
    actor_email = models.EmailField(blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at", "actor"]), models.Index(fields=["action"])]

class EmailDeliveryLog(models.Model):
    recipient = models.EmailField()
    event = models.CharField(max_length=80)
    event_key = models.CharField(max_length=255)
    language = models.CharField(max_length=2, default="fr")
    status = models.CharField(max_length=16, choices=[("PENDING","Pending"),("SENT","Sent"),("FAILED","Failed")], default="PENDING")
    error_code = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["recipient", "event_key"], name="unique_email_event_recipient")]
        ordering = ["-created_at"]
