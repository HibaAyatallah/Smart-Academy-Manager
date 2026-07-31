from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.accounts.choices import UserRole
from .models import AuditLog, Notification, NotificationPreference
from .serializers import AuditLogSerializer, NotificationPreferenceSerializer, NotificationSerializer

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.none()
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["category"]
    ordering = ["-created_at"]
    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        unread = self.request.query_params.get("unread")
        return qs.filter(read_at__isnull=True) if unread in ["1", "true", "True"] else qs
    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        item = self.get_object(); item.read_at = item.read_at or timezone.now(); item.save(update_fields=["read_at"])
        return Response(self.get_serializer(item).data)
    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": count})

class NotificationPreferenceViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = NotificationPreference.objects.none()
    serializer_class = NotificationPreferenceSerializer
    def get_object(self):
        return NotificationPreference.objects.get_or_create(user=self.request.user)[0]

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.none()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["method", "status_code", "actor"]
    search_fields = ["actor_email", "path", "action", "target_type", "target_id"]
    ordering = ["-created_at"]
    def get_queryset(self):
        if self.request.user.role != UserRole.SUPER_ADMIN: return AuditLog.objects.none()
        return AuditLog.objects.all()
    def list(self, request, *args, **kwargs):
        if request.user.role != UserRole.SUPER_ADMIN: return Response({"detail":"Access denied."}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)
