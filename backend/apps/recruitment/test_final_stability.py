import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services.user_deletion import delete_user_account
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from .analysis_pipeline import process_application_analysis, recalculate_offer_matches
from .intelligence import rank_offer_candidates, update_training_recommendations
from .models import Application, ApplicationDocument, CandidateProfile, CVAnalysis, InternProfile, Offer
from .serializers import ApplicationMatchSerializer
from .services import convert_accepted_application


class FinalRecruitmentStabilityTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.admin = User.objects.create_superuser(email="final-admin@test.com", password="test")
        self.user = User.objects.create_user(email="final-candidate@test.com", password="test", role="CANDIDATE")
        self.bu = BusinessUnit.objects.create(name="Software", code="Software", manager=self.admin)
        self.profile = CandidateProfile.objects.create(user=self.user)
        self.offer = Offer.objects.create(title="Python", description="APIs", required_skills="Python, Docker", business_unit=self.bu, application_type="HIRING")
        self.application = Application.objects.create(candidate_profile=self.profile, offer=self.offer, application_type="HIRING")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def cv(self, content=b"Jane Doe\nSkills: Python\nMaster informatique"):
        with patch("apps.recruitment.signals.process_application_analysis"):
            return ApplicationDocument.objects.create(application=self.application, document_type="CV", file=SimpleUploadedFile("cv.txt", content), original_name="cv.txt")

    def test_recalculation_analyzes_historical_cv_and_reuses_rows(self):
        self.cv()
        self.assertEqual(recalculate_offer_matches(self.offer)["updated"], 1)
        self.assertEqual(recalculate_offer_matches(self.offer)["updated"], 1)
        self.assertEqual(CVAnalysis.objects.count(), 1)
        self.assertEqual(self.application.matches.count(), 1)

    def test_recalculation_without_cv_never_creates_a_score(self):
        self.assertEqual(recalculate_offer_matches(self.offer)["updated"], 0)
        self.assertFalse(self.application.matches.exists())

    def test_ranking_handles_missing_physical_cv(self):
        document = self.cv()
        process_application_analysis(self.application)
        document.file.storage.delete(document.file.name)
        self.assertIsNone(rank_offer_candidates(self.offer)[0]["match"])
        self.assertEqual(recalculate_offer_matches(self.offer)["updated"], 0)

    def test_changed_bytes_hide_stale_score_before_reanalysis(self):
        document = self.cv()
        process_application_analysis(self.application)
        with document.file.open("wb") as target:
            target.write(b"Skills: Docker, Kubernetes")
        data = ApplicationMatchSerializer(self.application.matches.get()).data
        self.assertTrue(data["is_stale"])
        self.assertIsNone(data["score"])
        self.assertTrue(process_application_analysis(self.application).analysis_updated)

    def test_removed_cv_hides_existing_score(self):
        document = self.cv()
        process_application_analysis(self.application)
        document.delete()
        self.assertIsNone(ApplicationMatchSerializer(self.application.matches.get()).data["score"])

    def test_old_cv_on_another_application_remains_discoverable(self):
        self.cv()
        self.application.offer = None
        self.application.save()
        Application.objects.create(candidate_profile=self.profile, offer=self.offer, application_type="HIRING")
        self.assertEqual(recalculate_offer_matches(self.offer)["updated"], 1)
        self.assertEqual(CVAnalysis.objects.get().application_id, self.application.pk)

    def test_recommendations_are_built_even_when_matching_is_cached(self):
        from apps.trainings.models import Training
        Training.objects.create(title="Docker", description="Docker", duration=2)
        self.cv()
        process_application_analysis(self.application)
        response = self.client.post(f"/api/applications/{self.application.pk}/match-offers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["training_recommendations"]), 1)
        recommendation = self.application.training_recommendations.get()
        recommendation.human_decision = "APPROVED"
        recommendation.save()
        update_training_recommendations(self.application, list(self.application.matches.all()))
        recommendation.refresh_from_db()
        self.assertEqual(recommendation.human_decision, "APPROVED")

    def test_detached_candidate_can_still_review_cv(self):
        self.cv()
        process_application_analysis(self.application)
        delete_user_account(user=self.user, actor=self.admin, reason="TEST")
        response = self.client.patch(f"/api/applications/{self.application.pk}/cv-analysis/", {"first_name": "Corrected"}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(f"/api/applications/{self.application.pk}/validate-cv/", {"last_name": "Name"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.account_first_name, "Corrected")

    def test_conversion_is_locked_and_repeated_conversion_is_rejected(self):
        self.application.status = "ACCEPTED"
        self.application.save()
        supervisor = User.objects.create_user(email="final-supervisor@test.com", role="EMPLOYEE")
        BusinessUnitMembership.objects.create(user=supervisor, business_unit=self.bu)
        payload = {"conversion_type": "INTERN", "business_unit": self.bu, "supervisor": supervisor}
        convert_accepted_application(self.application, payload, self.admin)
        with self.assertRaises(ValidationError):
            convert_accepted_application(self.application, payload, self.admin)
        self.assertEqual(InternProfile.objects.filter(source_application=self.application).count(), 1)
        self.assertTrue(Application.objects.filter(pk=self.application.pk).exists())

    def test_conversion_uses_related_account_instead_of_contact_email_collision(self):
        other = User.objects.create_user(email="other@test.com", contact_email=self.user.email, role="HR")
        self.application.status = "ACCEPTED"
        self.application.save()
        convert_accepted_application(self.application, {"conversion_type": "EMPLOYEE", "business_unit": self.bu}, self.admin)
        other.refresh_from_db()
        self.assertEqual(other.role, "HR")
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "EMPLOYEE")

    def test_deactivated_user_is_hidden_but_can_be_reactivated_by_admin(self):
        user = User.objects.create_user(email="inactive@test.com", role="EMPLOYEE")
        self.assertEqual(self.client.delete(f"/api/users/{user.pk}/").status_code, 204)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        ids = [row["id"] for row in self.client.get("/api/users/").data["results"]]
        self.assertNotIn(user.pk, ids)
        self.assertEqual(self.client.patch(f"/api/users/{user.pk}/", {"is_active": True}, format="json").status_code, 200)

    def test_manager_without_bu_cannot_receive_global_report_data(self):
        from apps.reports.views import report_data
        manager = User.objects.create_user(email="unassigned-manager@test.com", role="BU_MANAGER")
        data = report_data({}, manager)
        self.assertNotIn(self.application.candidate_profile.display_email, str(data))
        self.assertEqual(data["recent_applications"], [])
        with self.assertRaises(Exception) as error:
            report_data({"business_unit": "invalid"}, manager)
        self.assertEqual(error.exception.status_code, 403)
