from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.projects.models import ProjectAssignment, ProjectDocument
from apps.recruitment.models import InternDocument, InternEvaluation, InternProfile
from apps.trainings.models import TrainingCertificate, TrainingEnrollment, TrainingSession
from .models import NotificationCategory
from .services import notify

@receiver(post_save, sender=TrainingEnrollment)
def enrollment_notice(sender, instance, created, **kwargs):
    if not created:
        notify(instance.user, NotificationCategory.APPROVAL, "Training request updated", f"Your enrollment for {instance.training.title} is now {instance.status}.", "/training-enrollments", instance)

@receiver(post_save, sender=ProjectAssignment)
def project_assignment_notice(sender, instance, created, **kwargs):
    if created: notify(instance.user, NotificationCategory.ASSIGNMENT, "Project assignment", f"You were assigned to {instance.project.title}.", f"/projects/{instance.project_id}", instance.project)

@receiver(post_save, sender=InternProfile)
def internship_assignment_notice(sender, instance, created, **kwargs):
    if instance.supervisor_id:
        notify(instance.supervisor, NotificationCategory.ASSIGNMENT, "Internship supervision", f"You supervise {instance.user.email}.", f"/internships/{instance.pk}", instance)
    notify(instance.user, NotificationCategory.ASSIGNMENT, "Internship updated", "Your internship assignment or status was updated.", "/internships/me", instance)

@receiver(post_save, sender=TrainingSession)
def session_notice(sender, instance, created, **kwargs):
    title = "Session scheduled" if created else "Session updated"
    if instance.trainer_id: notify(instance.trainer, NotificationCategory.SESSION, title, f"{instance.training.title} on {instance.start_date}.", "/trainings", instance)
    for enrollment in instance.enrollments.select_related("user").all():
        notify(enrollment.user, NotificationCategory.SESSION, title, f"{instance.training.title} is now {instance.status}.", "/training-enrollments", instance)

@receiver(post_save, sender=InternEvaluation)
def evaluation_notice(sender, instance, created, **kwargs):
    if created: notify(instance.intern.user, NotificationCategory.EVALUATION, "New evaluation", f"A {instance.evaluation_type} evaluation was added.", "/internships/me", instance)

@receiver(post_save, sender=InternDocument)
def intern_document_notice(sender, instance, created, **kwargs):
    recipient = instance.intern.supervisor if created else instance.intern.user
    if recipient: notify(recipient, NotificationCategory.DOCUMENT, "Internship document", f"A document for {instance.intern.user.email} was {'uploaded' if created else 'updated'}.", f"/internships/{instance.intern_id}", instance)

@receiver(post_save, sender=ProjectDocument)
def project_document_notice(sender, instance, created, **kwargs):
    if created:
        recipients={instance.project.supervisor, *instance.project.assignees.all()}
        for recipient in recipients:
            if recipient != instance.uploaded_by: notify(recipient, NotificationCategory.DOCUMENT, "Project document", f"A document was uploaded to {instance.project.title}.", f"/projects/{instance.project_id}", instance)

@receiver(post_save, sender=TrainingCertificate)
def certificate_notice(sender, instance, created, **kwargs):
    if created: notify(instance.enrollment.user, NotificationCategory.CERTIFICATE, "Certificate available", f"Your certificate for {instance.enrollment.training.title} is ready.", "/attendance-certificates", instance)
