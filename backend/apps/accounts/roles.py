from .choices import UserRole


ADMINISTRATIVE_ROLES = frozenset({UserRole.SUPER_ADMIN, UserRole.HR})


def is_administrative_user(user) -> bool:
    """Return whether a user has the shared HR/Super Admin capability set."""
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.role in ADMINISTRATIVE_ROLES)
    )
