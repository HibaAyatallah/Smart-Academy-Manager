from apps.notifications.services import queue_email
from .choices import ApplicationStatus
EMAIL_SUBJECTS={ApplicationStatus.PRESELECTED:"Candidature présélectionnée",ApplicationStatus.INTERVIEW:"Entretien planifié",ApplicationStatus.ACCEPTED:"Candidature acceptée",ApplicationStatus.REJECTED:"Candidature refusée"}
def send_application_status_email(application,status,message=""):
    subject=EMAIL_SUBJECTS.get(status)
    if not subject:return
    queue_email(recipient=application.candidate,event="application.status",event_key=f"application:{application.pk}:status:{status}",subject=subject,context={"message":message or f"Le statut de votre candidature est maintenant : {application.get_status_display()}."})
