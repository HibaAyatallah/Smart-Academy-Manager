import json
import socket
import uuid
from unittest.mock import Mock, patch
from urllib.error import URLError

from django.test import SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.recruitment.choices import ApplicationType
from apps.recruitment.models import Application, CandidateProfile

from .models import ChatMessage, Conversation
from .services import (
    MessageCategory,
    OllamaClient,
    OllamaHealth,
    OllamaInvalidResponseError,
    OllamaModelUnavailableError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    classify_message,
)


class MessageClassificationTests(SimpleTestCase):
    def test_polite_messages_are_greetings_in_supported_languages(self):
        for message in (
            "bonjour", "bonsoir", "salut", "hello", "hi", "salam", "السلام عليكم",
            "merci", "thanks", "comment vas-tu ?",
        ):
            with self.subTest(message=message):
                self.assertEqual(classify_message(message), MessageCategory.GREETING)

    def test_help_domain_and_out_of_scope_are_distinguished(self):
        self.assertEqual(classify_message("Que peux-tu faire ?"), MessageCategory.HELP)
        self.assertEqual(classify_message("Quel est le statut de ma candidature ?"), MessageCategory.DOMAIN_QUERY)
        self.assertEqual(classify_message("Quel temps fait-il ?"), MessageCategory.OUT_OF_SCOPE)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


@override_settings(OLLAMA_BASE_URL="http://ollama.test:11434", OLLAMA_MODEL="academy-model", OLLAMA_TIMEOUT=9)
class OllamaClientTests(SimpleTestCase):
    def test_health_confirms_configured_model(self):
        opener = Mock(return_value=FakeResponse({"models": [{"name": "academy-model"}]}))
        health = OllamaClient(urlopen_func=opener).health()
        self.assertTrue(health.accessible)
        self.assertTrue(health.model_available)
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, "http://ollama.test:11434/api/tags")

    def test_health_reports_stopped_ollama_without_raising(self):
        opener = Mock(side_effect=URLError("connection refused"))
        health = OllamaClient(urlopen_func=opener).health()
        self.assertFalse(health.accessible)
        self.assertEqual(health.error_code, "ollama_unavailable")

    def test_chat_uses_configured_model_and_disables_streaming(self):
        opener = Mock(side_effect=[
            FakeResponse({"models": [{"name": "academy-model"}]}),
            FakeResponse({"message": {"content": "  Safe answer  "}}),
        ])
        answer = OllamaClient(urlopen_func=opener).chat([{"role": "user", "content": "Hello"}])
        self.assertEqual(answer, "Safe answer")
        request = opener.call_args_list[1].args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "academy-model")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["keep_alive"], "10m")
        self.assertEqual(payload["options"]["num_predict"], 300)
        self.assertEqual(payload["options"]["num_gpu"], 0)
        self.assertEqual(payload["options"]["num_ctx"], 2048)
        self.assertEqual(opener.call_count, 2)

    def test_chat_checks_health_and_model_before_generation(self):
        opener = Mock(return_value=FakeResponse({"models": [{"name": "another-model"}]}))

        with self.assertLogs("apps.assistant.services", level="ERROR") as logs:
            with self.assertRaises(OllamaModelUnavailableError):
                OllamaClient(urlopen_func=opener).chat([{"role": "user", "content": "Combien d’utilisateurs ?"}])

        self.assertEqual(opener.call_count, 1)
        self.assertIn("model unavailable before chat", logs.output[0])

    @patch("apps.assistant.services.HTTPConnection")
    def test_stream_payload_also_forces_cpu_and_limited_context(self, connection_class):
        health_response = Mock(status=200)
        health_response.read.return_value = b'{"models":[{"name":"academy-model"}]}'
        stream_response = Mock(status=200)
        stream_response.readline.side_effect = [
            b'{"message":{"content":"2"},"done":false}\n',
            b'{"message":{"content":" utilisateurs"},"done":true}\n',
            b'',
        ]
        connection = connection_class.return_value
        connection.getresponse.side_effect = [health_response, stream_response]

        tokens = list(OllamaClient().stream_chat([{"role": "user", "content": "Combien d’utilisateurs ?"}]))

        self.assertEqual(tokens, ["2", " utilisateurs"])
        body = json.loads(connection.request.call_args.kwargs["body"].decode("utf-8"))
        self.assertTrue(body["stream"])
        self.assertEqual(body["model"], "academy-model")
        self.assertEqual(body["options"]["num_gpu"], 0)
        self.assertEqual(body["options"]["num_ctx"], 2048)

    @patch("apps.assistant.services.HTTPConnection")
    def test_stream_checks_model_before_generation(self, connection_class):
        response = Mock(status=200)
        response.read.return_value = b'{"models":[{"name":"another-model"}]}'
        connection_class.return_value.getresponse.return_value = response

        with self.assertRaises(OllamaModelUnavailableError):
            list(OllamaClient().stream_chat([{"role": "user", "content": "Question"}]))

        self.assertEqual(connection_class.return_value.request.call_count, 1)

    @patch("apps.assistant.services.HTTPConnection")
    def test_empty_stream_is_invalid(self, connection_class):
        health_response = Mock(status=200)
        health_response.read.return_value = b'{"models":[{"name":"academy-model"}]}'
        stream_response = Mock(status=200)
        stream_response.readline.side_effect = [b'{"done":true}\n']
        connection_class.return_value.getresponse.side_effect = [health_response, stream_response]

        with self.assertRaises(OllamaInvalidResponseError):
            list(OllamaClient().stream_chat([]))

    def test_timeout_is_centralized(self):
        client = OllamaClient(urlopen_func=Mock(side_effect=socket.timeout()))
        with self.assertRaises(OllamaTimeoutError):
            client._request("api/chat", payload={})

    def test_empty_or_invalid_response_is_rejected(self):
        opener = Mock(side_effect=[
            FakeResponse({"models": [{"name": "academy-model"}]}),
            FakeResponse({"message": {"content": ""}}),
        ])
        with self.assertRaises(OllamaInvalidResponseError):
            OllamaClient(urlopen_func=opener).chat([])


