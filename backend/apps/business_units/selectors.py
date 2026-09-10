from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.accounts.choices import UserRole

User = get_user_model()

ELIGIBLE_SUPERVISOR_ROLES = (
    UserRole.EMPLOYEE,
    UserRole.TRAINER_TUTOR,
    UserRole.BU_MANAGER,
)


def eligible_supervisors_for_business_unit(business_unit) -> QuerySet:
    """Return active supervisors belonging to exactly one requested BU."""
    return User.objects.filter(is_active=True).filter(
        Q(
            role__in=(UserRole.EMPLOYEE, UserRole.TRAINER_TUTOR),
            bu_memberships__business_unit=business_unit,
            bu_memberships__is_active=True,
        )
        | Q(role=UserRole.BU_MANAGER, managed_business_units=business_unit)
    ).distinct().order_by("last_name", "first_name", "email")
