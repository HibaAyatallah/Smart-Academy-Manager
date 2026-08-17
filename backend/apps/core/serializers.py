from rest_framework import serializers

from .models import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = (
            "id",
            "full_name",
            "email",
            "request_type",
            "subject",
            "message",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "status", "created_at")

    def validate_full_name(self, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Le nom doit contenir au moins 2 caractères.")
        return value

    def validate_subject(self, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 3:
            raise serializers.ValidationError("Le sujet doit contenir au moins 3 caractères.")
        return value

    def validate_message(self, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Le message doit contenir au moins 10 caractères.")
        return value


class ContactMessageAdminSerializer(ContactMessageSerializer):
    class Meta(ContactMessageSerializer.Meta):
        read_only_fields = ("id", "created_at", "full_name", "email", "request_type", "subject", "message")
