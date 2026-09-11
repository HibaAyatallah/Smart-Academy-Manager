"""Read scopes shared by session endpoints, nested responses and assistant context."""

from apps.accounts.choices import UserRole
from apps.accounts.roles import is_super_admin
from .choices import SessionStatus, TrainingStatus


def visible_sessions(queryset, user):
    if not user or not user.is_authenticated:
        return queryset.none()
    if is_super_admin(user):
        return queryset
    if user.role == UserRole.CLIENT:
        # Check both owners, including historical inconsistent records.
        return queryset.filter(external_client__user=user, training__external_client__user=user)
    if user.role == UserRole.TRAINER_TUTOR:
        return queryset.filter(trainer=user)
    internal = queryset.filter(external_client__isnull=True, training__external_client__isnull=True)
    if user.role == UserRole.HR:
        return internal.filter(
            training__status=TrainingStatus.PUBLISHED,
            status__in=[SessionStatus.OPEN, SessionStatus.PLANNED, SessionStatus.FULL],
        )
    if user.role == UserRole.BU_MANAGER:
        return internal.filter(training__business_unit__manager=user)
    return queryset.none()
