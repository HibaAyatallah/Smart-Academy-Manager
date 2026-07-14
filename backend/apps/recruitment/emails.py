from django.core.mail import send_mail

from .choices import ApplicationStatus


EMAIL_SUBJECTS = {
    ApplicationStatus.PRESELECTED: "Votre candidature a ete preselectionnee",
    ApplicationStatus.INTERVIEW_SCHEDULED: "Votre entretien est planifie",
    ApplicationStatus.ACCEPTED: "Votre candidature est acceptee",
    ApplicationStatus.REJECTED: "Votre candidature est refusee",
}


def send_application_status_email(application, status: str, message: str = "") -> None:
    subject = EMAIL_SUBJECTS.get(status)
    if not subject:
        return

    candidate = application.candidate
    body = message or (
        f"Bonjour {candidate.full_name},\n\n"
        f"Le statut de votre candidature est maintenant: {application.get_status_display()}.\n\n"
        "Cordialement,\nSmart Academy Manager"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=None,
        recipient_list=[candidate.email],
        fail_silently=True,
    )

