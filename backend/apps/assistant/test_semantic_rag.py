from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.recruitment.embeddings import EmbeddingUnavailableError
from apps.recruitment.models import Application, CandidateProfile, InternProfile
from apps.trainings.models import ClientProfile, Training, TrainingEnrollment, TrainingSession
from .services import (
    AnswerSource, AssistantEmbeddingError, OllamaAssistantProvider, SafeContext,
    answer_user_message, build_safe_context, retrieve_authorized_context,
)
from .models import ChatMessage, Conversation


@override_settings(ASSISTANT_RAG_MIN_SIMILARITY=0.35, ASSISTANT_RAG_TOP_K=5)
class SemanticRAGTests(TestCase):
    def setUp(self):
        self.initial_visible_trainings = Training.objects.filter(status="PUBLISHED", external_client__isnull=True).count()
        self.users = {role: User.objects.create_user(email=f"{role}@test.com", role=role) for role in [
            "SUPER_ADMIN", "HR", "BU_MANAGER", "EMPLOYEE", "TRAINER_TUTOR", "INTERN", "CLIENT", "CANDIDATE",
        ]}
        self.own_bu = BusinessUnit.objects.create(name="Own", code="OWN", manager=self.users["BU_MANAGER"])
        self.foreign_bu = BusinessUnit.objects.create(name="Foreign", code="FOREIGN")
        self.own = Training.objects.create(title="Visible training", description="Allowed", business_unit=self.own_bu, duration=1, status="PUBLISHED")
        self.foreign = Training.objects.create(title="Foreign secret", description="Private", business_unit=self.foreign_bu, duration=1)
        self.client_profile = ClientProfile.objects.create(user=self.users["CLIENT"])
        self.reserved = Training.objects.create(title="Reserved project", project_name="Client project", external_client=self.client_profile, business_unit=self.own_bu, duration=1)
        self.candidate_profile = CandidateProfile.objects.create(user=self.users["CANDIDATE"])
        self.application = Application.objects.create(candidate_profile=self.candidate_profile, application_type="HIRING")
        InternProfile.objects.create(user=self.users["INTERN"], business_unit=self.own_bu, subject_title="Own internship")

    @patch("apps.recruitment.embeddings.get_or_create_embedding", return_value=[1.0, 0.0])
    def test_role_scope_is_applied_before_any_embedding_or_generation(self, embedding):
        expected_absent = {
            "SUPER_ADMIN": ["Foreign secret"],  # Current admin corpus is aggregate-only.
            "HR": ["Applications total", "Business units total", "Foreign secret", "Reserved project"],
            "BU_MANAGER": ["Foreign secret", "Reserved project"],
            "EMPLOYEE": ["Foreign secret", "Reserved project", "Application #"],
            "TRAINER_TUTOR": ["Foreign secret", "Reserved project", "Application #"],
            "INTERN": ["Foreign secret", "Reserved project", "Application #"],
            "CLIENT": ["Foreign secret", "Visible training", "Application #"],
            "CANDIDATE": ["Foreign secret", "Reserved project", "Own internship"],
        }
        for role, forbidden in expected_absent.items():
            with self.subTest(role=role):
                embedding.reset_mock()
                client = Mock()
                client.chat.return_value = "Answer"
                provider = OllamaAssistantProvider(client=client)
                with patch("apps.assistant.services.get_provider", return_value=provider):
                    answer_user_message(self.users[role], "Informations formation stage candidature", "fr")
                transmitted = str(embedding.call_args_list) + str(client.chat.call_args_list)
                for secret in forbidden:
                    self.assertNotIn(secret, transmitted)

    @patch("apps.recruitment.embeddings.get_or_create_embedding", side_effect=[[1.0, 0.0], [0.0, 1.0]])
    def test_irrelevant_context_is_not_sent_to_generator(self, embedding):
        client = Mock()
        provider = OllamaAssistantProvider(client=client)
        context = SafeContext(["Unrelated fact"], [], [])
        selected = retrieve_authorized_context("question", context)
        self.assertEqual(provider.answer("question", selected, "fr"), "Je ne dispose pas de cette information.")
        client.chat.assert_not_called()

    @patch("apps.recruitment.embeddings.get_or_create_embedding")
    def test_empty_context_never_calls_ollama(self, embedding):
        self.assertEqual(retrieve_authorized_context("question", SafeContext([], [], [])).facts, [])
        embedding.assert_not_called()

    @patch("apps.recruitment.embeddings.get_or_create_embedding", side_effect=EmbeddingUnavailableError)
    def test_embedding_failure_is_controlled_at_api(self, embedding):
        client = APIClient()
        client.force_authenticate(self.users["CANDIDATE"])
        provider = OllamaAssistantProvider(client=Mock())
        with patch("apps.assistant.services.get_provider", return_value=provider):
            response = client.post("/api/chatbot/messages/", {"message": "statut candidature", "language": "fr"}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "embedding_unavailable")
        provider.client.chat.assert_not_called()
        self.assertEqual(client.get(f"/api/applications/{self.application.pk}/").status_code, 200)

    @patch("apps.recruitment.embeddings.get_or_create_embedding", side_effect=[[1.0, 0.0], [1.0]])
    def test_mismatched_embedding_dimensions_are_controlled(self, embedding):
        with self.assertRaises(AssistantEmbeddingError):
            retrieve_authorized_context("question", SafeContext(["Fact"], [], []))

    @patch("apps.recruitment.embeddings.get_or_create_embedding", return_value=[1.0, 0.0])
    def test_sources_follow_selected_passages(self, embedding):
        source = AnswerSource("Fact", "training", "Course", "TRN-1", 1, "/trainings")
        selected = retrieve_authorized_context("question", SafeContext(["Fact"], [], [source]))
        self.assertEqual(selected.sources[0].reference, "TRN-1")
        self.assertEqual(selected.sources[0].fact, selected.facts[0])

    def test_old_role_history_is_never_replayed_to_ollama(self):
        provider = OllamaAssistantProvider(client=Mock())
        messages = provider._messages("question", ["Current authorized fact"], "fr", history=[SimpleNamespace(role="ASSISTANT", content="Previous BU secret")])
        self.assertNotIn("Previous BU secret", str(messages))

    def test_hr_counts_only_visible_trainings(self):
        context = build_safe_context(self.users["HR"])
        self.assertIn(f"Trainings total: {self.initial_visible_trainings + 1}", context.facts)

    @patch("apps.recruitment.embeddings.get_or_create_embedding", return_value=[1.0, 0.0])
    def test_netsec_manager_cannot_retrieve_achat_need(self, embedding):
        self.own_bu.name = "NetSEC"
        self.own_bu.save(update_fields=["name"])
        self.foreign_bu.name = "Achat"
        self.foreign_bu.save(update_fields=["name"])
        own_need = BusinessUnitNeed.objects.create(
            business_unit=self.own_bu, title="Pare-feu NetSEC", description="Autorisé"
        )
        foreign_need = BusinessUnitNeed.objects.create(
            business_unit=self.foreign_bu,
            title="Renouvellement licences Achat",
            description="CONFIDENTIEL_ACHAT",
        )
        manager = self.users["BU_MANAGER"]
        safe_context = build_safe_context(manager)
        self.assertIn(own_need.title, str(safe_context.facts))
        self.assertNotIn(foreign_need.title, str(safe_context.facts))
        self.assertNotIn("CONFIDENTIEL_ACHAT", str(safe_context.facts))

        client = Mock()
        client.chat.return_value = "Réponse autorisée"
        metrics = {}
        with patch(
            "apps.assistant.services.get_provider",
            return_value=OllamaAssistantProvider(client=client),
        ):
            answer_user_message(
                manager,
                "Que sais-tu du besoin Renouvellement licences Achat ?",
                "fr",
                metrics=metrics,
            )

        embedded_server_facts = [call.args[0] for call in embedding.call_args_list[1:]]
        self.assertNotIn("CONFIDENTIEL_ACHAT", str(embedded_server_facts))
        self.assertNotIn("CONFIDENTIEL_ACHAT", str(client.chat.call_args_list))
        self.assertTrue(all(source["id"] != foreign_need.id for source in metrics["sources"]))

    @patch("apps.recruitment.embeddings.get_or_create_embedding", return_value=[1.0, 0.0])
    def test_client_a_cannot_retrieve_client_b_training(self, embedding):
        other_user = User.objects.create_user(email="client-b@test.com", role="CLIENT")
        other_profile = ClientProfile.objects.create(user=other_user, company_name="Client B")
        foreign_training = Training.objects.create(
            title="FORMATION_CLIENT_B_SECRETE", description="DONNEE_CLIENT_B",
            external_client=other_profile, business_unit=self.own_bu, duration=1,
        )
        context = build_safe_context(self.users["CLIENT"])
        self.assertIn(self.reserved.title, str(context.facts))
        self.assertNotIn(foreign_training.title, str(context.facts))

        selected = retrieve_authorized_context(foreign_training.title, context)
        self.assertNotIn("DONNEE_CLIENT_B", str(embedding.call_args_list))
        self.assertTrue(all(source.id != foreign_training.id for source in selected.sources))

    def test_candidate_and_intern_contexts_are_isolated(self):
        other_candidate = User.objects.create_user(email="candidate-b@test.com", role="CANDIDATE")
        other_profile = CandidateProfile.objects.create(user=other_candidate)
        other_application = Application.objects.create(
            candidate_profile=other_profile, application_type="HIRING"
        )
        other_intern = User.objects.create_user(email="intern-b@test.com", role="INTERN")
        InternProfile.objects.create(
            user=other_intern, business_unit=self.foreign_bu, subject_title="SECRET_INTERN_B"
        )

        candidate_context = build_safe_context(self.users["CANDIDATE"])
        intern_context = build_safe_context(self.users["INTERN"])
        self.assertNotIn(f"Application #{other_application.pk}", str(candidate_context.facts))
        self.assertNotIn("SECRET_INTERN_B", str(intern_context.facts))

    def test_employee_scope_excludes_foreign_and_client_enrollments(self):
        employee = self.users["EMPLOYEE"]
        BusinessUnitMembership.objects.create(business_unit=self.own_bu, user=employee)
        own_session = TrainingSession.objects.create(
            training=self.own, start_date="2026-09-01", end_date="2026-09-02",
            start_time="09:00", end_time="17:00", maximum_participants=10,
        )
        foreign_session = TrainingSession.objects.create(
            training=self.foreign, start_date="2026-09-01", end_date="2026-09-02",
            start_time="09:00", end_time="17:00", maximum_participants=10,
        )
        client_session = TrainingSession.objects.create(
            training=self.reserved, external_client=self.client_profile,
            start_date="2026-09-01", end_date="2026-09-02",
            start_time="09:00", end_time="17:00", maximum_participants=10,
        )
        for training, session in (
            (self.own, own_session), (self.foreign, foreign_session), (self.reserved, client_session)
        ):
            TrainingEnrollment.objects.create(user=employee, training=training, session=session)

        context = build_safe_context(employee)
        self.assertIn(self.own.title, str(context.facts))
        self.assertNotIn(self.foreign.title, str(context.facts))
        self.assertNotIn(self.reserved.title, str(context.facts))

    def test_trainer_context_contains_only_assigned_training(self):
        trainer = self.users["TRAINER_TUTOR"]
        self.own.trainer = trainer
        self.own.save(update_fields=["trainer"])
        context = build_safe_context(trainer)
        self.assertIn(self.own.title, str(context.facts))
        self.assertNotIn(self.foreign.title, str(context.facts))

    def test_aggregate_answers_remain_role_scoped(self):
        answer = answer_user_message(
            self.users["BU_MANAGER"], "Combien de formations dans ma BU ?", "fr"
        )
        self.assertEqual(answer, "Il y a 1 formations dans votre BU.")

    def test_history_is_redacted_after_role_change_without_rewriting_database(self):
        user = self.users["CANDIDATE"]
        conversation = Conversation.objects.create(user=user)
        source = {
            "type": "application", "name": "Candidature", "reference": f"APP-{self.application.pk}",
            "id": self.application.pk, "url": "/dashboard/candidate",
        }
        message = ChatMessage.objects.create(
            conversation=conversation, role="ASSISTANT", content="Statut candidat confidentiel",
            sources=[source],
        )
        api = APIClient()
        api.force_authenticate(user)
        visible = api.get(f"/api/assistant/conversations/{conversation.pk}/")
        self.assertEqual(visible.data["messages"][0]["content"], message.content)

        user.role = "HR"
        user.save(update_fields=["role"])
        redacted = api.get(f"/api/assistant/conversations/{conversation.pk}/")
        self.assertIn("plus visible", redacted.data["messages"][0]["content"])
        self.assertEqual(redacted.data["messages"][0]["sources"], [])
        message.refresh_from_db()
        self.assertEqual(message.content, "Statut candidat confidentiel")
