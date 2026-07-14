from django.db.models import Q
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from .serializers import (
    BusinessUnitSerializer,
    BusinessUnitMembershipSerializer,
    BusinessUnitNeedSerializer,
)
from .permissions import (
    CanViewBUData,
    IsHROrSuperAdmin,
    IsHRSuperAdminOrManager,
    is_bu_manager,
    is_collaborator,
    is_hr_or_superadmin,
)


class BusinessUnitViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessUnitSerializer
    permission_classes = [CanViewBUData]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "manager"]
    search_fields = ["name", "code", "manager__email", "manager__first_name", "manager__last_name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in {"create", "destroy"}:
            return [IsHROrSuperAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = BusinessUnit.objects.select_related("manager").all()

        if is_hr_or_superadmin(user):
            return queryset
        if is_bu_manager(user):
            return queryset.filter(manager=user)
        if is_collaborator(user):
            return queryset.filter(memberships__user=user, memberships__is_active=True).distinct()
        
        return queryset.none()


class BusinessUnitMembershipViewSet(viewsets.ModelViewSet):
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

        if is_hr_or_superadmin(user):
            return queryset
        if is_bu_manager(user):
            return queryset.filter(business_unit__manager=user)
        
        return queryset.none()


class BusinessUnitNeedViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessUnitNeedSerializer
    permission_classes = [CanViewBUData]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["business_unit", "status", "priority", "need_type", "required_level"]
    search_fields = ["title", "description", "required_skills"]
    ordering_fields = ["created_at", "expected_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = BusinessUnitNeed.objects.select_related("business_unit", "created_by").all()

        if is_hr_or_superadmin(user):
            return queryset
        if is_bu_manager(user):
            return queryset.filter(business_unit__manager=user)
        if is_collaborator(user):
            return queryset.filter(business_unit__memberships__user=user, business_unit__memberships__is_active=True).distinct()

        return queryset.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
