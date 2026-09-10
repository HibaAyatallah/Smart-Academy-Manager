from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.business_units.models import BusinessUnit
from apps.recruitment.embeddings import EmbeddingUnavailableError
from apps.recruitment.models import Application, CandidateProfile, InternProfile
from apps.trainings.models import ClientProfile, Training
from .services import (
    AnswerSource, AssistantEmbeddingError, OllamaAssistantProvider, SafeContext,
    answer_user_message, build_safe_context, retrieve_authorized_context,
)


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
