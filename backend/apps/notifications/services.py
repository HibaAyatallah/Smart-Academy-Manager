from .models import Notification, NotificationCategory, NotificationPreference

PREFERENCE_FIELDS = {
    NotificationCategory.APPROVAL: "approvals", NotificationCategory.ASSIGNMENT: "assignments",
    NotificationCategory.SESSION: "sessions", NotificationCategory.EVALUATION: "evaluations",
    NotificationCategory.DOCUMENT: "documents", NotificationCategory.CERTIFICATE: "certificates",
}

def notify(recipient, category, title, message, link="", target=None):
    if not recipient or not recipient.is_active:
        return None
    preferences, _ = NotificationPreference.objects.get_or_create(user=recipient)
    if not getattr(preferences, PREFERENCE_FIELDS[category]):
        return None
    return Notification.objects.create(recipient=recipient, category=category, title=title, message=message, link=link, target_type=target._meta.label if target else "", target_id=str(target.pk) if target else "")
