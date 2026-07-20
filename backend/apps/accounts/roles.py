from .choices import UserRole


def is_super_admin(user) -> bool:
    """Return True only for Super Administrators.

    Super Admins have full platform management and decision permissions.
    They are the only role that can perform write operations on users,
    Business Units, recruitment transitions, conversions, and audit logs.
    """
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.role == UserRole.SUPER_ADMIN)
    )


def is_hr(user) -> bool:
    """Return True for HR users.

    HR has global read-only access to a restricted set of data:
    - Accepted interns (personal and administrative information)
    - Collaborators grouped by Business Unit
    - Training courses and sessions (read-only)
    - Own personal profile and password change

    HR must NOT perform any write operations.
    """
    return bool(user and user.is_authenticated and user.role == UserRole.HR)


def is_super_admin_or_hr_readonly(user, *, request=None) -> bool:
    """Return True for Super Admin (all methods) or HR (safe methods only).

    Use this ONLY where HR genuinely needs the same read access as Super Admin.
    For write operations, always use is_super_admin() instead.
    """
    if is_super_admin(user):
        return True
    if is_hr(user):
        if request is not None:
            from rest_framework.permissions import SAFE_METHODS
            return request.method in SAFE_METHODS
        return True
    return False


# ---------------------------------------------------------------------------
# Deprecated — kept for backwards compatibility during transition.
# Do NOT use in new code. Replace all usages with is_super_admin().
# ---------------------------------------------------------------------------
ADMINISTRATIVE_ROLES = frozenset({UserRole.SUPER_ADMIN})


def is_administrative_user(user) -> bool:
    """Deprecated: use is_super_admin() instead.

    Previously grouped HR and Super Admin together. Now correctly maps
    to Super Admin only to enforce the role separation requirement.
    """
    return is_super_admin(user)
