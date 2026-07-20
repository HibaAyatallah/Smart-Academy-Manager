from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import filters, status, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.roles import is_hr
from apps.accounts.throttles import PublicSubmissionRateThrottle

from .choices import ApplicationStatus, OfferStatus
from .models import (
    Application, ApplicationDocument, Interview, Offer,
    InternProfile, InternDocument, InternEvaluation
)
from .permissions import (
    CanManageOffersOrReadPublished,
    IsApplicationParticipant,
    IsRecruitmentManager,
    can_access_application_document,
    is_candidate,
    is_recruitment_manager,
    IsInternshipParticipant,
    is_bu_manager,
    is_employee,
    is_intern,
)
from .serializers import (
    ApplicationDocumentSerializer,
    ApplicationDocumentUploadSerializer,
    ApplicationRejectionSerializer,
    ApplicationSerializer,
    ApplicationStatusHistorySerializer,
    ApplicationTransitionSerializer,
    AuthenticatedApplicationCreateSerializer,
    InterviewSerializer,
    OfferSerializer,
    PublicApplicationCreateSerializer,
    ScheduleInterviewSerializer,
    ApplicationConversionSerializer,
    InternProfileSerializer,
    InternDocumentSerializer,
    InternEvaluationSerializer,
)


class OfferViewSet(viewsets.ModelViewSet):
    serializer_class = OfferSerializer
    permission_classes = [CanManageOffersOrReadPublished]

    def get_queryset(self):
        queryset = Offer.objects.select_related("business_unit", "created_by").all()
        user = self.request.user

        if is_recruitment_manager(user) or is_hr(user):
            return queryset

        return queryset.filter(status=OfferStatus.PUBLISHED)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        offer = self.get_object()
        offer.status = OfferStatus.PUBLISHED
        offer.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(offer).data)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        offer = self.get_object()
        offer.status = OfferStatus.CLOSED
        offer.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(offer).data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        offer = self.get_object()
        offer.status = OfferStatus.ARCHIVED
        offer.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(offer).data)
