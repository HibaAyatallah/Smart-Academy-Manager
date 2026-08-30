import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.business_units.models import BusinessUnit

from .choices import ApplicationDocumentType, ApplicationType, StudyLevel
from .intelligence import (
    approximate_experience_years,
    extract_cv,
    match_application,
    parse_cv_text,
    rank_offer_candidates,
)
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

        self.assertEqual(analysis.skills, ["Django", "Python"])
        self.assertEqual(analysis.contact_details["emails"], ["jane@example.com"])
        self.assertFalse(analysis.human_validated)
        self.assertEqual(len(analysis.source_sha256), 64)

    def test_matching_is_idempotent_and_requires_human_decision(self):
        match_application(self.application)
        match_application(self.application)

        self.assertEqual(self.application.matches.count(), 1)
        match = self.application.matches.get()
        self.assertEqual(float(match.score), 66.67)
        self.assertEqual(match.missing_skills, ["Docker"])
        self.assertEqual(match.human_decision, "PENDING")

    def test_skill_aliases_are_canonical_and_deduplicated(self):
        data = parse_cv_text("Skills: Python3, Python, JS, Postgres, DRF, ML, REST API")
        self.assertEqual(
            data["skills"],
            ["Python", "JavaScript", "PostgreSQL", "Django REST Framework", "Machine Learning", "REST API"],
        )

    def test_experience_intervals_are_merged_conservatively(self):
        years = approximate_experience_years([
            {"start_date": "2022", "end_date": "2023"},
            {"start_date": "2023", "end_date": "2024"},
            {"start_date": "", "end_date": ""},
        ])
        self.assertEqual(years, 3.0)

    def test_explainable_score_normalizes_available_offer_criteria(self):
        self.offer.required_skills = "Python3, Django, Docker"
        self.offer.required_level = StudyLevel.MASTER
        self.offer.save(update_fields=["required_skills", "required_level"])
        analysis = extract_cv(self.application)
        analysis.education = [{"title": "Master informatique", "institution": "ENSA"}]
        analysis.diplomas = ["Master informatique"]
        analysis.skills = ["Python", "Django", "FastAPI"]
        analysis.save()

        match = match_application(self.application)[0]

        self.assertEqual(float(match.score), 74.36)
        self.assertEqual(match.matched_skills, ["Django", "Python"])
        self.assertEqual(match.missing_skills, ["Docker"])
        self.assertEqual(match.additional_skills, ["FastAPI"])
        self.assertEqual(match.score_breakdown["skills"]["score"], 66.67)
        self.assertFalse(match.score_breakdown["experience"]["available"])
        self.assertIn("aide à la décision", match.candidate_summary)

    def test_offer_without_criteria_returns_explainable_zero_not_random_score(self):
        self.offer.required_skills = ""
        self.offer.required_level = ""
        self.offer.save(update_fields=["required_skills", "required_level"])
        match = match_application(self.application)[0]
        self.assertEqual(float(match.score), 0.0)
        self.assertEqual(match.score_breakdown["normalized_weight"], 0)

    def test_ranking_is_offer_scoped_and_stable_for_equal_scores(self):
        other_user = User.objects.create_user(email="ranked@example.com", password="test")
        other_profile = CandidateProfile.objects.create(user=other_user)
        other_application = Application.objects.create(
            candidate_profile=other_profile, offer=self.offer,
            application_type=ApplicationType.HIRING,
        )
        content = b"Alex Doe\nalex@example.com\nSkills: Python, Django"
        ApplicationDocument.objects.create(
            application=other_application, document_type=ApplicationDocumentType.CV,
            file=SimpleUploadedFile("other.txt", content, content_type="text/plain"),
            original_name="other.txt", content_type="text/plain", size=len(content),
        )

        ranking = rank_offer_candidates(self.offer)

        self.assertEqual([row["application"].id for row in ranking], [self.application.id, other_application.id])
        self.assertTrue(all(row["application"].offer_id == self.offer.id for row in ranking))

    def test_ranking_api_requires_recruitment_manager(self):
        client = APIClient()
        candidate = self.application.candidate_profile.user
        client.force_authenticate(candidate)
        denied = client.get(f"/api/offers/{self.offer.id}/candidate-ranking/")
        self.assertEqual(denied.status_code, 403)

        admin = self.offer.created_by
        client.force_authenticate(admin)
        allowed = client.get(f"/api/offers/{self.offer.id}/candidate-ranking/")
        self.assertEqual(allowed.status_code, 200)
        ranking = allowed.json()["ranking"]
        self.assertEqual(ranking[0]["application"], self.application.id)
        self.assertIsInstance(ranking[0]["match"]["score"], float)
