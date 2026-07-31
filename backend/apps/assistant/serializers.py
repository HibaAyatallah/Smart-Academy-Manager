from rest_framework import serializers
from .models import Conversation,ChatMessage
class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:model=ChatMessage;fields=["id","role","content","created_at"];read_only_fields=fields
class ConversationSerializer(serializers.ModelSerializer):
    messages=ChatMessageSerializer(many=True,read_only=True)
    class Meta:model=Conversation;fields=["id","language","created_at","updated_at","messages"];read_only_fields=["id","created_at","updated_at","messages"]
class AskSerializer(serializers.Serializer):
    conversation_id=serializers.IntegerField(required=False)
    message=serializers.CharField(max_length=1000,trim_whitespace=True)
    language=serializers.ChoiceField(choices=["fr","en","ar"])
    def validate_message(self,value):
        blocked=["password","mot de passe","jwt","token","select ","insert ","delete ","update "]
        if any(term in value.lower() for term in blocked):raise serializers.ValidationError("Cette demande contient des données ou une action non autorisée.")
        return value
