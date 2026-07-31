from django.db import transaction
from django.db.models import Q
from django.core.files.base import ContentFile
import uuid
from rest_framework import viewsets, filters, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Training, TrainingSession, ClientProfile, TrainingEnrollment, EnrollmentHistory, SessionAttendance, TrainingCertificate
from .serializers import (
    TrainingSerializer, TrainingSessionSerializer,
    ClientTrainingSerializer, ClientTrainingSessionSerializer,
    TrainingEnrollmentSerializer,
    TrainingEnrollmentCreateSerializer, ManagerDecisionSerializer,
    SuperAdminDecisionSerializer, DirectEnrollmentSerializer
)
from .permissions import IsSuperAdminOrReadOnly, IsClientProfile, IsNotClientProfile, IsTrainingOperationsUser, IsTrainingCatalogueUser
from apps.accounts.permissions import IsSuperAdminOnly
from apps.accounts.choices import UserRole
from .choices import TrainingStatus, SessionStatus, EnrollmentStatus


def _certificate_pdf(enrollment, number):
    name = (enrollment.user.get_full_name() or enrollment.user.email).replace("(", "").replace(")", "")
    title = enrollment.training.title.replace("(", "").replace(")", "")
    text = f"Certificate {number} - {name} completed {title}"
    stream = f"BT /F1 16 Tf 50 740 Td ({text}) Tj ET".encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >> stream\n".encode() + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(pdf)


def _issue_certificate(enrollment, user):
    certificate, created = TrainingCertificate.objects.get_or_create(
        enrollment=enrollment,
        defaults={"certificate_number": f"SAM-{uuid.uuid4().hex[:12].upper()}", "issued_by": user},
    )
    if created:
        certificate.file.save(f"{certificate.certificate_number}.pdf", ContentFile(_certificate_pdf(enrollment, certificate.certificate_number)), save=True)
    return certificate


class TrainingViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingSerializer
    permission_classes = [IsTrainingCatalogueUser, IsSuperAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["training_type", "category", "delivery_mode", "level", "status", "business_unit", "trainer"]
    search_fields = ["title", "description", "category", "objectives"]
    ordering_fields = ["created_at", "title"]
    ordering = ["title"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.role == UserRole.CLIENT:
            return Training.objects.none()
            
        qs = Training.objects.all().select_related("trainer", "business_unit", "external_client").prefetch_related("sessions")
        
        if user.role == UserRole.SUPER_ADMIN:
            return qs

        # HR: read-only access to the published internal catalogue only.
        # HR must NOT see DRAFT or ARCHIVED trainings, nor client-reserved trainings.
        if user.role == UserRole.HR:
            return qs.filter(
                status=TrainingStatus.PUBLISHED,
                external_client__isnull=True,
            )

        if user.role == UserRole.BU_MANAGER:
            bu_ids = user.managed_business_units.values_list("id", flat=True)
            return qs.filter(
                Q(external_client__isnull=True),
                Q(business_unit__isnull=True) | Q(business_unit__id__in=bu_ids)
            )
            
        if user.role == UserRole.TRAINER_TUTOR:
            return qs.filter(Q(trainer=user) | Q(sessions__trainer=user)).distinct()
            
        bu_ids = user.bu_memberships.filter(is_active=True).values_list("business_unit_id", flat=True)
        return qs.filter(
            status=TrainingStatus.PUBLISHED,
            external_client__isnull=True
        ).filter(
            Q(business_unit__isnull=True) | Q(business_unit__id__in=bu_ids)
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        training = self.get_object()
        training.status = TrainingStatus.PUBLISHED
        training.save(update_fields=['status', 'updated_at'])
        return Response({"status": "Training published"})

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        training = self.get_object()
        training.status = TrainingStatus.ARCHIVED
        training.save(update_fields=['status', 'updated_at'])
        return Response({"status": "Training archived"})


class TrainingSessionViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingSessionSerializer
    permission_classes = [IsTrainingCatalogueUser, IsSuperAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["training", "status", "trainer", "location", "external_client"]
    search_fields = ["training__title", "location"]
    ordering_fields = ["start_date", "start_time"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.role == UserRole.CLIENT:
            return TrainingSession.objects.none()
            
        qs = TrainingSession.objects.all().select_related("training", "trainer", "external_client")
        
        if user.role == UserRole.SUPER_ADMIN:
            return qs

        # HR: read-only access to open/planned/full sessions of published internal trainings.
        # HR must NOT see sessions of client-reserved trainings or cancelled/completed sessions.
        if user.role == UserRole.HR:
            return qs.filter(
                status__in=[SessionStatus.OPEN, SessionStatus.PLANNED, SessionStatus.FULL],
                external_client__isnull=True,
                training__status=TrainingStatus.PUBLISHED,
            )

        if user.role == UserRole.BU_MANAGER:
            bu_ids = user.managed_business_units.values_list("id", flat=True)
            return qs.filter(
                Q(external_client__isnull=True),
                Q(training__business_unit__isnull=True) | Q(training__business_unit__id__in=bu_ids)
            )
            
        if user.role == UserRole.TRAINER_TUTOR:
            return qs.filter(trainer=user)
            
        bu_ids = user.bu_memberships.filter(is_active=True).values_list("business_unit_id", flat=True)
        return qs.filter(
            status__in=[SessionStatus.OPEN, SessionStatus.PLANNED, SessionStatus.FULL],
            external_client__isnull=True
        ).filter(
            Q(training__business_unit__isnull=True) | Q(training__business_unit__id__in=bu_ids)
        )
        
    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.status in [SessionStatus.COMPLETED, SessionStatus.CANCELLED]:
            raise ValidationError("Cannot update a completed or cancelled session.")
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        session = self.get_object()
        session.status = SessionStatus.CANCELLED
        session.save(update_fields=['status', 'updated_at'])
        return Response({"status": "Session cancelled"})

    @action(detail=True, methods=['post'])
    def open_registration(self, request, pk=None):
        session = self.get_object()
        session.status = SessionStatus.OPEN
        session.save(update_fields=['status', 'updated_at'])
        return Response({"status": "Session registration opened"})

    @action(detail=True, methods=['post'])
    def close_registration(self, request, pk=None):
        session = self.get_object()
        session.status = SessionStatus.FULL
        session.save(update_fields=['status', 'updated_at'])
        return Response({"status": "Session registration closed"})
        
    @action(detail=True, methods=['post'], permission_classes=[IsNotClientProfile])
    def complete(self, request, pk=None):
        session = self.get_object()
        if request.user.role != UserRole.SUPER_ADMIN and not (request.user.role == UserRole.TRAINER_TUTOR and session.trainer_id == request.user.id):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        enrollments = session.enrollments.filter(status=EnrollmentStatus.ENROLLED)
        attendances = SessionAttendance.objects.filter(enrollment__in=enrollments)
        expected_records = enrollments.count() * ((session.end_date - session.start_date).days + 1)
        if attendances.filter(validated=False).exists() or attendances.count() != expected_records:
            return Response({"detail": "Chaque journée de chaque participant doit être renseignée et validée."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            for enrollment in enrollments:
                if attendances.filter(enrollment=enrollment, status__in=["PRESENT", "LATE"]).exists():
                    previous = enrollment.status
                    enrollment.status = enrollment.final_status = EnrollmentStatus.COMPLETED
                    enrollment.save(update_fields=["status", "final_status", "updated_at"])
                    EnrollmentHistory.objects.create(enrollment=enrollment, previous_status=previous, new_status=EnrollmentStatus.COMPLETED, changed_by=request.user, comment="Attendance validated")
                    _issue_certificate(enrollment, request.user)
            session.status = SessionStatus.COMPLETED
            session.save(update_fields=['status', 'updated_at'])
        return Response({"status": "Session completed", "certificates": TrainingCertificate.objects.filter(enrollment__session=session).count()})


class ClientTrainingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClientTrainingSerializer
    permission_classes = [IsClientProfile]
    
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.role != UserRole.CLIENT:
            return Training.objects.none()
        try:
            profile = user.client_profile
            return profile.reserved_trainings.all().prefetch_related("sessions")
        except ClientProfile.DoesNotExist:
            return Training.objects.none()


class ClientTrainingSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClientTrainingSessionSerializer
    permission_classes = [IsClientProfile]
    
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.role != UserRole.CLIENT:
            return TrainingSession.objects.none()
        try:
            profile = user.client_profile
            return profile.sessions.all()
        except ClientProfile.DoesNotExist:
            return TrainingSession.objects.none()


class TrainingEnrollmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTrainingOperationsUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "training", "session"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "training__title"]
    ordering_fields = ["requested_at", "created_at", "updated_at"]
    ordering = ["-requested_at"]

    def create(self, request, *args, **kwargs):
        if request.user.role == UserRole.EMPLOYEE:
            raise PermissionDenied(
                "Les collaborateurs ne peuvent pas accéder au workflow d'inscription."
            )
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = TrainingEnrollment.objects.select_related("user", "training", "session").prefetch_related("history")
        
        if user.role == UserRole.SUPER_ADMIN:
            return qs
            
        if user.role == UserRole.BU_MANAGER:
            managed_bus = user.managed_business_units.all()
            return qs.filter(Q(user__bu_memberships__business_unit__in=managed_bus, user__bu_memberships__is_active=True) | Q(user=user)).distinct()
            
        if user.role == UserRole.TRAINER_TUTOR:
            return qs.filter(Q(session__trainer=user) | Q(user=user))
            
        if user.role == UserRole.EMPLOYEE:
            bu_ids = user.bu_memberships.filter(is_active=True).values_list(
                "business_unit_id", flat=True
            )
            return qs.filter(user=user, training__business_unit_id__in=bu_ids)
        return qs.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return TrainingEnrollmentCreateSerializer
        return TrainingEnrollmentSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            enrollment = serializer.save(user=self.request.user)
            EnrollmentHistory.objects.create(
                enrollment=enrollment,
                new_status=enrollment.status,
                changed_by=self.request.user,
                comment="Demande initiale"
            )

    def _log_history(self, enrollment, previous_status, comment=""):
        EnrollmentHistory.objects.create(
            enrollment=enrollment,
            previous_status=previous_status,
            new_status=enrollment.status,
            changed_by=self.request.user,
            comment=comment
        )

    @action(detail=True, methods=["post"], permission_classes=[IsTrainingOperationsUser])
    def manager_approve(self, request, pk=None):
        enrollment = self.get_object()
        
        if enrollment.status != EnrollmentStatus.PENDING_MANAGER:
            return Response({"detail": "L'inscription n'est pas en attente de manager."}, status=status.HTTP_400_BAD_REQUEST)
            
        if request.user.role != UserRole.SUPER_ADMIN:
            if request.user.role != UserRole.BU_MANAGER:
                return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
            user_bus = enrollment.user.bu_memberships.filter(is_active=True).values_list('business_unit', flat=True)
            managed_bus = request.user.managed_business_units.all().values_list('id', flat=True)
            if not set(user_bus).intersection(set(managed_bus)):
                return Response({"detail": "Vous ne gérez pas l'unité de cet utilisateur."}, status=status.HTTP_403_FORBIDDEN)
            if enrollment.user == request.user:
                return Response({"detail": "Vous ne pouvez pas valider votre propre demande."}, status=status.HTTP_403_FORBIDDEN)
                
        serializer = ManagerDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            prev_status = enrollment.status
            enrollment.manager_decision = EnrollmentStatus.APPROVED
            enrollment.manager_comment = serializer.validated_data.get('comment', '')
            enrollment.manager_decided_by = request.user
            enrollment.status = EnrollmentStatus.PENDING_SUPER_ADMIN
            enrollment.final_status = EnrollmentStatus.PENDING_SUPER_ADMIN
            enrollment.save()
            
            self._log_history(enrollment, prev_status, enrollment.manager_comment)
            
        return Response(self.get_serializer(enrollment).data)



    @action(detail=True, methods=["post"], permission_classes=[IsTrainingOperationsUser])
    def manager_reject(self, request, pk=None):
        enrollment = self.get_object()
        
        if enrollment.status != EnrollmentStatus.PENDING_MANAGER:
            return Response({"detail": "L'inscription n'est pas en attente de manager."}, status=status.HTTP_400_BAD_REQUEST)
            
        if request.user.role != UserRole.SUPER_ADMIN:
            if request.user.role != UserRole.BU_MANAGER:
                return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
            user_bus = enrollment.user.bu_memberships.filter(is_active=True).values_list('business_unit', flat=True)
            managed_bus = request.user.managed_business_units.all().values_list('id', flat=True)
            if not set(user_bus).intersection(set(managed_bus)):
                return Response({"detail": "Vous ne gérez pas l'unité de cet utilisateur."}, status=status.HTTP_403_FORBIDDEN)
                
        serializer = ManagerDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            prev_status = enrollment.status
            enrollment.manager_decision = EnrollmentStatus.REJECTED_BY_MANAGER
            enrollment.manager_comment = serializer.validated_data.get('comment', '')
            enrollment.manager_decided_by = request.user
            enrollment.status = EnrollmentStatus.REJECTED_BY_MANAGER
            enrollment.final_status = EnrollmentStatus.REJECTED_BY_MANAGER
            enrollment.save()
            
            self._log_history(enrollment, prev_status, enrollment.manager_comment)
            
        return Response(self.get_serializer(enrollment).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdminOnly])
    def super_admin_approve(self, request, pk=None):
        enrollment = self.get_object()
        
        if enrollment.status != EnrollmentStatus.PENDING_SUPER_ADMIN:
            return Response({"detail": "L'inscription n'est pas en attente de super admin."}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = SuperAdminDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Check capacity again
            session = enrollment.session
            participant_count = session.enrollments.filter(status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]).count()
            if participant_count >= session.maximum_participants:
                return Response({"detail": "La capacité maximale de cette session est atteinte."}, status=status.HTTP_400_BAD_REQUEST)
                
            prev_status = enrollment.status
            enrollment.super_admin_decision = EnrollmentStatus.APPROVED
            enrollment.super_admin_comment = serializer.validated_data.get('comment', '')
            enrollment.super_admin_decided_by = request.user
            enrollment.status = EnrollmentStatus.ENROLLED
            enrollment.final_status = EnrollmentStatus.ENROLLED
            enrollment.save()
            
            self._log_history(enrollment, prev_status, enrollment.super_admin_comment)
            
            if participant_count + 1 >= session.maximum_participants:
                session.status = SessionStatus.FULL
                session.save()
            
        return Response(self.get_serializer(enrollment).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdminOnly])
    def super_admin_reject(self, request, pk=None):
        enrollment = self.get_object()
        
        if enrollment.status != EnrollmentStatus.PENDING_SUPER_ADMIN:
            return Response({"detail": "L'inscription n'est pas en attente de super admin."}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = SuperAdminDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            prev_status = enrollment.status
            enrollment.super_admin_decision = EnrollmentStatus.REJECTED_BY_SUPER_ADMIN
            enrollment.super_admin_comment = serializer.validated_data.get('comment', '')
            enrollment.super_admin_decided_by = request.user
            enrollment.status = EnrollmentStatus.REJECTED_BY_SUPER_ADMIN
            enrollment.final_status = EnrollmentStatus.REJECTED_BY_SUPER_ADMIN
            enrollment.save()
            
            self._log_history(enrollment, prev_status, enrollment.super_admin_comment)
            
        return Response(self.get_serializer(enrollment).data)

    @action(detail=False, methods=["post"], permission_classes=[IsSuperAdminOnly])
    def direct_enrollment(self, request):
        serializer = DirectEnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            user = serializer.validated_data['user']
            training = serializer.validated_data['training']
            session = serializer.validated_data['session']
            
            enrollment = TrainingEnrollment.objects.create(
                user=user,
                training=training,
                session=session,
                status=EnrollmentStatus.ENROLLED,
                final_status=EnrollmentStatus.ENROLLED,
                super_admin_decision=EnrollmentStatus.APPROVED,
                super_admin_decided_by=request.user,
                super_admin_comment="Direct Enrollment"
            )
            
            self._log_history(enrollment, "", "Direct Enrollment")
            
            participant_count = session.enrollments.filter(status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]).count()
            if participant_count >= session.maximum_participants:
                session.status = SessionStatus.FULL
                session.save()
                
        return Response(self.get_serializer(enrollment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdminOnly])
    def cancel(self, request, pk=None):
        enrollment = self.get_object()
        
        if enrollment.status in [EnrollmentStatus.COMPLETED, EnrollmentStatus.CANCELLED]:
            return Response({"detail": "Impossible d'annuler une inscription dans cet état."}, status=status.HTTP_400_BAD_REQUEST)
            
        with transaction.atomic():
            prev_status = enrollment.status
            enrollment.status = EnrollmentStatus.CANCELLED
            enrollment.final_status = EnrollmentStatus.CANCELLED
            enrollment.save()
            
            self._log_history(enrollment, prev_status, "Annulation par Super Admin")
            
            session = enrollment.session
            if session.status == SessionStatus.FULL:
                participant_count = session.enrollments.filter(status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]).count()
                if participant_count < session.maximum_participants:
                    session.status = SessionStatus.OPEN
                    session.save()
                    
        return Response(self.get_serializer(enrollment).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdminOnly])
    def complete(self, request, pk=None):
        enrollment = self.get_object()
        
        if enrollment.status != EnrollmentStatus.ENROLLED:
            return Response({"detail": "L'inscription doit être ENROLLED pour être complétée."}, status=status.HTTP_400_BAD_REQUEST)
            
        with transaction.atomic():
            prev_status = enrollment.status
            enrollment.status = EnrollmentStatus.COMPLETED
            enrollment.final_status = EnrollmentStatus.COMPLETED
            enrollment.save()
            
            self._log_history(enrollment, prev_status, "Validation de complétion")
            
        return Response(self.get_serializer(enrollment).data)
