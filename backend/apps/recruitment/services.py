import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.choices import UserRole

from .choices import ApplicationStatus, ApplicationType
from .emails import send_application_status_email
from .models import (
    Application,
    ApplicationStatusHistory,
    EmployeeProfile,
    InternProfile,
    SensitiveAuditLog,
)

logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS = {
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.PRESELECTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.PRESELECTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.PRESELECTED: {
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.INTERVIEW_SCHEDULED: {
        ApplicationStatus.INTERVIEW_COMPLETED,
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.INTERVIEW_COMPLETED: {
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.ACCEPTED: set(),
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.CANCELLED: set(),
}


def log_sensitive_action(actor, application, action: str, details: dict | None = None) -> None:
    SensitiveAuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        application=application,
        action=action,
        details=details or {},
    )
    logger.info("Recruitment sensitive action: %s application=%s", action, application.pk)


def transition_application(application: Application, new_status: str, actor, comment: str = ""):
    if new_status not in ALLOWED_TRANSITIONS.get(application.status, set()):
        raise ValidationError(
            f"Transition invalide de {application.status} vers {new_status}."
        )

    with transaction.atomic():
        locked_application = Application.objects.select_for_update().get(pk=application.pk)
        old_status = locked_application.status
        if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
            raise ValidationError(
                f"Transition invalide de {old_status} vers {new_status}."
            )

        locked_application.status = new_status
        locked_application.reviewed_by = actor

        now = timezone.now()
        if new_status == ApplicationStatus.ACCEPTED:
            locked_application.accepted_at = now
            locked_application.set_retention_deadline()
            transform_accepted_candidate(locked_application)
        elif new_status == ApplicationStatus.REJECTED:
            locked_application.rejected_at = now
            locked_application.rejection_reason = comment
            locked_application.set_retention_deadline()
            send_application_status_email(locked_application, new_status)
            reject_candidate_account(locked_application)
        elif new_status == ApplicationStatus.CANCELLED:
            locked_application.cancelled_at = now
            locked_application.set_retention_deadline()
        elif new_status in {
            ApplicationStatus.PRESELECTED,
            ApplicationStatus.INTERVIEW_SCHEDULED,
        }:
            send_application_status_email(locked_application, new_status)

        locked_application.save()
        ApplicationStatusHistory.objects.create(
            application=locked_application,
            from_status=old_status,
            to_status=new_status,
            changed_by=actor,
            comment=comment,
        )
        log_sensitive_action(
            actor,
            locked_application,
            f"APPLICATION_STATUS_{new_status}",
            {"from_status": old_status, "to_status": new_status},
        )

    locked_application.refresh_from_db()
    if new_status == ApplicationStatus.ACCEPTED:
        send_application_status_email(locked_application, new_status)
    return locked_application


def transform_accepted_candidate(application: Application) -> None:
    candidate = application.candidate
    candidate.is_active = True
    if application.application_type in {
        ApplicationType.PFA_INTERNSHIP,
        ApplicationType.PFE_INTERNSHIP,
    }:
        candidate.role = UserRole.INTERN
        candidate.save(update_fields=["role", "is_active", "updated_at"])
        InternProfile.objects.get_or_create(
            user=candidate,
            defaults={"source_application": application},
        )
        return

    candidate.role = UserRole.EMPLOYEE
    candidate.save(update_fields=["role", "is_active", "updated_at"])
    EmployeeProfile.objects.get_or_create(
        user=candidate,
        defaults={"source_application": application},
    )


def reject_candidate_account(application: Application) -> None:
    candidate = application.candidate
    candidate.is_active = False
    candidate.save(update_fields=["is_active", "updated_at"])

