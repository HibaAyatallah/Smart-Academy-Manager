from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.recruitment.models import Application
from apps.recruitment.services import log_sensitive_action


class Command(BaseCommand):
    help = "Anonymise les candidatures dont la duree de conservation est expiree."

    def handle(self, *args, **options):
        now = timezone.now()
        applications = Application.objects.filter(
            retention_until__isnull=False,
            retention_until__lte=now,
            anonymized_at__isnull=True,
        ).select_related("candidate_profile__user")
        count = 0

        for application in applications:
            user = application.candidate
            profile = application.candidate_profile
            user.first_name = "Anonymise"
            user.last_name = ""
            user.email = f"anonymized-{user.pk}@smart-academy.local"
            user.phone_number = ""
            user.is_active = False
            user.save(update_fields=["first_name", "last_name", "email", "phone_number", "is_active", "updated_at"])

            profile.phone_number = ""
            profile.current_school = ""
            profile.study_level_other = ""
            profile.study_field = ""
            profile.linkedin_url = ""
            profile.portfolio_url = ""
            profile.address = ""
            profile.anonymized_at = now
            profile.save()

            application.motivation_message = ""
            application.rejection_reason = ""
            application.anonymized_at = now
            application.save(update_fields=["motivation_message", "rejection_reason", "anonymized_at", "updated_at"])
            log_sensitive_action(None, application, "APPLICATION_ANONYMIZED")
            count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} candidature(s) anonymisee(s)."))
