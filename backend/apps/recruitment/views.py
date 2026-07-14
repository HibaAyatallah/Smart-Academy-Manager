from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .choices import ApplicationStatus
from .models import Application, ApplicationDocument, Interview
from .permissions import (
    IsApplicationParticipant,
    IsRecruitmentManager,
    can_access_application_document,
    is_candidate,
    is_recruitment_manager,
)
from .serializers import (
    ApplicationDocumentSerializer,
    ApplicationDocumentUploadSerializer,
    ApplicationRejectionSerializer,
    ApplicationSerializer,
    ApplicationStatusHistorySerializer,
    ApplicationTransitionSerializer,
    InterviewSerializer,
    PublicApplicationCreateSerializer,
    ScheduleInterviewSerializer,
)
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
            "schedule_interview",
            "complete_interview",
            "accept",
            "reject",
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

        if application_type:
            queryset = queryset.filter(application_type=application_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                Q(candidate_profile__user__email__icontains=search)
                | Q(candidate_profile__user__first_name__icontains=search)
                | Q(candidate_profile__user__last_name__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
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

    @action(detail=True, methods=["post"], url_path="schedule-interview")
    def schedule_interview(self, request, pk=None):
        application = self.get_object()
        serializer = ScheduleInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = transition_application(
            application,
            ApplicationStatus.INTERVIEW_SCHEDULED,
            request.user,
            "Entretien planifié.",
        )
        interview = serializer.save(application=application, created_by=request.user)
        log_sensitive_action(
            request.user,
            application,
            "APPLICATION_INTERVIEW_SCHEDULED",
            {"interview_id": interview.pk},
        )
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"], url_path="complete-interview")
    def complete_interview(self, request, pk=None):
        return self._transition(request, ApplicationStatus.INTERVIEW_COMPLETED)

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

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = transition_application(
            application,
            ApplicationStatus.CANCELLED,
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
