from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.choices import UserRole
from apps.accounts.roles import is_super_admin
from apps.business_units.models import BusinessUnit, BusinessUnitMembership


# ---------------------------------------------------------------------------
# Role helper predicates
# ---------------------------------------------------------------------------

def is_bu_manager(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.BU_MANAGER)


def is_collaborator(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.EMPLOYEE)


# ---------------------------------------------------------------------------
# Permission classes
# ---------------------------------------------------------------------------


class IsHRSuperAdminOrManager(BasePermission):
    """
    Super Admin: All access.
    BU Manager: Read/Write only to their assigned BU objects.
    HR: Read-only access globally.
    Others: No access.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_super_admin(user) or is_bu_manager(user):
            return True
        if user.role == UserRole.HR:
            return request.method in SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if is_super_admin(user):
            return True
        if user.role == UserRole.HR:
            return request.method in SAFE_METHODS

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
    Super Admin: Full access (read + write).
    BU Manager: Read + write for own BU only.
    Collaborator (EMPLOYEE): Read-only for BU they are members of.
    HR: Read-only access globally.
    Candidate / Client / Others: No access.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_super_admin(user) or is_bu_manager(user):
            return True
        if user.role == UserRole.HR or is_collaborator(user):
            return request.method in SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if is_super_admin(user):
            return True
        if user.role == UserRole.HR and request.method in SAFE_METHODS:
            return True

        # Extract BU from object
        bu = obj if isinstance(obj, BusinessUnit) else getattr(obj, "business_unit", None)

        if is_bu_manager(user):
            return bu and bu.manager_id == user.id

        if is_collaborator(user) and request.method in SAFE_METHODS:
            if not bu:
                return False
            return BusinessUnitMembership.objects.filter(
                business_unit=bu, user=user, is_active=True
            ).exists()

        return False
