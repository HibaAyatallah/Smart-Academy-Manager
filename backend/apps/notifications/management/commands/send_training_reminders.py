from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.trainings.models import TrainingSession
from apps.notifications.services import send_templated_email
class Command(BaseCommand):
    help="Envoie les rappels des formations commençant le lendemain."
    def handle(self,*args,**options):
        target=timezone.localdate()+timedelta(days=1);sent=0
        for session in TrainingSession.objects.filter(start_date=target).prefetch_related("enrollments__user"):
            for enrollment in session.enrollments.select_related("user").all():
                if send_templated_email(recipient=enrollment.user,event="training.reminder",event_key=f"training-reminder:{session.pk}:{enrollment.user_id}:{target}",subject="Rappel de formation",context={"message":f"Votre formation {session.training.title} commence demain."}):sent+=1
        self.stdout.write(self.style.SUCCESS(f"{sent} rappel(s) envoyé(s)."))
