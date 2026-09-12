from contextlib import contextmanager
import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit

from .analysis_pipeline import (
    analysis_is_stale,
    analyze_application_batch,
    process_application_analysis,
    recalculate_offer_matches,
)
from .choices import ApplicationDocumentType, ApplicationType
from .models import Application, ApplicationDocument, CandidateProfile, CVAnalysis, Offer
from .signals import analyze_new_cv_document

User = get_user_model()
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApplicationAnalysisPipelineTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_superuser(email="pipeline-admin@example.com", password="test")
        self.hr = User.objects.create_user(email="pipeline-hr@example.com", password="test", role=UserRole.HR)
        self.bu = BusinessUnit.objects.create(name="Pipeline", code="PIPE", manager=self.admin)
        self.offer = Offer.objects.create(
            title="Python developer",
            description="Backend APIs",
            business_unit=self.bu,
            application_type=ApplicationType.HIRING,
            required_skills="Python, Django, Docker",
            created_by=self.admin,
        )

    def create_application(self, suffix: str) -> Application:
        user = User.objects.create_user(email=f"{suffix}@example.com", password="test")
        profile = CandidateProfile.objects.create(user=user)
        return Application.objects.create(
            candidate_profile=profile,
            offer=self.offer,
            application_type=ApplicationType.HIRING,
        )

    @contextmanager
    def without_automatic_pipeline(self):
        post_save.disconnect(analyze_new_cv_document, sender=ApplicationDocument)
        try:
            yield
        finally:
            post_save.connect(analyze_new_cv_document, sender=ApplicationDocument)

    def add_cv(self, application: Application, content: bytes | None = None):
        content = content if content is not None else b"Jane Doe\nSkills: Python, Django\nMaster informatique"
        return ApplicationDocument.objects.create(
            application=application,
            document_type=ApplicationDocumentType.CV,
            file=SimpleUploadedFile("cv.txt", content, content_type="text/plain"),
            original_name="cv.txt",
            content_type="text/plain",
            size=len(content),
        )

    def test_historical_application_with_cv_creates_analysis_and_match(self):
        application = self.create_application("historical")
        with self.without_automatic_pipeline():
            self.add_cv(application)

        result = process_application_analysis(application)

        self.assertTrue(result.analysis_created)
        self.assertTrue(result.matching_created)
        self.assertEqual(CVAnalysis.objects.filter(application=application).count(), 1)
        self.assertEqual(application.matches.filter(offer=self.offer).count(), 1)

    def test_already_analyzed_application_is_idempotent(self):
        application = self.create_application("complete")
        self.add_cv(application)
        analysis_id = application.cv_analysis.id
        match_id = application.matches.get(offer=self.offer).id

        result = process_application_analysis(application)

        self.assertEqual(result.status, "already_complete")
        self.assertEqual(application.cv_analysis.id, analysis_id)
        self.assertEqual(application.matches.get(offer=self.offer).id, match_id)
        self.assertEqual(CVAnalysis.objects.filter(application=application).count(), 1)
        self.assertEqual(application.matches.filter(offer=self.offer).count(), 1)

    def test_application_without_cv_never_gets_fake_analysis_or_score(self):
        application = self.create_application("no-cv")

        result = process_application_analysis(application)

        self.assertEqual(result.status, "no_cv")
        self.assertFalse(CVAnalysis.objects.filter(application=application).exists())
        self.assertFalse(application.matches.exists())

    def test_batch_force_matching_updates_without_creating_duplicate(self):
        application = self.create_application("forced-match")
        self.add_cv(application)
        match = application.matches.get(offer=self.offer)

        summary = analyze_application_batch(
            Application.objects.filter(pk=application.pk),
            force_matching=True,
        )

        self.assertEqual(summary["matchings_updated"], 1)
        self.assertEqual(application.matches.filter(offer=self.offer).count(), 1)
        self.assertEqual(application.matches.get(offer=self.offer).pk, match.pk)

    def test_cv_added_later_is_automatically_analyzed_and_matched(self):
        application = self.create_application("late-cv")
        self.assertFalse(application.matches.exists())

        self.add_cv(application)

        self.assertTrue(CVAnalysis.objects.filter(application=application).exists())
        self.assertTrue(application.matches.filter(offer=self.offer).exists())

    def test_new_application_with_cv_uses_same_automatic_pipeline(self):
        application = self.create_application("new-cv")

        document = self.add_cv(application)

        self.assertEqual(document._analysis_result.status, "processed")
        self.assertEqual(CVAnalysis.objects.filter(application=application).count(), 1)
        self.assertEqual(application.matches.filter(offer=self.offer).count(), 1)

    def test_one_invalid_cv_does_not_stop_batch(self):
        valid = self.create_application("batch-valid")
        invalid = self.create_application("batch-invalid")
        with self.without_automatic_pipeline():
            self.add_cv(valid)
            self.add_cv(invalid, b"")

        summary = analyze_application_batch(Application.objects.filter(pk__in=[valid.pk, invalid.pk]))

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["analyses_created"], 1)
        self.assertEqual(summary["matchings_created"], 1)
        self.assertEqual(summary["errors"], 1)
        self.assertTrue(CVAnalysis.objects.filter(application=valid).exists())
        self.assertFalse(CVAnalysis.objects.filter(application=invalid).exists())

    def test_offer_recalculation_reuses_analysis_and_updates_match(self):
        application = self.create_application("recalculate")
        self.add_cv(application)
        analysis_id = application.cv_analysis.id
        old_score = application.matches.get(offer=self.offer).score
        self.offer.required_skills = "Python"
        self.offer.save(update_fields=["required_skills", "updated_at"])

        summary = recalculate_offer_matches(self.offer)

        self.assertEqual(summary["updated"], 1)
        self.assertEqual(application.cv_analysis.id, analysis_id)
        self.assertNotEqual(application.matches.get(offer=self.offer).score, old_score)

    def test_empty_offer_batch_does_not_analyze_other_applications(self):
        application = self.create_application("other-offer")
        with self.without_automatic_pipeline():
            self.add_cv(application)
        empty_offer = Offer.objects.create(
            title="Empty offer",
            description="No candidates",
            business_unit=self.bu,
            application_type=ApplicationType.HIRING,
            created_by=self.admin,
        )

        summary = analyze_application_batch(empty_offer.applications.all())

        self.assertEqual(summary["total"], 0)
        self.assertFalse(CVAnalysis.objects.filter(application=application).exists())

    def test_only_super_admin_can_trigger_batch_endpoints(self):
        client = APIClient()
        client.force_authenticate(self.hr)
        self.assertEqual(client.post("/api/applications/analyze-existing/").status_code, 403)
        self.assertEqual(client.post(f"/api/offers/{self.offer.id}/analyze-applications/").status_code, 403)
        self.assertEqual(client.post(f"/api/offers/{self.offer.id}/recalculate-matches/").status_code, 403)

        client.force_authenticate(self.admin)
        self.assertEqual(client.post("/api/applications/analyze-existing/").status_code, 200)
        self.assertEqual(client.post(f"/api/offers/{self.offer.id}/analyze-applications/").status_code, 200)
        self.assertEqual(client.post(f"/api/offers/{self.offer.id}/recalculate-matches/").status_code, 200)

    def test_ranking_get_is_read_only_and_keeps_unanalyzed_candidate(self):
        application = self.create_application("read-only")
        with self.without_automatic_pipeline():
            self.add_cv(application)
        client = APIClient()
        client.force_authenticate(self.admin)

        response = client.get(f"/api/offers/{self.offer.id}/candidate-ranking/")

        self.assertEqual(response.status_code, 200)
        row = response.data["ranking"][0]
        self.assertEqual(row["application"], application.id)
        self.assertIsNone(row["match"])
        self.assertIn("pas encore pu être analysé", row["analysis_error"])
        self.assertFalse(CVAnalysis.objects.filter(application=application).exists())
        self.assertFalse(application.matches.exists())

    def test_replacement_cv_updates_analysis_and_existing_match_without_duplicates(self):
        application = self.create_application("replacement")
        self.add_cv(application, b"Skills: Python")
        analysis_id = application.cv_analysis.id
        match_id = application.matches.get(offer=self.offer).id
        first_hash = application.cv_analysis.source_sha256

        self.add_cv(application, b"Skills: Python, Django, Docker")

        application.refresh_from_db()
        self.assertEqual(application.cv_analysis.id, analysis_id)
        self.assertNotEqual(application.cv_analysis.source_sha256, first_hash)
        self.assertEqual(application.matches.get(offer=self.offer).id, match_id)
        self.assertEqual(CVAnalysis.objects.filter(application=application).count(), 1)
        self.assertEqual(application.matches.filter(offer=self.offer).count(), 1)

    def test_same_cv_bytes_reuse_analysis_and_match(self):
        application = self.create_application("same-cv")
        content = b"Skills: Python, Django"
        self.add_cv(application, content)
        analysis_id = application.cv_analysis.id
        match_id = application.matches.get(offer=self.offer).id

        document = self.add_cv(application, content)

        self.assertEqual(document._analysis_result.status, "already_complete")
        self.assertEqual(application.cv_analysis.id, analysis_id)
        self.assertEqual(application.matches.get(offer=self.offer).id, match_id)

    def test_replacement_cv_preserves_human_validated_analysis_until_explicit_force(self):
        application = self.create_application("validated-replacement")
        self.add_cv(application, b"Skills: Python")
        analysis = application.cv_analysis
        analysis.skills = ["Python", "Human correction"]
        analysis.human_validated = True
        analysis.validated_by = self.hr
        analysis.save(update_fields=["skills", "human_validated", "validated_by", "updated_at"])
        original_hash = analysis.source_sha256

        replacement = self.add_cv(application, b"Skills: Docker, Kubernetes")

        analysis.refresh_from_db()
        self.assertEqual(replacement._analysis_result.status, "stale_human_validated")
        self.assertEqual(analysis.skills, ["Python", "Human correction"])
        self.assertEqual(analysis.source_sha256, original_hash)
        self.assertTrue(analysis.human_validated)
        self.assertTrue(analysis_is_stale(application, analysis))

        forced = process_application_analysis(application, force_analysis=True, force_matching=True)
        analysis.refresh_from_db()
        self.assertTrue(forced.analysis_updated)
        self.assertFalse(analysis.human_validated)
        self.assertNotEqual(analysis.source_sha256, original_hash)

    def test_manual_analysis_change_invalidates_and_updates_same_match(self):
        application = self.create_application("manual-change")
        self.add_cv(application, b"Skills: Python")
        match = application.matches.get(offer=self.offer)
        match_id = match.id
        old_fingerprint = match.candidate_fingerprint
        analysis = application.cv_analysis
        analysis.skills = ["Python", "Django", "Docker"]
        analysis.save(update_fields=["skills", "updated_at"])

        result = process_application_analysis(application)

        self.assertTrue(result.matching_updated)
        match.refresh_from_db()
        self.assertEqual(match.id, match_id)
        self.assertEqual(float(match.score), 100.0)
        self.assertNotEqual(match.candidate_fingerprint, old_fingerprint)

    def test_offer_change_invalidates_persisted_match(self):
        application = self.create_application("offer-change")
        self.add_cv(application, b"Skills: Python, Django, Docker")
        match = application.matches.get(offer=self.offer)
        old_fingerprint = match.offer_fingerprint
        self.offer.description = "Nouvelle mission orientée sécurité"
        self.offer.save(update_fields=["description", "updated_at"])

        result = process_application_analysis(application)

        self.assertTrue(result.matching_updated)
        match.refresh_from_db()
        self.assertNotEqual(match.offer_fingerprint, old_fingerprint)

    def test_algorithm_and_extractor_versions_invalidate_caches(self):
        application = self.create_application("versions")
        self.add_cv(application, b"Skills: Python")
        analysis = application.cv_analysis
        match = application.matches.get(offer=self.offer)
        analysis.extractor_version = "obsolete-extractor"
        analysis.save(update_fields=["extractor_version"])
        match.algorithm_version = "obsolete-matcher"
        match.save(update_fields=["algorithm_version"])

        result = process_application_analysis(application)

        self.assertTrue(result.analysis_updated)
        self.assertTrue(result.matching_updated)
        analysis.refresh_from_db()
        match.refresh_from_db()
        self.assertEqual(analysis.extractor_version, "structured-v7")
        self.assertEqual(match.algorithm_version, "hybrid-v1")

    def test_match_endpoint_reuses_current_persisted_match(self):
        application = self.create_application("endpoint-cache")
        self.add_cv(application, b"Skills: Python")
        client = APIClient()
        client.force_authenticate(self.admin)

        with patch("apps.recruitment.analysis_pipeline.match_application") as matcher:
            response = client.post(f"/api/applications/{application.id}/match-offers/", {})

        self.assertEqual(response.status_code, 200)
        matcher.assert_not_called()
