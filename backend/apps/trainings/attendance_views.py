from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.choices import UserRole
from .models import AttendanceHistory, SessionAttendance, TrainingCertificate
from .serializers import SessionAttendanceSerializer, TrainingCertificateSerializer
from .permissions import IsTrainingOperationsUser


class SessionAttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = SessionAttendanceSerializer
    permission_classes = [IsTrainingOperationsUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["enrollment__session", "status", "validated"]
    ordering = ["enrollment__user__email"]

    def get_queryset(self):
        user = self.request.user
        qs = SessionAttendance.objects.select_related("enrollment__user", "enrollment__training", "enrollment__session").prefetch_related("history")
        if user.role == UserRole.SUPER_ADMIN:
            return qs
        if user.role == UserRole.TRAINER_TUTOR:
            return qs.filter(enrollment__session__trainer=user)
        return qs.filter(enrollment__user=user)

    def _can_manage(self, enrollment):
        user = self.request.user
        return user.role == UserRole.SUPER_ADMIN or (user.role == UserRole.TRAINER_TUTOR and enrollment.session.trainer_id == user.id)

    def perform_create(self, serializer):
        enrollment = serializer.validated_data["enrollment"]
        if not self._can_manage(enrollment):
            raise PermissionDenied("Only the assigned trainer or Super Admin can record attendance.")
        attendance = serializer.save(recorded_by=self.request.user)
        AttendanceHistory.objects.create(attendance=attendance, status=attendance.status, changed_by=self.request.user, note=attendance.note)

    def perform_update(self, serializer):
        if not self._can_manage(self.get_object().enrollment):
            raise PermissionDenied("Attendance is read-only for this role.")
        attendance = serializer.save(validated=False, validated_by=None, validated_at=None)
        AttendanceHistory.objects.create(attendance=attendance, status=attendance.status, changed_by=self.request.user, note=attendance.note)

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        attendance = self.get_object()
        if not self._can_manage(attendance.enrollment):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        attendance.validated, attendance.validated_by, attendance.validated_at = True, request.user, timezone.now()
        attendance.save(update_fields=["validated", "validated_by", "validated_at", "updated_at"])
        AttendanceHistory.objects.create(attendance=attendance, status=attendance.status, validated=True, changed_by=request.user, note=request.data.get("note", attendance.note))
        return Response(self.get_serializer(attendance).data)


class TrainingCertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrainingCertificateSerializer
    permission_classes = [IsTrainingOperationsUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["enrollment__session", "enrollment__training"]
    ordering = ["-issued_at"]

    def get_queryset(self):
        user = self.request.user
        qs = TrainingCertificate.objects.select_related("enrollment__user", "enrollment__training", "enrollment__session", "issued_by")
        if user.role == UserRole.SUPER_ADMIN:
            return qs
        if user.role == UserRole.TRAINER_TUTOR:
            return qs.filter(enrollment__session__trainer=user)
        return qs.filter(enrollment__user=user)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        certificate = self.get_object()
        return FileResponse(certificate.file.open("rb"), as_attachment=True, filename=f"{certificate.certificate_number}.pdf", content_type="application/pdf")
