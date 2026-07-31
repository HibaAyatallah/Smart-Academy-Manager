from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.projects.models import ProjectAssignment, ProjectDocument
from apps.recruitment.models import InternDocument, InternEvaluation, InternProfile
from apps.trainings.models import TrainingCertificate, TrainingEnrollment, TrainingSession
from .models import NotificationCategory
from .services import notify
from .services import queue_email
from apps.accounts.models import User
from apps.business_units.models import BusinessUnitMembership

@receiver(pre_save, sender=User)
def remember_previous_role(sender, instance, **kwargs):
    instance._previous_role = sender.objects.filter(pk=instance.pk).values_list("role", flat=True).first() if instance.pk else None

@receiver(post_save, sender=User)
def account_created_email(sender, instance, created, **kwargs):
    if created:
        queue_email(recipient=instance,event="account.created",event_key=f"account-created:{instance.pk}",context={"message":"Votre compte Smart Academy est disponible."})
    elif getattr(instance,"_previous_role",None) and instance._previous_role != instance.role:
        queue_email(recipient=instance,event="account.converted",event_key=f"account-role:{instance.pk}:{instance.role}",subject="Votre espace Smart Academy a évolué",context={"message":f"Votre nouveau rôle est : {instance.get_role_display()}."})

@receiver(post_save, sender=BusinessUnitMembership)
def business_unit_assignment_email(sender, instance, created, **kwargs):
    if created or instance.is_active:
        queue_email(recipient=instance.user,event="business-unit.assigned",event_key=f"bu-assignment:{instance.pk}:{instance.is_active}",subject="Affectation Business Unit",context={"message":f"Vous êtes affecté à la Business Unit {instance.business_unit.name}."})

@receiver(post_save, sender=TrainingEnrollment)
def enrollment_notice(sender, instance, created, **kwargs):
    notify(instance.user, NotificationCategory.APPROVAL, "Training enrollment" if created else "Training request updated", f"Your enrollment for {instance.training.title} is now {instance.status}.", "/training-enrollments", instance)

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
