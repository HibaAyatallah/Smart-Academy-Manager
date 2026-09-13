from rest_framework import serializers

from .models import Conversation, ChatMessage
from .services import build_safe_context


HISTORY_REDACTED = {
    "fr": "Ce message historique n’est plus visible avec vos autorisations actuelles.",
    "en": "This historical message is no longer visible with your current permissions.",
    "ar": "لم تعد هذه الرسالة السابقة مرئية وفق صلاحياتك الحالية.",
}


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "sources", "request_id", "created_at"]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.role != "ASSISTANT" or not instance.sources or not request:
            return data
        cache_key = "_assistant_authorized_source_keys"
        if cache_key not in self.context:
            context = build_safe_context(request.user)
            self.context[cache_key] = {
                (source.type, source.reference, source.id) for source in context.sources
            }
        source_keys = {
            (source.get("type"), source.get("reference"), source.get("id"))
            for source in instance.sources if isinstance(source, dict)
        }
        if len(source_keys) != len(instance.sources) or not source_keys.issubset(self.context[cache_key]):
            language = getattr(instance.conversation, "language", "fr")
            data["content"] = HISTORY_REDACTED.get(language, HISTORY_REDACTED["fr"])
            data["sources"] = []
        return data


class ConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "language", "created_at", "updated_at", "messages"]
        read_only_fields = ["id", "created_at", "updated_at", "messages"]


class AskSerializer(serializers.Serializer):
    conversation_id=serializers.IntegerField(required=False)
    message=serializers.CharField(max_length=1000,trim_whitespace=True)
    language=serializers.ChoiceField(choices=["fr","en","ar"])
    request_id=serializers.UUIDField(required=False)
    def validate_message(self,value):
        blocked=["password","mot de passe","jwt","token","select ","insert ","delete ","update "]
        if any(term in value.lower() for term in blocked):raise serializers.ValidationError("Cette demande contient des données ou une action non autorisée.")
        return value


class ChatbotHealthSerializer(serializers.Serializer):
    backend = serializers.BooleanField()
    ollama = serializers.BooleanField()
    model = serializers.CharField(allow_blank=True)
    model_available = serializers.BooleanField()
    error_code = serializers.CharField(allow_null=True)
    streaming_supported = serializers.BooleanField()


class ChatbotErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    conversation_id = serializers.IntegerField()
