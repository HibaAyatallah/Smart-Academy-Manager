from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.choices import UserRole
from apps.accounts.roles import is_administrative_user


def is_recruitment_manager(user) -> bool:
    return is_administrative_user(user)


def is_candidate(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.CANDIDATE)


def can_access_application_document(user, document) -> bool:
    if is_recruitment_manager(user):
        return True
    return bool(
        is_candidate(user)
        and document.application.candidate_profile.user_id == user.id
    )


class IsApplicationParticipant(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if is_recruitment_manager(user):
            return True
        if is_candidate(user):
            return request.method in SAFE_METHODS or view.action in {"cancel", "add_document"}
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        if is_recruitment_manager(request.user):
            return True
        application = getattr(obj, "application", obj)
        return bool(
            is_candidate(request.user)
            and application.candidate_profile.user_id == request.user.id
            and (request.method in SAFE_METHODS or view.action in {"cancel", "add_document"})
        )


class IsRecruitmentManager(BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_recruitment_manager(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return is_recruitment_manager(request.user)
