import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from .models import EmailDeliveryLog, Notification, NotificationCategory, NotificationPreference

logger = logging.getLogger(__name__)
PREFERENCE_FIELDS={NotificationCategory.APPROVAL:"approvals",NotificationCategory.ASSIGNMENT:"assignments",NotificationCategory.SESSION:"sessions",NotificationCategory.EVALUATION:"evaluations",NotificationCategory.DOCUMENT:"documents",NotificationCategory.CERTIFICATE:"certificates"}
EMAIL_TEXT={
 "fr":{
  "account.created":"Votre compte Smart Academy",
  "password.changed":"Votre mot de passe a été modifié",
  "email.changed":"Votre adresse e-mail a été modifiée",
  "application.submitted":"Candidature reçue",
  "notification":"Nouvelle notification Smart Academy",
 },
 "en":{
  "account.created":"Your Smart Academy account",
  "password.changed":"Your password was changed",
  "email.changed":"Your email address was changed",
  "application.submitted":"Application received",
  "notification":"New Smart Academy notification",
 },
 "ar":{
  "account.created":"حسابك في Smart Academy",
  "password.changed":"تم تغيير كلمة المرور",
  "email.changed":"تم تغير البريد الإلكتروني",
  "application.submitted":"تم استلام طلبك",
  "notification":"إشعار جديد من Smart Academy",
 },
}

def send_templated_email(*,recipient,event,event_key,context=None,subject=None):
    if not recipient or not recipient.is_active or not recipient.email: return None
    language=recipient.preferred_language if recipient.preferred_language in EMAIL_TEXT else "fr"
    try:
        with transaction.atomic():
            log=EmailDeliveryLog.objects.create(recipient=recipient.email,event=event,event_key=event_key,language=language)
    except IntegrityError:
        return None
    try:
        context={"user":recipient,"language":language,"direction":"rtl" if language=="ar" else "ltr","frontend_url":settings.FRONTEND_URL,**(context or {})}
        resolved_subject=subject or EMAIL_TEXT[language].get(event,EMAIL_TEXT[language]["notification"])
        text=context.get("message",resolved_subject)
        html=render_to_string("emails/notification.html",{"subject":resolved_subject,**context})
        message=EmailMultiAlternatives(resolved_subject,text,settings.DEFAULT_FROM_EMAIL,[recipient.email])
        message.attach_alternative(html,"text/html")
        sent_count=message.send(fail_silently=False)
        if sent_count != 1:
            raise EmailDeliveryError("The email backend did not confirm delivery.")
        log.status="SENT";log.sent_at=timezone.now();log.save(update_fields=["status","sent_at"])
    except Exception as exc:
        # Persist and log only the exception type. SMTP responses can contain
        # provider details and must never leak credentials or message payloads.
        error_code=exc.__class__.__name__[:120]
        log.status="FAILED";
        log.error_code=error_code
        log.save(update_fields=["status","error_code"])
        logger.error(
            "Email delivery failed event=%s delivery_log_id=%s error_type=%s",
            event,
            log.pk,
            error_code,
        )
        if settings.EMAIL_RAISE_DELIVERY_ERRORS:
            raise
    return log

def queue_email(**kwargs):
    """Send after the surrounding transaction commits.

    This is deliberately synchronous until a real task queue is configured: a
    failed SMTP delivery is logged with its traceback and can be surfaced in
    development instead of disappearing in an unobserved background callback.
    """
    transaction.on_commit(lambda: send_templated_email(**kwargs))


class EmailDeliveryError(RuntimeError):
    """Raised when an email backend does not confirm a delivery."""

def notify(recipient,category,title,message,link="",target=None):
    if not recipient or not recipient.is_active:return None
    preferences,_=NotificationPreference.objects.get_or_create(user=recipient)
    if not getattr(preferences,PREFERENCE_FIELDS[category]):return None
    item=Notification.objects.create(recipient=recipient,category=category,title=title,message=message,link=link,target_type=target._meta.label if target else "",target_id=str(target.pk) if target else "")
    queue_email(recipient=recipient,event="notification",event_key=f"notification:{item.pk}",subject=title,context={"message":message,"link":link})
    return item
