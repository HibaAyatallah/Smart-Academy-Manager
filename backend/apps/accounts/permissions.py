from rest_framework.permissions import BasePermission, SAFE_METHODS

from .roles import is_super_admin, is_hr


# ---------------------------------------------------------------------------
# Generic role-based base class
# ---------------------------------------------------------------------------

class HasRole(BasePermission):
    """Allow access only to users with specific roles."""
    allowed_roles: set[str] = set()

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in self.allowed_roles)
        )


# ---------------------------------------------------------------------------
# Super Admin — full management permissions
# ---------------------------------------------------------------------------

class IsSuperAdminOnly(BasePermission):
    """Allow access only to Super Administrators.

    Use for any endpoint that involves mutations to users, roles,
    Business Units, recruitment, conversions, certificates, or audit logs.
    """

    def has_permission(self, request, view) -> bool:
        return is_super_admin(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return is_super_admin(request.user)


# Alias for backwards compatibility with existing views that import IsSuperAdmin
IsSuperAdmin = IsSuperAdminOnly


# ---------------------------------------------------------------------------
# HR — read-only, restricted scope
# ---------------------------------------------------------------------------

class IsHROnly(BasePermission):
    """Allow access only to HR users.

    HR has restricted read-only access (safe methods only).
    """

    def has_permission(self, request, view) -> bool:
        return is_hr(request.user) and request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj) -> bool:
        return is_hr(request.user) and request.method in SAFE_METHODS


# ---------------------------------------------------------------------------
# Super Admin full access OR HR read-only
# ---------------------------------------------------------------------------

class IsSuperAdminOrHRReadOnly(BasePermission):
    """Super Admin: all methods. HR: GET/HEAD/OPTIONS only.

    Use where HR genuinely needs global read access alongside Super Admin
    full access (e.g., certain list views that HR is allowed to see).
    """

    def has_permission(self, request, view) -> bool:
        if is_super_admin(request.user):
            return True
        if is_hr(request.user):
            return request.method in SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        if is_super_admin(request.user):
            return True
        if is_hr(request.user):
            return request.method in SAFE_METHODS
        return False


# ---------------------------------------------------------------------------
# User management — Super Admin only
# ---------------------------------------------------------------------------

class CanManageUsers(BasePermission):
    """Allow user management only to Super Administrators.

    HR must NOT access user management endpoints.
    """

    def has_permission(self, request, view) -> bool:
        return is_super_admin(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return is_super_admin(request.user)
