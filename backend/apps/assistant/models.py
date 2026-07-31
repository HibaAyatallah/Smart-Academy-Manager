from django.conf import settings
from django.db import models
class Conversation(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="assistant_conversations")
    language=models.CharField(max_length=2,choices=[("fr","Français"),("en","English"),("ar","العربية")],default="fr")
    created_at=models.DateTimeField(auto_now_add=True);updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["-updated_at"]
class ChatMessage(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name="messages")
    role=models.CharField(max_length=12,choices=[("USER","User"),("ASSISTANT","Assistant")])
    content=models.TextField(max_length=4000);created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["created_at"]
