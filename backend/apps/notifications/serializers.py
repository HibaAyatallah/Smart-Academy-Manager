from rest_framework import serializers
from .models import AuditLog, Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    class Meta:
        model = Notification
        fields = ["id", "category", "title", "message", "link", "target_type", "target_id", "is_read", "read_at", "created_at"]
        read_only_fields = fields
    def get_is_read(self, obj): return obj.read_at is not None

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["approvals", "assignments", "sessions", "evaluations", "documents", "certificates", "updated_at"]
        read_only_fields = ["updated_at"]

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "actor_email", "method", "path", "action", "target_type", "target_id", "status_code", "ip_address", "metadata", "created_at"]
        read_only_fields = fields
