from rest_framework import mixins,viewsets,status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from .models import Conversation,ChatMessage
from .serializers import ConversationSerializer,AskSerializer
from .services import build_safe_context,get_provider
class ChatThrottle(UserRateThrottle):scope="chatbot"
class ConversationViewSet(mixins.ListModelMixin,mixins.RetrieveModelMixin,mixins.DestroyModelMixin,viewsets.GenericViewSet):
    queryset=Conversation.objects.none();serializer_class=ConversationSerializer;throttle_classes=[ChatThrottle]
    def get_queryset(self):return Conversation.objects.filter(user=self.request.user).prefetch_related("messages")
    @action(detail=False,methods=["get"])
    def suggestions(self,request):return Response({"suggestions":build_safe_context(request.user).suggestions})
    @action(detail=False,methods=["post"])
    def ask(self,request):
        serializer=AskSerializer(data=request.data);serializer.is_valid(raise_exception=True);data=serializer.validated_data
        if data.get("conversation_id"):
            conversation=self.get_queryset().filter(pk=data["conversation_id"]).first()
            if not conversation:return Response({"detail":"Conversation introuvable."},status=status.HTTP_404_NOT_FOUND)
            conversation.language=data["language"];conversation.save(update_fields=["language","updated_at"])
        else:conversation=Conversation.objects.create(user=request.user,language=data["language"])
        ChatMessage.objects.create(conversation=conversation,role="USER",content=data["message"])
        answer=get_provider().answer(data["message"],build_safe_context(request.user),data["language"])
        ChatMessage.objects.create(conversation=conversation,role="ASSISTANT",content=answer)
        return Response(self.get_serializer(conversation).data)
