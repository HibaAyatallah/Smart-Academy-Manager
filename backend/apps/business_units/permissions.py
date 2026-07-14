from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.choices import UserRole
from apps.accounts.roles import is_administrative_user
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed


def is_hr_or_superadmin(user) -> bool:
    return is_administrative_user(user)


class IsHROrSuperAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_administrative_user(request.user)


def is_bu_manager(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.BU_MANAGER)


def is_collaborator(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.EMPLOYEE)


class IsHRSuperAdminOrManager(BasePermission):
    """
    HR/SuperAdmin: All access.
    Manager: Read/Write only to their assigned BU objects.
    Others: No access.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if is_hr_or_superadmin(user) or is_bu_manager(user):
            return True
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if is_hr_or_superadmin(user):
            return True

        if is_bu_manager(user):
            # For BusinessUnit
            if isinstance(obj, BusinessUnit):
                return obj.manager_id == user.id
            # For BusinessUnitMembership and BusinessUnitNeed
            business_unit = getattr(obj, "business_unit", None)
            if business_unit:
                return business_unit.manager_id == user.id

        return False


class CanViewBUData(BasePermission):
    """
    HR/SuperAdmin: Read all.
    Manager: Read own.
    Collaborator: Read BU they are members of.
    Candidate/Client: No access.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if is_hr_or_superadmin(user) or is_bu_manager(user) or is_collaborator(user):
            # Write operations only for HR/Manager (handled in views or viewsets)
            # This permission might just allow GET for collaborators
            if is_collaborator(user):
                return request.method in SAFE_METHODS
            return True
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if is_hr_or_superadmin(user):
            return True

        # Extract BU from object
        bu = obj if isinstance(obj, BusinessUnit) else getattr(obj, "business_unit", None)

        if is_bu_manager(user):
            return bu and bu.manager_id == user.id

        if is_collaborator(user) and request.method in SAFE_METHODS:
            # Check if user is an active member of this BU
            if not bu:
                return False
            return BusinessUnitMembership.objects.filter(
                business_unit=bu, user=user, is_active=True
            ).exists()

        return False
