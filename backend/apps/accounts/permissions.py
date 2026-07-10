from rest_framework.permissions import BasePermission

from .choices import UserRole


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
    allowed_roles = {UserRole.SUPER_ADMIN}


class CanManageUsers(BasePermission):
    manager_roles = {UserRole.SUPER_ADMIN, UserRole.HR}

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in self.manager_roles)
        )

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_superuser or user.role == UserRole.SUPER_ADMIN:
            return True
        if user.role == UserRole.HR:
            return obj.role != UserRole.SUPER_ADMIN and not obj.is_superuser
        return False

