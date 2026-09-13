from django.utils import timezone
from time import perf_counter
from django.conf import settings
import uuid
import json
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .models import ChatMessage, Conversation
from .serializers import AskSerializer, ChatbotErrorSerializer, ChatbotHealthSerializer, ChatMessageSerializer, ConversationSerializer
from .services import (
    OllamaClient,
    OllamaInvalidResponseError,
    OllamaServiceError,
    answer_user_message,
    prepare_stream_answer,
    suggestions_for_role,
)


class ChatThrottle(UserRateThrottle):
    scope = "chatbot"


def process_message(request, queryset):
    request_started = perf_counter()
    serializer = AskSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    request_id = data.get("request_id") or uuid.uuid4()
    conversation_id = data.get("conversation_id")
    if conversation_id:
        conversation = queryset.filter(pk=conversation_id).first()
        if not conversation:
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)
        conversation.language = data["language"]
        conversation.save(update_fields=["language", "updated_at"])
    else:
        conversation = Conversation.objects.create(user=request.user, language=data["language"])

    completed = ChatMessage.objects.filter(conversation=conversation, request_id=request_id, role="ASSISTANT").first()
    if completed:
        return Response(ConversationSerializer(conversation, context={"request": request}).data)
    if ChatMessage.objects.filter(conversation=conversation, request_id=request_id, role="USER").exists():
        return Response({"detail": "Cette génération est déjà en cours.", "code": "generation_in_progress"}, status=409)
    history_started = perf_counter()
    history = list(
        reversed(list(ChatMessage.objects.filter(conversation=conversation).order_by("-created_at")[:settings.OLLAMA_MAX_HISTORY]))
    )
    history_ms = (perf_counter() - history_started) * 1000
    ChatMessage.objects.create(conversation=conversation, role="USER", content=data["message"], request_id=request_id)
    metrics = {}
    try:
        answer = answer_user_message(request.user, data["message"], data["language"], history=history, metrics=metrics)
    except OllamaServiceError as exc:
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])
        response = Response(
            {
                "code": exc.code,
                "detail": exc.user_message(data["language"]),
                "conversation_id": conversation.pk,
                "request_id": str(request_id),
            },
            status=exc.status_code,
        )
        response["Server-Timing"] = f"django;dur={history_ms:.1f}, total;dur={(perf_counter()-request_started)*1000:.1f}"
        return response
    ChatMessage.objects.create(conversation=conversation, role="ASSISTANT", content=answer, sources=metrics.get("sources", []), request_id=request_id)
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=["updated_at"])
    response = Response(ConversationSerializer(conversation, context={"request": request}).data)
    django_ms = history_ms + metrics.get("django_db_ms", 0)
    response["Server-Timing"] = (
        f"django;dur={django_ms:.1f}, context;dur={metrics.get('context_ms', 0):.1f}, "
        f"ollama;dur={metrics.get('ollama_ms', 0):.1f}, total;dur={(perf_counter()-request_started)*1000:.1f}"
    )
    return response


class ChatbotHealthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(responses=ChatbotHealthSerializer)
    def get(self, request):
        health = OllamaClient().health()
        return Response(
            {
                "backend": True,
                "ollama": health.accessible,
                "model": health.model,
                "model_available": health.model_available,
                "error_code": health.error_code or None,
                "streaming_supported": True,
            }
        )


class ChatbotMessageView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatThrottle]
    renderer_classes = [JSONRenderer]

    @extend_schema(
        request=AskSerializer,
        responses={200: ConversationSerializer, 502: ChatbotErrorSerializer, 503: ChatbotErrorSerializer, 504: ChatbotErrorSerializer},
    )
    def post(self, request):
        queryset = Conversation.objects.filter(user=request.user)
        return process_message(request, queryset)


class ChatbotStreamView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatThrottle]

    @extend_schema(
        request=AskSerializer,
        responses={200: ConversationSerializer, 409: ChatbotErrorSerializer},
    )
    def post(self, request):
        serializer = AskSerializer(data=request.data); serializer.is_valid(raise_exception=True); data = serializer.validated_data
        request_id = data.get("request_id") or uuid.uuid4()
        conversation = None
        if data.get("conversation_id"):
            conversation = Conversation.objects.filter(user=request.user, pk=data["conversation_id"]).first()
            if not conversation:
                return Response({"detail": "Conversation introuvable."}, status=404)
            conversation.language = data["language"]
            conversation.save(update_fields=["language", "updated_at"])
        else:
            conversation = Conversation.objects.create(user=request.user, language=data["language"])
        completed = ChatMessage.objects.filter(conversation=conversation, request_id=request_id, role="ASSISTANT").first()
        if completed:
            return Response(ConversationSerializer(conversation, context={"request": request}).data)
        if ChatMessage.objects.filter(conversation=conversation, role="USER", request_id=request_id).exists():
            return Response({"detail": "Cette génération est déjà en cours.", "code": "generation_in_progress"}, status=409)
        history = list(reversed(list(ChatMessage.objects.filter(conversation=conversation).order_by("-created_at")[:settings.OLLAMA_MAX_HISTORY])))
        ChatMessage.objects.create(conversation=conversation, role="USER", content=data["message"], request_id=request_id)

        def event(name, payload):
            return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        def generate():
            parts = []
            sources = []
            try:
                yield event("meta", {"conversation_id": conversation.pk, "request_id": str(request_id)})
                tokens, sources = prepare_stream_answer(request.user, data["message"], data["language"], history=history)
                for token in tokens:
                    parts.append(token)
                    yield event("token", {"request_id": str(request_id), "content": token})
                content = "".join(parts).strip()
                if not content:
                    raise OllamaInvalidResponseError
                message = ChatMessage.objects.create(conversation=conversation, role="ASSISTANT", content=content[:4000], sources=sources, request_id=request_id)
                conversation.updated_at = timezone.now(); conversation.save(update_fields=["updated_at"])
                yield event("done", {
                    "request_id": str(request_id),
                    "message": ChatMessageSerializer(message, context={"request": request}).data,
                })
            except GeneratorExit:
                cancelled = "".join(parts).strip() or {"fr":"Génération arrêtée.","en":"Generation stopped.","ar":"تم إيقاف التوليد."}[data["language"]]
                ChatMessage.objects.create(conversation=conversation, role="ASSISTANT", content=cancelled[:4000], sources=sources, request_id=request_id)
                conversation.updated_at = timezone.now(); conversation.save(update_fields=["updated_at"])
                raise
            except OllamaServiceError as exc:
                ChatMessage.objects.create(conversation=conversation, role="ASSISTANT", content=exc.user_message(data["language"]), request_id=request_id)
                conversation.updated_at = timezone.now(); conversation.save(update_fields=["updated_at"])
                yield event("error", {"request_id": str(request_id), "code": exc.code, "detail": exc.user_message(data["language"])})

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ConversationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Conversation.objects.none()
    serializer_class = ConversationSerializer
    throttle_classes = [ChatThrottle]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).prefetch_related("messages")

    @action(detail=False, methods=["get"])
    def suggestions(self, request):
        return Response({"suggestions": suggestions_for_role(request.user.role)})

    @action(detail=False, methods=["post"])
    def ask(self, request):
        """Backward-compatible endpoint; new clients use /api/chatbot/messages/."""
        return process_message(request, Conversation.objects.filter(user=request.user))