from .services import log_sensitive_action, transition_application


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsApplicationParticipant]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action == "public_submit":
            return [AllowAny()]
        if self.action in {
            "mark_under_review",
            "preselect",
            "mark_interview",
            "accept",
            "reject",
            "archive",
            "convert",
        }:
            return [IsRecruitmentManager()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Application.objects.select_related("candidate_profile__user", "reviewed_by")
            .prefetch_related("documents", "interviews", "status_history")
            .all()
        )
        user = self.request.user
        if is_recruitment_manager(user):
            queryset = queryset
        elif is_candidate(user):
            queryset = queryset.filter(candidate_profile__user=user)
        else:
            return queryset.none()

        application_type = self.request.query_params.get("application_type")
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search")
        offer_id = self.request.query_params.get("offer")
        business_unit_id = self.request.query_params.get("business_unit")

        if application_type:
            queryset = queryset.filter(application_type=application_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if offer_id:
            queryset = queryset.filter(offer_id=offer_id)
        if business_unit_id:
            queryset = queryset.filter(offer__business_unit_id=business_unit_id)
        if search:
            queryset = queryset.filter(
                Q(candidate_profile__user__email__icontains=search)
                | Q(candidate_profile__user__first_name__icontains=search)
                | Q(candidate_profile__user__last_name__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = AuthenticatedApplicationCreateSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        log_sensitive_action(
            request.user,
            application,
            "APPLICATION_SUBMITTED",
            {"candidate_email": application.candidate.email},
        )
        return Response(
            ApplicationSerializer(application, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        throttle_classes=[PublicSubmissionRateThrottle],
        url_path="public-submit",
    )
    def public_submit(self, request):
        serializer = PublicApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        log_sensitive_action(
            None,
            application,
            "APPLICATION_PUBLIC_SUBMITTED",
            {"candidate_email": application.candidate.email},
        )
        return Response(
            ApplicationSerializer(application, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "count": len(serializer.data),
                "next": None,
                "previous": None,
                "results": serializer.data,
            }
        )

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationStatusHistorySerializer(
            application.status_history.all(),
            many=True,
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="documents")
    def add_document(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data["file"]
        document = ApplicationDocument.objects.create(
            application=application,
            document_type=serializer.validated_data["document_type"],
            file=uploaded_file,
            original_name=uploaded_file.name,
            content_type=getattr(uploaded_file, "content_type", ""),
            size=uploaded_file.size,
            uploaded_by=request.user,
        )
        log_sensitive_action(
            request.user,
            application,
            "APPLICATION_DOCUMENT_UPLOADED",
            {"document_type": document.document_type},
        )
        return Response(
            ApplicationDocumentSerializer(
                document,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="mark-under-review")
    def mark_under_review(self, request, pk=None):
        return self._transition(request, ApplicationStatus.UNDER_REVIEW)

    @action(detail=True, methods=["post"], url_path="preselect")
    def preselect(self, request, pk=None):
        return self._transition(request, ApplicationStatus.PRESELECTED)

    @action(detail=True, methods=["post"], url_path="mark-interview")
    def mark_interview(self, request, pk=None):
        application = self.get_object()
        serializer = ScheduleInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = transition_application(
            application,
            ApplicationStatus.INTERVIEW,
            request.user,
            "Entretien planifié.",
        )
        interview = serializer.save(application=application, created_by=request.user)
        log_sensitive_action(
            request.user,
            application,
            "APPLICATION_INTERVIEW",
            {"interview_id": interview.pk},
        )
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        return self._transition(request, ApplicationStatus.ACCEPTED)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationRejectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = transition_application(
            application,
            ApplicationStatus.REJECTED,
            request.user,
            serializer.validated_data["reason"],
        )
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = transition_application(
            application,
            ApplicationStatus.ARCHIVED,
            request.user,
            serializer.validated_data.get("comment", ""),
        )
        return Response(self.get_serializer(application).data)

    def _transition(self, request, new_status):
        application = self.get_object()
        serializer = ApplicationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = transition_application(
            application,
            new_status,
            request.user,
            serializer.validated_data.get("comment", ""),
        )
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from .services import convert_accepted_application
        convert_accepted_application(application, serializer.validated_data, request.user)
        return Response({"detail": "Candidat converti avec succès."}, status=status.HTTP_200_OK)


class ApplicationDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApplicationDocumentSerializer
    permission_classes = [IsApplicationParticipant]

    def get_queryset(self):
        queryset = ApplicationDocument.objects.select_related(
            "application__candidate_profile__user",
            "uploaded_by",
        )
        user = self.request.user
        if is_recruitment_manager(user):
            return queryset
        if is_candidate(user):
            return queryset.filter(application__candidate_profile__user=user)
        return queryset.none()

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        if not can_access_application_document(request.user, document):
            raise PermissionDenied("Vous n'avez pas acces a ce document.")
        if not document.file:
            raise Http404
        response = FileResponse(
            document.file.open("rb"),
            as_attachment=request.query_params.get("download") == "1",
            filename=document.original_name,
            content_type=document.content_type or "application/octet-stream",
        )
        return response


class InterviewViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    permission_classes = [IsApplicationParticipant]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in {"create", "partial_update"}:
            return [IsRecruitmentManager()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = Interview.objects.select_related(
            "application__candidate_profile__user",
            "interviewer",
            "created_by",
        )
        user = self.request.user
        if is_recruitment_manager(user):
            return queryset
        if is_candidate(user):
            return queryset.filter(application__candidate_profile__user=user)
        return queryset.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InternProfileViewSet(viewsets.ModelViewSet):
    serializer_class = InternProfileSerializer
    permission_classes = [IsInternshipParticipant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business_unit", "supervisor", "current_status", "internship_type", "paid"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "school", "specialization", "subject_title"]
    ordering_fields = ["created_at", "internship_start", "internship_end", "progress"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        queryset = InternProfile.objects.select_related(
            "user", "source_application", "business_unit", "supervisor"
        ).prefetch_related("documents", "evaluations")
        user = self.request.user
        
        if is_recruitment_manager(user) or is_hr(user):
            return queryset
            
        if is_bu_manager(user):
            return queryset.filter(business_unit__manager_id=user.id)
            
        if is_intern(user):
            return queryset.filter(user_id=user.id)
            
        return queryset.filter(supervisor_id=user.id)

    def perform_update(self, serializer):
        user = self.request.user
        if is_employee(user) and not (is_recruitment_manager(user) or is_hr(user)):
            forbidden = set(serializer.validated_data) - {"progress", "current_status", "final_decision"}
            if forbidden:
                raise PermissionDenied("Le superviseur peut uniquement mettre à jour la progression et le statut.")
        serializer.save()


class InternDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = InternDocumentSerializer
    permission_classes = [IsInternshipParticipant]
    
    def get_queryset(self):
        queryset = InternDocument.objects.select_related("intern__user", "validator")
        user = self.request.user
        
        if is_recruitment_manager(user) or is_hr(user):
            return queryset
            
        if is_bu_manager(user):
            return queryset.filter(intern__business_unit__manager_id=user.id)
            
        if is_intern(user):
            return queryset.filter(intern__user_id=user.id)
            
        return queryset.filter(intern__supervisor_id=user.id)

    def perform_create(self, serializer):
        intern = serializer.validated_data["intern"]
        user = self.request.user
        if is_intern(user) and intern.user_id != user.id:
            raise PermissionDenied("Vous pouvez uniquement ajouter vos propres documents.")
        if is_employee(user) and not (is_recruitment_manager(user) or is_hr(user)) and intern.supervisor_id != user.id:
            raise PermissionDenied("Ce stagiaire ne vous est pas affecté.")
        serializer.save()

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.file:
            raise Http404
        return FileResponse(document.file.open("rb"), as_attachment=True, filename=document.file.name.rsplit("/", 1)[-1])

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_document(self, request, pk=None):
        if not (is_recruitment_manager(request.user) or is_hr(request.user)):
            raise PermissionDenied("Seuls le Super Admin et RH peuvent valider un document.")
        document = self.get_object()
        from django.utils import timezone
        document.is_validated = True
        document.validated_at = timezone.now()
        document.validator = request.user
        document.comment = request.data.get("comment", document.comment)
        document.save(update_fields=["is_validated", "validated_at", "validator", "comment"])
        return Response(self.get_serializer(document).data)


class InternEvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = InternEvaluationSerializer
    permission_classes = [IsInternshipParticipant]
    
    def get_queryset(self):
        queryset = InternEvaluation.objects.select_related("intern__user", "evaluator")
        user = self.request.user
        
        if is_recruitment_manager(user) or is_hr(user):
            return queryset
            
        if is_bu_manager(user):
            return queryset.filter(intern__business_unit__manager_id=user.id)
            
        if is_intern(user):
            return queryset.filter(intern__user_id=user.id)
            
        return queryset.filter(intern__supervisor_id=user.id)

    def perform_create(self, serializer):
        intern = serializer.validated_data["intern"]
        user = self.request.user
        if is_employee(user) and not (is_recruitment_manager(user) or is_hr(user)) and intern.supervisor_id != user.id:
            raise PermissionDenied("Ce stagiaire ne vous est pas affecté.")
        serializer.save(evaluator=user)

    def perform_update(self, serializer):
        evaluation = self.get_object()
        user = self.request.user
        if is_employee(user) and not (is_recruitment_manager(user) or is_hr(user)) and evaluation.evaluator_id != user.id:
            raise PermissionDenied("Vous pouvez uniquement modifier vos propres évaluations.")
        if "intern" in serializer.validated_data and serializer.validated_data["intern"].id != evaluation.intern_id:
            raise PermissionDenied("Une évaluation ne peut pas être réaffectée à un autre stagiaire.")
        serializer.save()
