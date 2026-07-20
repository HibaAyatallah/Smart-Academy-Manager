from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .choices import NeedStatus
from .models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed, BusinessUnitNeedHistory
from .serializers import (
    BusinessUnitSerializer,
    BusinessUnitMembershipSerializer,
    BusinessUnitNeedWorkflowSerializer,
    NeedDecisionSerializer,
)
from .permissions import (
    CanViewBUData,
    IsHROrSuperAdmin,
    IsHRSuperAdminOrManager,
    IsSuperAdminOnly,
    is_bu_manager,
    is_collaborator,
    is_hr_or_superadmin,
)
from apps.accounts.roles import is_super_admin


class BusinessUnitViewSet(viewsets.ModelViewSet):
    """
    Business Unit management.

    - Super Admin: full CRUD.
    - BU Manager: read-only list/detail for own BU; limited update (no manager/code/is_active).
    - Collaborator (EMPLOYEE): read-only for BU they belong to.
    - HR: no access — HR uses /api/hr/collaborators/ to view collaborators grouped by BU.
    """
    serializer_class = BusinessUnitSerializer
    permission_classes = [CanViewBUData]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "manager"]
    search_fields = ["name", "code", "manager__email", "manager__first_name", "manager__last_name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in {"create", "destroy"}:
            return [IsSuperAdminOnly()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = BusinessUnit.objects.select_related("manager").all()

        if is_super_admin(user):
            return queryset
        if is_bu_manager(user):
            return queryset.filter(manager=user)
        if is_collaborator(user):
            return queryset.filter(memberships__user=user, memberships__is_active=True).distinct()

        # HR and all other roles: no access via this viewset
        return queryset.none()

    def perform_update(self, serializer):
        user = self.request.user
        if is_bu_manager(user):
            # BU Managers may only update non-sensitive fields on their own BU.
            # The manager field is already blocked by the serializer validator.
            # Explicitly prevent changing sensitive fields at the view level.
            forbidden = {"manager", "code", "is_active"}
            attempted = set(serializer.validated_data.keys()) & forbidden
            if attempted:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    "Vous n'êtes pas autorisé à modifier les champs sensibles."
                )
        serializer.save()


class BusinessUnitMembershipViewSet(viewsets.ModelViewSet):
    """
    Membership management.

    - Super Admin: full CRUD.
    - BU Manager: CRUD for own BU's memberships (soft delete only).
    - HR: no access — HR uses /api/hr/collaborators/ instead.
    """
    serializer_class = BusinessUnitMembershipSerializer
    permission_classes = [IsHRSuperAdminOrManager]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["business_unit", "is_active", "position"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "position"]
    ordering_fields = ["joined_at"]
    ordering = ["-joined_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = BusinessUnitMembership.objects.select_related("user", "business_unit").all()

        if is_super_admin(user):
            return queryset
        if is_bu_manager(user):
            return queryset.filter(business_unit__manager=user)

        return queryset.none()

    def perform_destroy(self, instance):
        if is_bu_manager(self.request.user):
            instance.is_active = False
            instance.save(update_fields=["is_active"])
            return
        instance.delete()


class BusinessUnitNeedViewSet(viewsets.ModelViewSet):
    """
    BU Need management.

    - Super Admin: full CRUD + status transitions.
    - BU Manager: CRUD for own BU needs; submit/draft transitions.
    - Collaborator (EMPLOYEE): read-only for CONFIRMED TRAINING needs targeted to them.
    - HR: no access via this viewset.
    """
    serializer_class = BusinessUnitNeedWorkflowSerializer
    permission_classes = [CanViewBUData]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["business_unit", "status", "priority", "need_type", "required_level"]
    search_fields = ["title", "description", "required_skills"]
    ordering_fields = ["created_at", "expected_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = BusinessUnitNeed.objects.select_related(
            "business_unit", "created_by", "requester", "trainer"
        ).prefetch_related("training_recipients").all()

        if is_super_admin(user):
            return queryset
        if is_bu_manager(user):
            return queryset.filter(business_unit__manager=user)
        if is_collaborator(user):
            return queryset.filter(
                business_unit__memberships__user=user,
                business_unit__memberships__is_active=True,
                need_type="TRAINING",
                status=NeedStatus.ACCEPTED,
            ).filter(
                Q(training_audience="ALL") | Q(training_recipients=user)
            ).distinct()

        return queryset.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _transition_status(self, need, new_status, comment=""):
        old_status = need.status
        if old_status == new_status:
            return Response({"detail": "Le besoin est déjà dans ce statut."}, status=status.HTTP_400_BAD_REQUEST)
        
        need.status = new_status
        if comment:
            need.decision_comment = comment
        need.save(update_fields=["status", "decision_comment", "updated_at"])

        BusinessUnitNeedHistory.objects.create(
            need=need,
            from_status=old_status,
            to_status=new_status,
            changed_by=self.request.user,
            comment=comment
        )
        serializer = BusinessUnitNeedWorkflowSerializer(need, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        need = self.get_object()
        if need.status != NeedStatus.DRAFT:
            return Response({"detail": "Transition invalide."}, status=status.HTTP_400_BAD_REQUEST)
        return self._transition_status(need, NeedStatus.SUBMITTED)

    @action(detail=True, methods=["post"])
    def mark_under_review(self, request, pk=None):
        if not is_super_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        need = self.get_object()
        if need.status != NeedStatus.SUBMITTED:
            return Response({"detail": "Transition invalide."}, status=status.HTTP_400_BAD_REQUEST)
        return self._transition_status(need, NeedStatus.UNDER_REVIEW)

    @action(detail=True, methods=["post"], serializer_class=NeedDecisionSerializer)
    def accept(self, request, pk=None):
        if not is_super_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        need = self.get_object()
        if need.status not in {NeedStatus.SUBMITTED, NeedStatus.UNDER_REVIEW}:
            return Response({"detail": "Transition invalide."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._transition_status(need, NeedStatus.ACCEPTED, serializer.validated_data.get("comment", ""))

    @action(detail=True, methods=["post"], serializer_class=NeedDecisionSerializer)
    def reject(self, request, pk=None):
        if not is_super_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        need = self.get_object()
        if need.status not in {NeedStatus.SUBMITTED, NeedStatus.UNDER_REVIEW}:
            return Response({"detail": "Transition invalide."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._transition_status(need, NeedStatus.REJECTED, serializer.validated_data.get("comment", ""))

    @action(detail=True, methods=["post"])
    def satisfy(self, request, pk=None):
        if not is_super_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        need = self.get_object()
        if need.status != NeedStatus.ACCEPTED:
            return Response({"detail": "Transition invalide."}, status=status.HTTP_400_BAD_REQUEST)
        return self._transition_status(need, NeedStatus.SATISFIED)

    @action(detail=True, methods=["post"], serializer_class=NeedDecisionSerializer)
    def close(self, request, pk=None):
        need = self.get_object()
        if need.status == NeedStatus.CLOSED:
            return Response({"detail": "Transition invalide."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._transition_status(need, NeedStatus.CLOSED, serializer.validated_data.get("comment", ""))
