from django.core.management import call_command
from django.test import TestCase
from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.recruitment.choices import ApplicationType
from apps.recruitment.models import Application, CandidateProfile
from .models import FactApplication

class WarehouseETLTests(TestCase):
    def test_sync_is_idempotent(self):
        user=User.objects.create_user(email="etl@test.com",password="pwd",role=UserRole.CANDIDATE)
        profile=CandidateProfile.objects.create(user=user,phone_number="",current_school="School",study_level="MASTER")
        Application.objects.create(candidate_profile=profile,application_type=ApplicationType.HIRING)
        call_command("sync_warehouse");call_command("sync_warehouse")
        self.assertEqual(FactApplication.objects.count(),1)
