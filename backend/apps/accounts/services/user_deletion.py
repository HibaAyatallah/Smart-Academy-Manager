from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.notifications.models import AuditLog

User = get_user_model()


def _revoke_authentication(locked_user) -> None:
    """Revoke server-side authentication state for a deleted/retired account."""
    # Outstanding JWTs are blacklisted when the blacklist application is enabled.
    try:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
        for token in OutstandingToken.objects.filter(user=locked_user):
            BlacklistedToken.objects.get_or_create(token=token)
    except (ImportError, RuntimeError):
        pass
    for session in Session.objects.all():
        try:
            if str(session.get_decoded().get("_auth_user_id")) == str(locked_user.pk):
                session.delete()
        except Exception:
            continue


def _write_deletion_audit(*, locked_user, actor, identity, action: str) -> None:
    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        actor_email=getattr(actor, "email", ""),
        method="DELETE",
        path=f"/api/users/{locked_user.pk}/",
        action=action,
        target_type="users",
        target_id=str(locked_user.pk),
        status_code=204,
        metadata=identity,
    )


@transaction.atomic
def delete_user_account(*, user, actor=None, reason: str) -> dict:
    """Apply the role-aware account deletion policy.

    Candidate accounts are detached and hard-deleted so application history is
    retained without a login. Internal accounts are retired instead: the User
    and historical foreign keys remain, but all operational access is removed.
    """
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if actor and actor.pk == locked_user.pk:
        raise ValidationError({"detail": "Vous ne pouvez pas supprimer votre propre compte."})

    identity = {
        "user_id": locked_user.pk,
        "user_email": locked_user.email,
        "user_role": locked_user.role,
        "reason": reason,
    }

    is_candidate_account = locked_user.role == "CANDIDATE"
    candidate_profile = getattr(locked_user, "candidate_profile", None)
    if is_candidate_account and candidate_profile:
        candidate_profile.account_email = locked_user.email
        candidate_profile.account_first_name = locked_user.first_name
        candidate_profile.account_last_name = locked_user.last_name
        candidate_profile.save(update_fields=[
            "account_email", "account_first_name", "account_last_name", "updated_at"
        ])

    _revoke_authentication(locked_user)
    if is_candidate_account:
        identity["deletion_mode"] = "HARD_DELETE"
        _write_deletion_audit(
            locked_user=locked_user, actor=actor, identity=identity,
            action="USER_HARD_DELETED",
        )
        locked_user.delete()
        return identity

    # Preserve internal profiles, enrollments and project history. Only current
    # operational assignments are detached/deactivated.
    from apps.business_units.models import BusinessUnit, BusinessUnitMembership
    BusinessUnit.objects.filter(manager=locked_user).update(manager=None)
    BusinessUnitMembership.objects.filter(user=locked_user, is_active=True).update(is_active=False)
    locked_user.is_active = False
    locked_user.save(update_fields=["is_active", "updated_at"])
    identity["deletion_mode"] = "DEACTIVATED"
    _write_deletion_audit(
        locked_user=locked_user, actor=actor, identity=identity,
        action="USER_DEACTIVATED",
    )
    return identity


@transaction.atomic
def hard_delete_user(*, user, actor=None, reason: str) -> dict:
    """Hard-delete a candidate account after its business identity is detached."""
    if user.role != "CANDIDATE":
        raise ValidationError({"detail": "La suppression définitive est réservée aux comptes candidats."})
    return delete_user_account(user=user, actor=actor, reason=reason)
