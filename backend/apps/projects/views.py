from django.db.models import Q
from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from apps.accounts.choices import UserRole
from apps.accounts.roles import is_hr, is_super_admin
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.recruitment.models import InternProfile
from .models import Project, ProjectComment, ProjectDeliverable, ProjectDocument
from .permissions import IsProjectParticipant
from .serializers import ProjectCommentSerializer, ProjectDeliverableSerializer, ProjectDocumentSerializer, ProjectSerializer


def visible_projects(user):
    qs = Project.objects.select_related("business_unit", "supervisor", "created_by").prefetch_related("assignees", "deliverables", "comments__author", "documents__uploaded_by")
    if is_super_admin(user) or is_hr(user):
        return qs
    if user.role == UserRole.EMPLOYEE:
        return qs.filter(Q(supervisor=user) | Q(assignees=user)).distinct()
    return qs.filter(assignees=user)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsProjectParticipant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["business_unit", "supervisor", "status"]
    search_fields = ["title", "description", "assignees__email"]
    ordering_fields = ["created_at", "start_date", "end_date", "progress", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return visible_projects(self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == UserRole.EMPLOYEE and serializer.validated_data.get("supervisor") != user:
            raise PermissionDenied("Un superviseur doit créer un projet sous sa propre responsabilité.")
        serializer.save(created_by=user)

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == UserRole.EMPLOYEE and not is_super_admin(user):
            forbidden = {"business_unit", "supervisor"}.intersection(serializer.validated_data)
            if forbidden:
                raise PermissionDenied("Le superviseur ne peut pas réaffecter le projet ou sa Business Unit.")
        serializer.save()

    @action(detail=False, methods=["get"], url_path="assignment-options")
    def assignment_options(self, request):
        user = request.user
        if is_hr(user):
            raise PermissionDenied("RH dispose d'un accès lecture seule aux projets.")
        if is_super_admin(user):
            business_units = BusinessUnit.objects.filter(is_active=True)
            supervisors = User.objects.filter(role=UserRole.EMPLOYEE, is_active=True)
        else:
            bu_ids = BusinessUnitMembership.objects.filter(user=user, is_active=True).values_list("business_unit_id", flat=True)
            business_units = BusinessUnit.objects.filter(id__in=bu_ids, is_active=True)
            supervisors = User.objects.filter(id=user.id)
        bu_ids = list(business_units.values_list("id", flat=True))
        employee_ids = BusinessUnitMembership.objects.filter(business_unit_id__in=bu_ids, is_active=True, user__role=UserRole.EMPLOYEE).values_list("user_id", flat=True)
        intern_ids = InternProfile.objects.filter(business_unit_id__in=bu_ids).values_list("user_id", flat=True)
        assignees = User.objects.filter(Q(id__in=employee_ids) | Q(id__in=intern_ids), is_active=True).distinct()
        return Response({
            "business_units": [{"id": bu.id, "name": bu.name, "code": bu.code} for bu in business_units],
            "supervisors": [{"id": item.id, "full_name": item.full_name, "email": item.email} for item in supervisors],
            "assignees": [{"id": item.id, "full_name": item.full_name, "email": item.email, "role": item.role} for item in assignees],
        })


class ProjectDeliverableViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectDeliverableSerializer
    permission_classes = [IsProjectParticipant]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["project", "status"]
    def get_queryset(self): return ProjectDeliverable.objects.filter(project__in=visible_projects(self.request.user)).select_related("project", "created_by", "updated_by")
    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if project.supervisor_id != self.request.user.id and not is_super_admin(self.request.user): raise PermissionDenied("Seul le superviseur peut créer un livrable.")
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    def perform_update(self, serializer):
        deliverable = self.get_object(); user = self.request.user
        if project := serializer.validated_data.get("project"):
            if project.id != deliverable.project_id: raise PermissionDenied("Un livrable ne peut pas changer de projet.")
        if deliverable.project.supervisor_id != user.id and not is_super_admin(user):
            forbidden = set(serializer.validated_data) - {"status"}
            if forbidden: raise PermissionDenied("Un participant peut uniquement modifier le statut.")
        serializer.save(updated_by=user)


class ProjectCommentViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectCommentSerializer; permission_classes = [IsProjectParticipant]; http_method_names = ["get", "post", "head", "options"]
    def get_queryset(self): return ProjectComment.objects.filter(project__in=visible_projects(self.request.user)).select_related("project", "author")
    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if not visible_projects(self.request.user).filter(id=project.id).exists(): raise PermissionDenied("Projet inaccessible.")
        serializer.save(author=self.request.user)


class ProjectDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectDocumentSerializer; permission_classes = [IsProjectParticipant]; parser_classes = [MultiPartParser, FormParser, JSONParser]; http_method_names = ["get", "post", "head", "options"]
    def get_queryset(self): return ProjectDocument.objects.filter(project__in=visible_projects(self.request.user)).select_related("project", "uploaded_by")
    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if not visible_projects(self.request.user).filter(id=project.id).exists(): raise PermissionDenied("Projet inaccessible.")
        uploaded = serializer.validated_data["file"]
        serializer.save(uploaded_by=self.request.user, original_name=uploaded.name)
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.file: raise Http404
        return FileResponse(document.file.open("rb"), as_attachment=True, filename=document.original_name)
