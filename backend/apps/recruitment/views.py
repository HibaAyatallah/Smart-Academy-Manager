import logging

from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import filters, status, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.throttles import PublicSubmissionRateThrottle
from apps.accounts.choices import UserRole

logger = logging.getLogger(__name__)

from .choices import ApplicationStatus, OfferStatus
from .models import (
    Application, ApplicationDocument, Interview, Offer,
    InternProfile, InternDocument, InternDocumentRequirement, InternEvaluation
)
from .permissions import (
    CanManageOffersOrReadPublished,
    IsApplicationParticipant,
    IsRecruitmentManager,
    can_access_application_document,
    is_candidate,
    is_recruitment_manager,
    IsInternshipParticipant,
    IsInternDocumentRequirementUser,
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
    InternDocumentRequirementSerializer,
    InternEvaluationSerializer,
    CVAnalysisSerializer,
    CVReviewSerializer,
)


class OfferViewSet(viewsets.ModelViewSet):
    serializer_class = OfferSerializer
    permission_classes = [CanManageOffersOrReadPublished]

    def get_queryset(self):
        queryset = Offer.objects.select_related("business_unit", "created_by").all()
        user = self.request.user

        if is_recruitment_manager(user):
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
from apps.notifications.services import queue_email


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsApplicationParticipant]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in {"public_submit", "preview_cv"}:
            return [AllowAny()]
        if self.action in {
            "mark_under_review",
            "preselect",
            "mark_interview",
            "accept",
            "reject",
            "archive",
            "convert",
            "match_offers",
            "review_match",
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

    @action(detail=True, methods=["post"], url_path="analyze-cv")
    def analyze_cv(self, request, pk=None):
        from .intelligence import extract_cv
        try:
            analysis = extract_cv(self.get_object(), force=request.data.get("force") is True)
        except ValueError as exc:
            raise DRFValidationError({"detail": str(exc)}) from exc
        return Response(CVAnalysisSerializer(analysis).data)

    @action(detail=True, methods=["get", "patch"], url_path="cv-analysis")
    def cv_analysis(self, request, pk=None):
        analysis = getattr(self.get_object(), "cv_analysis", None)
        if not analysis:
            raise DRFValidationError({"detail": "Analyse CV inexistante."})
        if request.method == "PATCH":
            if analysis.human_validated:
                raise DRFValidationError({"detail": "Les informations sont déjà validées. Relancez l’analyse pour les modifier."})
            serializer = CVReviewSerializer(analysis, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            first_name = serializer.validated_data.pop("first_name", None)
            last_name = serializer.validated_data.pop("last_name", None)
            analysis = serializer.save()
            user = analysis.application.candidate_profile.user
            changed = []
            if first_name is not None: user.first_name = first_name; changed.append("first_name")
            if last_name is not None: user.last_name = last_name; changed.append("last_name")
            if changed: user.save(update_fields=[*changed, "updated_at"])
        return Response(CVAnalysisSerializer(analysis).data)

    @action(detail=True, methods=["post"], url_path="upload-cv", parser_classes=[MultiPartParser, FormParser])
    def upload_cv(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationDocumentUploadSerializer(data={"document_type": "CV", "file": request.FILES.get("file")})
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        document = ApplicationDocument.objects.create(application=application, document_type="CV", file=uploaded,
            original_name=uploaded.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1], content_type=getattr(uploaded, "content_type", ""),
            size=uploaded.size, uploaded_by=request.user)
        try:
            from .intelligence import extract_cv
            analysis = extract_cv(application, force=True)
        except ValueError as exc:
            return Response({"document": ApplicationDocumentSerializer(document, context=self.get_serializer_context()).data,
                             "analysis": None, "analysis_error": str(exc)}, status=status.HTTP_201_CREATED)
        return Response({"document": ApplicationDocumentSerializer(document, context=self.get_serializer_context()).data,
                         "analysis": CVAnalysisSerializer(analysis).data, "analysis_error": ""}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="preview-cv", throttle_classes=[PublicSubmissionRateThrottle], parser_classes=[MultiPartParser, FormParser])
    def preview_cv(self, request):
        serializer = ApplicationDocumentUploadSerializer(data={"document_type": "CV", "file": request.FILES.get("file")})
        serializer.is_valid(raise_exception=True)
        from .intelligence import extract_cv_data
        try:
            data = extract_cv_data(serializer.validated_data["file"])
        except ValueError as exc:
            raise DRFValidationError({"detail": str(exc)}) from exc
        return Response(data)

    @action(detail=True, methods=["post"], url_path="match-offers")
    def match_offers(self, request, pk=None):
        from .intelligence import match_application
        try:
            matches = match_application(self.get_object())
        except ValueError as exc:
            raise DRFValidationError({"detail": str(exc)}) from exc
        match_data = [{"id": item.id, "offer": item.offer_id, "score": item.score,
                          "matched_skills": item.matched_skills, "missing_skills": item.missing_skills,
                          "explanation": item.explanation, "human_decision": item.human_decision}
                         for item in matches]
        recommendations = self.get_object().training_recommendations.select_related("training")
        return Response({"matches": match_data, "training_recommendations": [
            {"id": item.id, "training": item.training_id, "training_title": item.training.title,
             "score": item.score, "skill_gaps": item.skill_gaps, "explanation": item.explanation,
             "human_decision": item.human_decision} for item in recommendations
        ]})

    @action(detail=True, methods=["post"], url_path="validate-cv")
    def validate_cv(self, request, pk=None):
        analysis = getattr(self.get_object(), "cv_analysis", None)
        if not analysis:
            raise DRFValidationError({"detail": "Analyse CV inexistante."})
        serializer = CVReviewSerializer(analysis, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        first_name = serializer.validated_data.pop("first_name", None)
        last_name = serializer.validated_data.pop("last_name", None)
        analysis = serializer.save()
        profile = analysis.application.candidate_profile
        user = profile.user
        if first_name is not None: user.first_name = first_name
        if last_name is not None: user.last_name = last_name
        if analysis.email and analysis.email != user.email and not type(user).objects.filter(email=analysis.email).exclude(pk=user.pk).exists(): user.email = analysis.email
        if analysis.phone: profile.phone_number = analysis.phone
        if analysis.location: profile.address = analysis.location
        user.save(update_fields=["first_name", "last_name", "email", "updated_at"])
        profile.save(update_fields=["phone_number", "address", "updated_at"])
        analysis.human_validated = True
        analysis.validated_by = request.user
        analysis.validated_at = timezone.now()
        analysis.save(update_fields=["human_validated", "validated_by", "validated_at", "updated_at"])
        return Response(CVAnalysisSerializer(analysis).data)

    @action(detail=True, methods=["post"], url_path="review-match")
    def review_match(self, request, pk=None):
        from .models import ApplicationMatch
        decision = request.data.get("decision")
        if decision not in {"APPROVED", "REJECTED"}:
            raise DRFValidationError({"decision": "Décision attendue: APPROVED ou REJECTED."})
        match = ApplicationMatch.objects.filter(application=self.get_object(), pk=request.data.get("match_id")).first()
        if not match:
            raise DRFValidationError({"match_id": "Résultat introuvable."})
        match.human_decision = decision; match.reviewed_by = request.user; match.reviewed_at = timezone.now()
        match.save(update_fields=["human_decision", "reviewed_by", "reviewed_at"])
        return Response({"id": match.id, "human_decision": match.human_decision, "reviewed_at": match.reviewed_at})

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
        queue_email(recipient=application.candidate,event="application.submitted",event_key=f"application:{application.pk}:submitted",subject="Candidature reçue",context={"message":"Votre candidature a bien été enregistrée."})
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
        try:
            serializer.is_valid(raise_exception=True)
            application = serializer.save()
            queue_email(recipient=application.candidate,event="application.submitted",event_key=f"application:{application.pk}:submitted",subject="Candidature reçue",context={"message":"Votre candidature a bien été enregistrée."})
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - defensive guard for unexpected API failures
            logger.error("Public application submission failed error_type=%s", exc.__class__.__name__)
            return Response(
                {"detail": "Impossible de traiter votre candidature. Veuillez réessayer plus tard."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        
        if is_recruitment_manager(user):
            return queryset
            
        if is_bu_manager(user):
            return queryset.filter(business_unit__manager_id=user.id)
            
        if is_intern(user):
            return queryset.filter(user_id=user.id)
            
        return queryset.filter(supervisor_id=user.id)

    def perform_update(self, serializer):
        user = self.request.user
        if is_employee(user) and not is_recruitment_manager(user):
            forbidden = set(serializer.validated_data) - {"progress", "current_status", "final_decision"}
            if forbidden:
                raise PermissionDenied("Le superviseur peut uniquement mettre à jour la progression et le statut.")
        serializer.save()

    @action(detail=True, methods=["get"], url_path="specification")
    def specification(self, request, pk=None):
        intern = self.get_object()
        if not intern.specification_pdf:
            raise Http404
        return FileResponse(
            intern.specification_pdf.open("rb"),
            as_attachment=True,
            filename=intern.specification_pdf.name.rsplit("/", 1)[-1],
            content_type="application/pdf",
        )


class InternDocumentViewSet(viewsets.ModelViewSet):
    queryset = InternDocument.objects.none()
    serializer_class = InternDocumentSerializer
    permission_classes = [IsInternshipParticipant]
    
    def get_queryset(self):
        queryset = InternDocument.objects.select_related("intern__user", "validator")
        user = self.request.user
        
        if is_recruitment_manager(user):
            return queryset
        if user.role == UserRole.HR:
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
        if is_employee(user) and not is_recruitment_manager(user) and intern.supervisor_id != user.id:
            raise PermissionDenied("Ce stagiaire ne vous est pas affecté.")
        requirement = serializer.validated_data["requirement"]
        uploaded_file = serializer.validated_data["file"]
        serializer.save(
            document_type=requirement.document_type,
            submission_method=InternDocument.SubmissionMethod.ONLINE,
            original_name=uploaded_file.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
            content_type=getattr(uploaded_file, "content_type", ""),
            size=uploaded_file.size,
            status="PENDING",
            is_validated=False,
            validator=None,
            validated_at=None,
        )

    @action(detail=False, methods=["post"], url_path="declare-physical")
    def declare_physical(self, request):
        intern_id = request.data.get("intern")
        requirement_id = request.data.get("requirement")
        try:
            intern = InternProfile.objects.get(pk=intern_id)
            requirement = InternDocumentRequirement.objects.get(pk=requirement_id, is_active=True)
        except (InternProfile.DoesNotExist, InternDocumentRequirement.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Stagiaire ou document demandé invalide."}, status=status.HTTP_400_BAD_REQUEST)
        if is_intern(request.user) and intern.user_id != request.user.id:
            raise PermissionDenied("Vous pouvez uniquement déclarer vos propres documents.")
        if not is_intern(request.user) and not is_recruitment_manager(request.user):
            raise PermissionDenied("Cette déclaration est réservée au stagiaire ou au Super Admin.")
        document = InternDocument.objects.create(
            intern=intern,
            requirement=requirement,
            document_type=requirement.document_type,
            submission_method=InternDocument.SubmissionMethod.PHYSICAL,
            file=None,
            original_name="",
            content_type="",
            size=0,
            status="PENDING",
            is_validated=False,
        )
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.file:
            raise Http404
        return FileResponse(document.file.open("rb"), as_attachment=True, filename=document.file.name.rsplit("/", 1)[-1])

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_document(self, request, pk=None):
        if not is_recruitment_manager(request.user):
            raise PermissionDenied("Seul le Super Admin peut valider un document.")
        document = self.get_object()
        from django.utils import timezone
        document.is_validated = True
        document.status = "VALIDATED"
        document.validated_at = timezone.now()
        document.validator = request.user
        document.comment = request.data.get("comment", document.comment)
        document.save(update_fields=["is_validated", "status", "validated_at", "validator", "comment"])
        return Response(self.get_serializer(document).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_document(self, request, pk=None):
        if not is_recruitment_manager(request.user):
            raise PermissionDenied("Seul le Super Admin peut refuser un document.")
        document = self.get_object()
        document.is_validated = False
        document.status = "REJECTED"
        document.validated_at = timezone.now()
        document.validator = request.user
        document.comment = request.data.get("comment", "")
        if not document.comment:
            raise DRFValidationError({"comment": "Le motif du refus est obligatoire."})
        document.save(update_fields=["is_validated", "status", "validated_at", "validator", "comment"])
        return Response(self.get_serializer(document).data)


class InternDocumentRequirementViewSet(viewsets.ModelViewSet):
    serializer_class = InternDocumentRequirementSerializer
    permission_classes = [IsInternDocumentRequirementUser]
    queryset = InternDocumentRequirement.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InternEvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = InternEvaluationSerializer
    permission_classes = [IsInternshipParticipant]
    
    def get_queryset(self):
        queryset = InternEvaluation.objects.select_related("intern__user", "evaluator")
        user = self.request.user
        
        if is_recruitment_manager(user):
            return queryset
            
        if is_bu_manager(user):
            return queryset.filter(intern__business_unit__manager_id=user.id)
            
        if is_intern(user):
            return queryset.filter(intern__user_id=user.id)
            
        return queryset.filter(intern__supervisor_id=user.id)

    def perform_create(self, serializer):
        intern = serializer.validated_data["intern"]
        user = self.request.user
        if is_employee(user) and not is_recruitment_manager(user) and intern.supervisor_id != user.id:
            raise PermissionDenied("Ce stagiaire ne vous est pas affecté.")
        serializer.save(evaluator=user)

    def perform_update(self, serializer):
        evaluation = self.get_object()
        user = self.request.user
        if is_employee(user) and not is_recruitment_manager(user) and evaluation.evaluator_id != user.id:
            raise PermissionDenied("Vous pouvez uniquement modifier vos propres évaluations.")
        if "intern" in serializer.validated_data and serializer.validated_data["intern"].id != evaluation.intern_id:
            raise PermissionDenied("Une évaluation ne peut pas être réaffectée à un autre stagiaire.")
        serializer.save()
