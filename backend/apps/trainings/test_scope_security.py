from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.business_units.models import BusinessUnit
from apps.business_units.models import BusinessUnitMembership
from apps.assistant.services import build_safe_context, retrieve_authorized_context, OllamaAssistantProvider
from .models import Training, TrainingSession, ClientProfile, TrainingEnrollment
from .serializers import TrainingSerializer, ClientTrainingSerializer
from .selectors import visible_sessions


class TrainingScopeSecurityTests(APITestCase):
    def setUp(self):
        Training.objects.all().delete()
        self.admin = User.objects.create_user(email="scope-admin@test.com", role="SUPER_ADMIN")
        self.hr = User.objects.create_user(email="scope-hr@test.com", role="HR")
        self.manager = User.objects.create_user(email="scope-manager@test.com", role="BU_MANAGER")
        self.trainer = User.objects.create_user(email="scope-trainer@test.com", role="TRAINER_TUTOR")
        self.other_trainer = User.objects.create_user(email="scope-other@test.com", role="TRAINER_TUTOR")
        self.a = User.objects.create_user(email="scope-a@test.com", role="CLIENT")
        self.b = User.objects.create_user(email="scope-b@test.com", role="CLIENT")
        self.ca = ClientProfile.objects.create(user=self.a, company_name="A")
        self.cb = ClientProfile.objects.create(user=self.b, company_name="B")
        self.bu = BusinessUnit.objects.create(name="Own BU", code="OWN", manager=self.manager)
        self.other_bu = BusinessUnit.objects.create(name="Other BU", code="OTHER")
        self.internal = self.training("Internal", business_unit=self.bu, trainer=self.trainer)
        self.ta = self.training("Client A", external_client=self.ca)
        self.tb = self.training("SECRET_B_TRAINING", external_client=self.cb)
        self.sa = self.session(self.ta, external_client=self.ca, location="Room A")
        self.sb = self.session(self.tb, external_client=self.cb, location="SECRET_B_ROOM")
        # Legacy inconsistent records must remain unreadable even before cleanup.
        self.bad = self.session(self.ta, external_client=self.cb, location="SECRET_B_LEGACY")
        self.bad_internal = self.session(self.internal, external_client=self.ca, location="INTERNAL_SECRET")

    def training(self, title, **kwargs):
        return Training.objects.create(title=title, description="Internal description", objectives="Internal objectives", duration=2, status="PUBLISHED", delivery_mode="ON_SITE", **kwargs)

    def session(self, training, **kwargs):
        defaults = dict(start_date=timezone.localdate()+timedelta(days=2), end_date=timezone.localdate()+timedelta(days=3), start_time="09:00", end_time="17:00", maximum_participants=10, location="Room", status="PLANNED")
        defaults.update(kwargs)
        return TrainingSession.objects.create(training=training, **defaults)

    def test_client_list_detail_and_sessions_hide_foreign_and_internal_records(self):
        for user, training, session, other in [(self.a, self.ta, self.sa, self.tb), (self.b, self.tb, self.sb, self.ta)]:
            with self.subTest(user=user.email):
                self.client.force_authenticate(user)
                response = self.client.get("/api/client/trainings/")
                self.assertEqual([x["id"] for x in response.data["results"]], [training.pk])
                detail = self.client.get(f"/api/client/trainings/{training.pk}/").data
                self.assertEqual([x["id"] for x in detail["sessions"]], [session.pk])
                self.assertEqual(set(detail), {"id", "title", "project_name", "associated_link", "sessions"})
                self.assertEqual(self.client.get(f"/api/client/trainings/{other.pk}/").status_code, 404)
                self.assertEqual([x["id"] for x in self.client.get("/api/client/sessions/").data["results"]], [session.pk])
                for hidden in [self.bad, self.bad_internal]:
                    self.assertEqual(self.client.get(f"/api/client/sessions/{hidden.pk}/").status_code, 404)
                self.assertEqual(self.client.get("/api/trainings/").status_code, 403)
                self.assertEqual(self.client.get("/api/training-sessions/").status_code, 403)

    def test_hr_nested_sessions_match_endpoint_scope(self):
        allowed = self.session(self.internal)
        self.session(self.internal, status="CANCELLED", location="Cancelled secret")
        self.session(self.internal, status="COMPLETED", location="Completed secret")
        self.session(self.ta, location="Reserved parent secret")
        self.client.force_authenticate(self.hr)
        detail = self.client.get(f"/api/trainings/{self.internal.pk}/")
        self.assertEqual([x["id"] for x in detail.data["sessions"]], [allowed.pk])
        self.assertEqual([x["id"] for x in self.client.get("/api/training-sessions/").data["results"]], [allowed.pk])
        self.assertEqual(self.client.get(f"/api/training-sessions/{self.bad_internal.pk}/").status_code, 404)

    def test_trainer_parent_assignment_does_not_expose_other_sessions(self):
        own = self.session(self.internal, trainer=self.trainer)
        other = self.session(self.internal, trainer=self.other_trainer, location="Other trainer secret")
        self.client.force_authenticate(self.trainer)
        for url in ["/api/trainings/", "/api/trainings/trainer-dashboard/"]:
            response = self.client.get(url)
            self.assertEqual([x["id"] for x in response.data["results"][0]["sessions"]], [own.pk])
            self.assertNotIn("Other trainer secret", str(response.data))
        self.assertEqual([x["id"] for x in self.client.get("/api/training-sessions/").data["results"]], [own.pk])
        self.assertEqual(self.client.get(f"/api/training-sessions/{other.pk}/").status_code, 404)

    def test_manager_serialization_is_bu_scoped_and_catalogue_stays_denied(self):
        own = self.session(self.internal)
        foreign = self.training("Other BU course", business_unit=self.other_bu)
        self.session(foreign)
        self.assertEqual(list(visible_sessions(TrainingSession.objects.all(), self.manager)), [own])
        data = TrainingSerializer(foreign, context={"request": SimpleNamespace(user=self.manager)}).data
        self.assertEqual(data["sessions"], [])
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get("/api/trainings/").status_code, 403)
        self.assertEqual(self.client.get("/api/training-sessions/").status_code, 403)

    def test_super_admin_keeps_all_sessions_including_legacy_records(self):
        self.client.force_authenticate(self.admin)
        detail = self.client.get(f"/api/trainings/{self.ta.pk}/").data
        self.assertEqual({x["id"] for x in detail["sessions"]}, {self.sa.pk, self.bad.pk})
        self.assertEqual(self.client.get("/api/training-sessions/").data["count"], TrainingSession.objects.count())

    def test_manager_enrollments_do_not_reveal_other_bu_or_client_training(self):
        employee = User.objects.create_user(email="scope-employee@test.com", role="EMPLOYEE")
        BusinessUnitMembership.objects.create(user=employee, business_unit=self.bu)
        foreign = self.training("FOREIGN_BU_SECRET", business_unit=self.other_bu)
        own_session = self.session(self.internal)
        own = TrainingEnrollment.objects.create(user=employee, training=self.internal, session=own_session)
        TrainingEnrollment.objects.create(user=employee, training=foreign, session=self.session(foreign))
        TrainingEnrollment.objects.create(user=employee, training=self.tb, session=self.sb)
        self.client.force_authenticate(self.manager)
        response = self.client.get("/api/enrollments/")
        self.assertEqual([row["id"] for row in response.data["results"]], [own.pk])
        self.assertNotIn("FOREIGN_BU_SECRET", str(response.data))
        self.assertNotIn("SECRET_B_TRAINING", str(response.data))

    def test_nested_serialization_without_identity_fails_closed(self):
        self.assertEqual(ClientTrainingSerializer(self.ta).data["sessions"], [])
        self.assertEqual(TrainingSerializer(self.internal).data["sessions"], [])

    def test_session_create_and_patch_reject_inconsistent_clients(self):
        self.client.force_authenticate(self.admin)
        payload = dict(training=self.ta.pk, external_client=self.cb.pk, start_date=str(self.sa.start_date), end_date=str(self.sa.end_date), start_time="09:00", end_time="17:00", maximum_participants=4, location="Room")
        response = self.client.post("/api/training-sessions/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("external_client", response.data)
        for change in [{"external_client": self.cb.pk}, {"external_client": None}, {"training": self.tb.pk}, {"training": self.internal.pk}]:
            response = self.client.patch(f"/api/training-sessions/{self.sa.pk}/", change, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("external_client", response.data)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.external_client_id, self.ca.pk)

    def test_consistent_session_creation_and_atomic_reassignment_are_allowed(self):
        self.client.force_authenticate(self.admin)
        payload = dict(training=self.ta.pk, external_client=self.ca.pk, start_date=str(self.sa.start_date), end_date=str(self.sa.end_date), start_time="09:00", end_time="17:00", maximum_participants=4, location="Room")
        self.assertEqual(self.client.post("/api/training-sessions/", payload, format="json").status_code, 201)
        response = self.client.patch(f"/api/training-sessions/{self.sa.pk}/", {"training": self.tb.pk, "external_client": self.cb.pk}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_parent_client_change_cannot_invalidate_existing_sessions(self):
        self.client.force_authenticate(self.admin)
        for client_id in [self.cb.pk, None]:
            response = self.client.patch(f"/api/trainings/{self.ta.pk}/", {"external_client": client_id}, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("external_client", response.data)
        self.ta.external_client = self.cb
        with self.assertRaises(ValidationError):
            self.ta.clean()
        self.bad.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.bad.clean()

    @override_settings(ASSISTANT_RAG_MIN_SIMILARITY=0, ASSISTANT_RAG_TOP_K=20)
    @patch("apps.recruitment.embeddings.get_or_create_embedding", return_value=[1.0, 0.0])
    def test_client_context_and_semantic_retrieval_never_include_other_client(self, embedding):
        context = build_safe_context(self.a)
        for secret in ["SECRET_B_TRAINING", "SECRET_B_ROOM", "SECRET_B_LEGACY", "INTERNAL_SECRET", "Internal objectives"]:
            self.assertNotIn(secret, str(context))
        question = "Formation SECRET_B_TRAINING : quelles sessions ?"
        selected = retrieve_authorized_context(question, context)
        self.assertTrue(selected.facts)
        self.assertNotIn("SECRET_B", str(selected))
        # The question is embedded, but none of the retrieved documents contain B.
        for call in embedding.call_args_list[1:]:
            self.assertNotIn("SECRET_B", str(call))
        llm = Mock()
        llm.chat.return_value = "Answer"
        OllamaAssistantProvider(client=llm).answer(question, selected, "fr")
        messages = llm.chat.call_args.args[0]
        self.assertNotIn("SECRET_B_ROOM", str(messages))
        self.assertNotIn("SECRET_B_LEGACY", str(messages))
