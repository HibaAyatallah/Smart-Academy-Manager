from rest_framework.permissions import BasePermission

from .choices import UserRole
from .roles import ADMINISTRATIVE_ROLES, is_administrative_user


class HasRole(BasePermission):
    allowed_roles: set[str] = set()

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in self.allowed_roles)
        )


class IsSuperAdmin(HasRole):
    allowed_roles = ADMINISTRATIVE_ROLES


class CanManageUsers(BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_administrative_user(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return is_administrative_user(request.user)
