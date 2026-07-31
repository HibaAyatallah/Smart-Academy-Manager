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
    filterset_fields = ["enrollment", "enrollment__session", "enrollment__training", "date", "status", "validated"]
    ordering = ["date", "enrollment__user__email"]

    def get_queryset(self):
        user = self.request.user
        qs = SessionAttendance.objects.select_related("enrollment__user", "enrollment__training", "enrollment__session").prefetch_related("history")
        if user.role == UserRole.SUPER_ADMIN:
            return qs
        if user.role == UserRole.BU_MANAGER:
            return qs.filter(enrollment__training__business_unit__manager=user)
        if user.role == UserRole.TRAINER_TUTOR:
            return qs.filter(enrollment__session__trainer=user)
        if user.role == UserRole.EMPLOYEE:
            bu_ids = user.bu_memberships.filter(is_active=True).values_list(
                "business_unit_id", flat=True
            )
            return qs.filter(
                enrollment__user=user,
                enrollment__training__business_unit_id__in=bu_ids,
            )
        return qs.filter(enrollment__user=user)

    def _can_manage(self, enrollment):
        user = self.request.user
        return (
            user.role == UserRole.SUPER_ADMIN
            or (user.role == UserRole.BU_MANAGER and enrollment.training.business_unit and enrollment.training.business_unit.manager_id == user.id)
            or (user.role == UserRole.TRAINER_TUTOR and enrollment.session.trainer_id == user.id)
        )

    def _is_self_service(self, enrollment):
        return (
            self.request.user.role == UserRole.EMPLOYEE
            and enrollment.user_id == self.request.user.id
            and self.request.user.bu_memberships.filter(
                is_active=True,
                business_unit_id=enrollment.training.business_unit_id,
            ).exists()
        )

    def _check_self_service_date(self, attendance_date):
        if attendance_date > timezone.localdate():
            raise PermissionDenied("Les présences futures ne peuvent pas être déclarées.")

    def perform_create(self, serializer):
        enrollment = serializer.validated_data["enrollment"]
        if not self._can_manage(enrollment) and not self._is_self_service(enrollment):
            raise PermissionDenied("Vous ne pouvez enregistrer que vos propres présences.")
        if self._is_self_service(enrollment):
            self._check_self_service_date(serializer.validated_data["date"])
        attendance = serializer.save(recorded_by=self.request.user)
        AttendanceHistory.objects.create(attendance=attendance, status=attendance.status, changed_by=self.request.user, note=attendance.note)

    def perform_update(self, serializer):
        current = self.get_object()
        if current.validated and not self._can_manage(current.enrollment):
            raise PermissionDenied("Une présence validée ne peut plus être modifiée.")
        if not self._can_manage(current.enrollment) and not self._is_self_service(current.enrollment):
            raise PermissionDenied("Vous ne pouvez modifier que vos propres présences.")
        if self._is_self_service(current.enrollment):
            self._check_self_service_date(serializer.validated_data.get("date", current.date))
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
