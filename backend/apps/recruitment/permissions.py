from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.choices import UserRole
from apps.accounts.roles import is_super_admin, is_hr


def is_recruitment_manager(user) -> bool:
    """Return True only for Super Administrators.

    Only Super Admins can manage recruitment: review applications, perform
    status transitions (accept, reject, preselect), schedule interviews, etc.

    HR must NOT perform any recruitment management action.
    """
    return is_super_admin(user)


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
    """
    Super Admin: full access to all applications and all methods.
    Candidate: safe methods + cancel + add_document (own applications only).
    HR and all others: no access.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if is_recruitment_manager(user):
            return True
        if is_candidate(user):
            return request.method in SAFE_METHODS or view.action in {"create", "cancel", "add_document"}
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
    """Allow access only to Super Administrators for recruitment management."""

    def has_permission(self, request, view) -> bool:
        return is_recruitment_manager(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return is_recruitment_manager(request.user)


def is_intern(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.INTERN)


def is_bu_manager(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.BU_MANAGER)


def is_employee(user) -> bool:
    return bool(user and user.is_authenticated and user.role == UserRole.EMPLOYEE)


class IsInternshipParticipant(BasePermission):
    """
    Super Admin: Full CRUD.
    HR: Read-only access to all interns.
    BU Manager: Read-only access to interns assigned to their BU.
    Supervisor: Read-only access to interns they supervise.
    Intern: Read-only access to their own profile.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_recruitment_manager(user):
            return True
        return request.method in SAFE_METHODS and (
            is_hr(user) or is_bu_manager(user) or is_intern(user) or is_employee(user)
        )

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if is_recruitment_manager(user):
            return True
        if request.method not in SAFE_METHODS:
            return False

        if is_hr(user):
            return True

        if hasattr(obj, "intern"):
            intern_profile = obj.intern
        else:
            intern_profile = obj

        if is_intern(user):
            return intern_profile.user_id == user.id

        if is_bu_manager(user):
            return bool(
                intern_profile.business_unit
                and intern_profile.business_unit.manager_id == user.id
            )

        return intern_profile.supervisor_id == user.id


class CanManageOffersOrReadPublished(BasePermission):
    """
    Super Admin and HR: full access.
    Public/Candidate/BU Manager: Read-only (list/retrieve) depending on queryset scoping.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        if is_super_admin(user) or is_hr(user):
            return True
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if is_super_admin(user) or is_hr(user):
            return True
        return request.method in SAFE_METHODS
