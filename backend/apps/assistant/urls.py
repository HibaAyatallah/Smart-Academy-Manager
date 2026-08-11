from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatbotHealthView, ChatbotMessageView, ChatbotStreamView, ConversationViewSet

router = DefaultRouter()
router.register("assistant/conversations", ConversationViewSet, basename="assistant-conversation")

urlpatterns = [
    path("chatbot/health/", ChatbotHealthView.as_view(), name="chatbot-health"),
    path("chatbot/messages/", ChatbotMessageView.as_view(), name="chatbot-message"),
    path("chatbot/stream/", ChatbotStreamView.as_view(), name="chatbot-stream"),
    *router.urls,
]
