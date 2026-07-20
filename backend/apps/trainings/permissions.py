from rest_framework import permissions
from apps.accounts.choices import UserRole

class IsSuperAdminOrReadOnly(permissions.BasePermission):
    """
    Allow full access to Super Admin.
    Allow read-only access to authenticated users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in [UserRole.SUPER_ADMIN, UserRole.HR]


class IsClientProfile(permissions.BasePermission):
    """
    Allow access only to External Clients.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == UserRole.CLIENT


class IsNotClientProfile(permissions.BasePermission):
    """
    Deny access to External Clients for internal endpoints.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role != UserRole.CLIENT

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == UserRole.SUPER_ADMIN