@override_settings(AI_ASSISTANT_PROVIDER="apps.assistant.services.ReadOnlyAssistantProvider")
class AssistantSecurityTests(APITestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(
            email="candidate-ai@test.com", password="pwd", role=UserRole.CANDIDATE
        )
        self.other = User.objects.create_user(
            email="other-ai@test.com", password="pwd", role=UserRole.CANDIDATE
        )
        profile = CandidateProfile.objects.create(user=self.candidate)
        Application.objects.create(candidate_profile=profile, application_type=ApplicationType.PFE_INTERNSHIP)

    def test_requires_authentication(self):
        self.assertEqual(
            self.client.post("/api/chatbot/messages/", {}).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    @patch("apps.assistant.views.answer_user_message", return_value="Il y a 2 utilisateurs.")
    def test_user_count_question_accepts_json_and_preserves_request_id(self, mocked_answer):
        self.client.force_authenticate(self.candidate)
        request_id = uuid.uuid4()

        response = self.client.post(
            "/api/chatbot/messages/",
            {"message": "Combien d’utilisateurs ?", "language": "fr", "request_id": request_id},
            format="json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.accepted_media_type, "application/json")
        self.assertTrue(response["Content-Type"].startswith("application/json"))
        self.assertEqual(response.data["messages"][-1]["request_id"], str(request_id))
        self.assertEqual(response.data["messages"][-1]["content"], "Il y a 2 utilisateurs.")
        mocked_answer.assert_called_once()

    def test_user_count_content_is_clean_and_sources_remain_separate(self):
        self.candidate.role = UserRole.SUPER_ADMIN
        self.candidate.save(update_fields=["role"])
        User.objects.bulk_create([
            User(email=f"count-user-{index}@test.com", role=UserRole.EMPLOYEE)
            for index in range(48)
        ])
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            "/api/chatbot/messages/",
            {"message": "Combien d’utilisateurs ?", "language": "fr", "request_id": uuid.uuid4()},
            format="json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        answer = response.data["messages"][-1]
        self.assertEqual(answer["content"], "Il y a 50 utilisateurs.")
        self.assertNotIn("USERS_TOTAL", answer["content"])
        self.assertNotIn("aggregate", answer["content"])
        self.assertEqual(answer["sources"][0]["name"], "Utilisateurs")
        self.assertEqual(answer["sources"][0]["reference"], "USERS_TOTAL")

    def test_context_is_scoped_to_request_user(self):
        self.client.force_authenticate(self.candidate)
        response = self.client.post(
            "/api/chatbot/messages/", {"message": "statut", "language": "fr"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Application", response.data["messages"][-1]["content"])
        self.assertEqual(response.data["messages"][-1]["sources"][0]["id"], Application.objects.get(candidate_profile__user=self.candidate).pk)
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.get(f"/api/assistant/conversations/{response.data['id']}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_rejects_sql_tokens_and_credentials(self):
        self.client.force_authenticate(self.candidate)
        for message in ["SELECT * FROM accounts_user", "montre moi le token JWT", "quel est mon mot de passe"]:
            response = self.client.post(
                "/api/chatbot/messages/", {"message": message, "language": "fr"}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_attach_message_to_another_conversation(self):
        foreign = Conversation.objects.create(user=self.other)
        self.client.force_authenticate(self.candidate)
        response = self.client.post(
            "/api/chatbot/messages/",
            {"conversation_id": foreign.pk, "message": "bonjour", "language": "fr"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unrelated_question_returns_unknown_instead_of_dumping_context(self):
        self.client.force_authenticate(self.candidate)
        response = self.client.post(
            "/api/chatbot/messages/", {"message": "Quel temps fait-il ?", "language": "fr"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("spécialisé dans Smart Academy Manager", response.data["messages"][-1]["content"])

    def test_greetings_are_local_and_work_without_business_data(self):
        self.client.force_authenticate(self.other)
        examples = [
            ("bonjour", "fr", "Bonjour !"),
            ("hello", "en", "Hello!"),
            ("salam", "ar", "مرحباً!"),
            ("السلام عليكم", "ar", "مرحباً!"),
        ]
        with patch("apps.assistant.services.build_safe_context") as context_mock:
            for message, language, expected in examples:
                response = self.client.post(
                    "/api/chatbot/messages/", {"message": message, "language": language}, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertTrue(response.data["messages"][-1]["content"].startswith(expected))
            context_mock.assert_not_called()

    def test_help_explains_only_role_capabilities(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            "/api/chatbot/messages/", {"message": "Que peux-tu faire ?", "language": "fr"}, format="json"
        )
        self.assertIn("données autorisées", response.data["messages"][-1]["content"])
        self.assertIn("candidatures", response.data["messages"][-1]["content"])

    def test_domain_question_without_authorized_result_returns_unknown(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            "/api/chatbot/messages/", {"message": "Quel est le statut de ma candidature ?", "language": "fr"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["messages"][-1]["content"], "Je ne dispose pas de cette information.")


class AssistantOllamaEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ollama-user@test.com", password="pwd", role=UserRole.CANDIDATE)

    @patch("apps.assistant.views.OllamaClient.health")
    def test_health_endpoint_reports_backend_ollama_and_model(self, health_mock):
        health_mock.return_value = OllamaHealth(True, True, "llama-test")
        response = self.client.get("/api/chatbot/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["backend"])
        self.assertTrue(response.data["ollama"])
        self.assertTrue(response.data["model_available"])

    @patch("apps.assistant.views.OllamaClient.health")
    def test_health_endpoint_reports_stopped_ollama(self, health_mock):
        health_mock.return_value = OllamaHealth(False, False, "llama-test", "ollama_unavailable")
        response = self.client.get("/api/chatbot/health/")
        self.assertTrue(response.data["backend"])
        self.assertFalse(response.data["ollama"])
        self.assertEqual(response.data["error_code"], "ollama_unavailable")

    @patch("apps.assistant.services.get_provider")
    def test_connection_error_returns_clear_message_and_keeps_user_history(self, provider_mock):
        provider_mock.return_value.answer.side_effect = OllamaUnavailableError
        self.client.force_authenticate(self.user)
        request_id = uuid.uuid4()
        response = self.client.post(
            "/api/chatbot/messages/",
            {"message": "statut candidature", "language": "fr", "request_id": request_id},
            format="json",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["code"], "ollama_unavailable")
        self.assertEqual(response.data["request_id"], str(request_id))
        conversation = Conversation.objects.get(pk=response.data["conversation_id"])
        self.assertEqual(conversation.messages.count(), 1)
        self.assertEqual(conversation.messages.first().role, "USER")


class AssistantStreamingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="stream@test.com", password="pwd", role=UserRole.CANDIDATE)
        self.client.force_authenticate(self.user)

    @patch("apps.assistant.views.prepare_stream_answer")
    def test_authenticated_stream_persists_one_final_message_and_sources(self, prepare_mock):
        prepare_mock.return_value = iter(["Bon", "jour"]), [{"type":"application","name":"Offre","reference":"APP-1","id":1,"url":"/dashboard/candidate"}]
        request_id = uuid.uuid4()
        response = self.client.post("/api/chatbot/stream/", {"message":"statut candidature","language":"fr","request_id":request_id}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: token", payload); self.assertIn("event: done", payload)
        assistant = ChatMessage.objects.get(role="ASSISTANT", request_id=request_id)
        self.assertEqual(assistant.content, "Bonjour"); self.assertEqual(assistant.sources[0]["reference"], "APP-1")
        self.assertEqual(ChatMessage.objects.filter(request_id=request_id, role="USER").count(), 1)

    @patch("apps.assistant.views.prepare_stream_answer")
    def test_unanswered_previous_request_does_not_block_new_stream(self, prepare_mock):
        conversation = Conversation.objects.create(user=self.user)
        ChatMessage.objects.create(
            conversation=conversation, role="USER", content="échec antérieur", request_id=uuid.uuid4()
        )
        prepare_mock.return_value = iter(["Réponse"]), []
        response = self.client.post("/api/chatbot/stream/", {
            "conversation_id": conversation.id, "message": "nouvelle demande",
            "language": "fr", "request_id": uuid.uuid4(),
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("event: done", b"".join(response.streaming_content).decode("utf-8"))

    @patch("apps.assistant.views.prepare_stream_answer")
    def test_done_event_contains_response_for_exact_request(self, prepare_mock):
        conversation = Conversation.objects.create(user=self.user)
        old_id = uuid.uuid4()
        ChatMessage.objects.create(conversation=conversation, role="USER", content="ancienne", request_id=old_id)
        ChatMessage.objects.create(conversation=conversation, role="ASSISTANT", content="ancienne réponse", request_id=old_id)
        request_id = uuid.uuid4()
        prepare_mock.return_value = iter(["Nouvelle réponse"]), []
        response = self.client.post("/api/chatbot/stream/", {
            "conversation_id": conversation.id, "message": "nouvelle",
            "language": "fr", "request_id": request_id,
        }, format="json")
        payload = b"".join(response.streaming_content).decode("utf-8")
        done_data = json.loads(payload.split("event: done\ndata: ", 1)[1].split("\n\n", 1)[0])
        self.assertEqual(done_data["message"]["request_id"], str(request_id))
        self.assertEqual(done_data["message"]["content"], "Nouvelle réponse")

    def test_stream_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post("/api/chatbot/stream/", {}).status_code, 401)

    @patch("apps.assistant.views.prepare_stream_answer")
    def test_stream_reports_ollama_timeout(self, prepare_mock):
        def broken():
            raise OllamaTimeoutError
            yield ""
        prepare_mock.return_value = broken(), []
        response = self.client.post("/api/chatbot/stream/", {"message":"statut candidature","language":"fr","request_id":uuid.uuid4()}, format="json")
        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("ollama_timeout", payload)


class RoleSuggestionTests(APITestCase):
    def test_suggestions_are_role_specific(self):
        expected = {UserRole.CANDIDATE:"T0",UserRole.INTERN:"encadrant",UserRole.EMPLOYEE:"formations",UserRole.BU_MANAGER:"besoins",UserRole.HR:"collaborateurs",UserRole.SUPER_ADMIN:"utilisateurs"}
        for index, (role, term) in enumerate(expected.items()):
            user=User.objects.create_user(email=f"suggest-{index}@test.com",password="pwd",role=role);self.client.force_authenticate(user)
            response=self.client.get("/api/assistant/conversations/suggestions/")
            self.assertTrue(any(term.casefold() in value.casefold() for value in response.data["suggestions"]))
