import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnitMembership

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
    ApplicationStatus.RECEIVED: {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.PRESELECTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.ARCHIVED,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.PRESELECTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.ARCHIVED,
    },
    ApplicationStatus.PRESELECTED: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.ARCHIVED,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.ARCHIVED,
    },
    ApplicationStatus.ACCEPTED: {
        ApplicationStatus.ARCHIVED,
    },
    ApplicationStatus.REJECTED: {
        ApplicationStatus.ARCHIVED,
    },
    ApplicationStatus.ARCHIVED: set(),
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
        elif new_status == ApplicationStatus.REJECTED:
            locked_application.rejected_at = now
            locked_application.rejection_reason = comment
            locked_application.set_retention_deadline()
            send_application_status_email(locked_application, new_status)
            reject_candidate_account(locked_application)
        elif new_status == ApplicationStatus.ARCHIVED:
            locked_application.cancelled_at = now
            locked_application.set_retention_deadline()
        elif new_status in {
            ApplicationStatus.PRESELECTED,
            ApplicationStatus.INTERVIEW,
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

def convert_accepted_application(application: Application, payload: dict, actor) -> None:
    if application.status != ApplicationStatus.ACCEPTED:
        raise ValidationError("L'application doit être acceptée pour procéder à la conversion.")

    conversion_type = payload["conversion_type"]
    bu = payload["business_unit"]
    supervisor = payload.get("supervisor")

    candidate = application.candidate

    from apps.accounts.services.account_generation import generate_account_for_user
    from apps.accounts.choices import UserRole

    payload_for_generation = {
        "contact_email": candidate.email,
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "phone_number": candidate.phone_number,
        "role": UserRole.INTERN if conversion_type == "INTERN" else UserRole.EMPLOYEE,
        "business_unit": bu,
        "supervisor": supervisor,
        "school": payload.get("school", ""),
        "specialization": payload.get("specialization", ""),
        "internship_type": payload.get("internship_type", ""),
        "paid": payload.get("paid", False),
        "internship_start": payload.get("internship_start"),
        "internship_end": payload.get("internship_end"),
        "subject_title": payload.get("subject_title", ""),
    }

    with transaction.atomic():
        result = generate_account_for_user(payload_for_generation, actor=actor)
        user = result["user"]

        # Link the source application
        if conversion_type == "INTERN":
            profile = InternProfile.objects.get(user=user)
            profile.source_application = application
            if "specification_pdf" in payload:
                profile.specification_pdf = payload["specification_pdf"]
            profile.save(update_fields=["source_application", "specification_pdf"])
        else:
            profile = EmployeeProfile.objects.get(user=user)
            profile.source_application = application
            profile.save(update_fields=["source_application"])

        log_sensitive_action(
            actor,
            application,
            f"CANDIDATE_CONVERTED_TO_{conversion_type}",
            {
                "business_unit": bu.code,
                "supervisor_id": supervisor.id if supervisor else None,
                "generated_email": result["email"],
            },
        )


def reject_candidate_account(application: Application) -> None:
    """Deactivate the candidate account, but only if they are still a CANDIDATE.

    Guard against the edge case where a user has a second application rejected
    after having already been accepted and promoted to INTERN or EMPLOYEE via
    a previous application, or if they have other pending applications.
    """
    from apps.accounts.choices import UserRole

    candidate = application.candidate
    if candidate.role != UserRole.CANDIDATE:
        # Already promoted — do not deactivate an active employee/intern.
        return
        
    has_active_applications = Application.objects.filter(
        candidate_profile=application.candidate_profile
    ).exclude(pk=application.pk).exclude(
        status__in=[ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED, ApplicationStatus.ARCHIVED]
    ).exists()
    
    if not has_active_applications:
        candidate.is_active = False
        candidate.save(update_fields=["is_active", "updated_at"])

