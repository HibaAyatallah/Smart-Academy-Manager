from rest_framework.permissions import SAFE_METHODS, BasePermission
from apps.accounts.choices import UserRole
from apps.accounts.roles import is_hr, is_super_admin


class IsProjectParticipant(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_super_admin(user):
            return True
        if is_hr(user):
            return False
        if user.role == UserRole.EMPLOYEE:
            if view.basename == "project":
                return request.method in SAFE_METHODS or request.method in {"POST", "PATCH"}
            if view.basename == "project-deliverable":
                return request.method in SAFE_METHODS or request.method in {"POST", "PATCH", "DELETE"}
            return request.method in SAFE_METHODS or request.method == "POST"
        if user.role == UserRole.INTERN:
            if view.basename == "project-deliverable":
                return request.method in SAFE_METHODS or request.method == "PATCH"
            if view.basename in {"project-comment", "project-document"}:
                return request.method in SAFE_METHODS or request.method == "POST"
            return request.method in SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_super_admin(user):
            return True
        project = getattr(obj, "project", obj)
        if user.role == UserRole.EMPLOYEE and project.supervisor_id == user.id:
            return True
        if request.method in SAFE_METHODS or view.basename in {"project-comment", "project-document", "project-deliverable"}:
            return project.assignees.filter(id=user.id).exists()
        return False
