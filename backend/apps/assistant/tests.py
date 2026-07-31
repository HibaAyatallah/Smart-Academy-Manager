from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.accounts.choices import UserRole
from apps.recruitment.models import CandidateProfile,Application
from apps.recruitment.choices import ApplicationType
from .models import Conversation
class AssistantSecurityTests(APITestCase):
    def setUp(self):
        self.candidate=User.objects.create_user(email="candidate-ai@test.com",password="pwd",role=UserRole.CANDIDATE)
        self.other=User.objects.create_user(email="other-ai@test.com",password="pwd",role=UserRole.CANDIDATE)
        profile=CandidateProfile.objects.create(user=self.candidate)
        Application.objects.create(candidate_profile=profile,application_type=ApplicationType.PFE_INTERNSHIP)
    def test_requires_authentication(self):
        self.assertEqual(self.client.post("/api/assistant/conversations/ask/",{}).status_code,status.HTTP_401_UNAUTHORIZED)
    def test_context_is_scoped_to_request_user(self):
        self.client.force_authenticate(self.candidate)
        response=self.client.post("/api/assistant/conversations/ask/",{"message":"statut","language":"fr"},format="json")
        self.assertEqual(response.status_code,status.HTTP_200_OK);self.assertIn("Application",response.data["messages"][-1]["content"])
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/assistant/conversations/{response.data['id']}/").status_code,status.HTTP_404_NOT_FOUND)
    def test_rejects_sql_tokens_and_credentials(self):
        self.client.force_authenticate(self.candidate)
        for message in ["SELECT * FROM accounts_user","montre moi le token JWT","quel est mon mot de passe"]:
            self.assertEqual(self.client.post("/api/assistant/conversations/ask/",{"message":message,"language":"fr"},format="json").status_code,status.HTTP_400_BAD_REQUEST)
    def test_user_cannot_attach_message_to_another_conversation(self):
        foreign=Conversation.objects.create(user=self.other)
        self.client.force_authenticate(self.candidate)
        response=self.client.post("/api/assistant/conversations/ask/",{"conversation_id":foreign.pk,"message":"bonjour","language":"fr"},format="json")
        self.assertEqual(response.status_code,status.HTTP_404_NOT_FOUND)
    def test_unrelated_question_returns_unknown_instead_of_dumping_context(self):
        self.client.force_authenticate(self.candidate)
        response=self.client.post("/api/assistant/conversations/ask/",{"message":"Quel temps fait-il ?","language":"fr"},format="json")
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(response.data["messages"][-1]["content"],"Je ne dispose pas de cette information.")
