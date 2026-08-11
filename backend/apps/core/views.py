from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.throttling import UserRateThrottle

from apps.accounts.permissions import IsSuperAdminOnly

from .models import ContactMessage
from .serializers import ContactMessageAdminSerializer, ContactMessageSerializer


class ContactSubmissionRateThrottle(UserRateThrottle):
    scope = "public_submission"


class ContactMessageViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ContactMessage.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["status", "request_type"]
    search_fields = ["full_name", "email", "subject", "message"]

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsSuperAdminOnly()]

    def get_throttles(self):
        if self.action == "create":
            return [ContactSubmissionRateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == "create":
            return ContactMessageSerializer
        return ContactMessageAdminSerializer
