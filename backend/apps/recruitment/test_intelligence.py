import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.business_units.models import BusinessUnit

from .choices import ApplicationDocumentType, ApplicationType
from .intelligence import extract_cv, match_application
from .models import Application, ApplicationDocument, CandidateProfile, Offer


User = get_user_model()
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class RecruitmentIntelligenceTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        admin = User.objects.create_superuser(email="admin-ai@example.com", password="test")
        candidate = User.objects.create_user(email="candidate-ai@example.com", password="test")
        profile = CandidateProfile.objects.create(user=candidate)
        business_unit = BusinessUnit.objects.create(name="Data", code="DATA", manager=admin)
        self.offer = Offer.objects.create(
            title="Développeur backend",
            description="API métier",
            business_unit=business_unit,
            application_type=ApplicationType.HIRING,
            required_skills="python, django, docker",
            created_by=admin,
        )
        self.application = Application.objects.create(
            candidate_profile=profile,
            offer=self.offer,
            application_type=ApplicationType.HIRING,
        )
        content = b"Jane Doe\njane@example.com\nExperience Python Django\nMaster informatique"
        ApplicationDocument.objects.create(
            application=self.application,
            document_type=ApplicationDocumentType.CV,
            file=SimpleUploadedFile("cv.txt", content, content_type="text/plain"),
            original_name="cv.txt",
            content_type="text/plain",
            size=len(content),
        )

    def test_extracts_structured_cv_and_keeps_human_validation_pending(self):
        analysis = extract_cv(self.application)

        self.assertEqual(analysis.skills, ["django", "python"])
        self.assertEqual(analysis.contact_details["emails"], ["jane@example.com"])
        self.assertFalse(analysis.human_validated)
        self.assertEqual(len(analysis.source_sha256), 64)

    def test_matching_is_idempotent_and_requires_human_decision(self):
        match_application(self.application)
        match_application(self.application)

        self.assertEqual(self.application.matches.count(), 1)
        match = self.application.matches.get()
        self.assertEqual(float(match.score), 66.67)
        self.assertEqual(match.missing_skills, ["docker"])
        self.assertEqual(match.human_decision, "PENDING")
