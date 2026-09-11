"""Transactional operational BU assignments; historical rows are retained."""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.choices import UserRole
from .models import BusinessUnit, BusinessUnitMembership
from .selectors import eligible_supervisors_for_business_unit

UNSET = object()


def current_business_unit(user):
    if user.role == UserRole.INTERN:
        from apps.recruitment.models import InternProfile
        profile = InternProfile.objects.filter(user=user).select_related("business_unit").first()
        if profile:
            return profile.business_unit
    if user.role == UserRole.BU_MANAGER:
        units = BusinessUnit.objects.filter(manager=user, is_active=True)
    else:
        units = BusinessUnit.objects.filter(memberships__user=user, memberships__is_active=True)
    units = list(units.distinct().order_by("id")[:2])
    if len(units) > 1:
        raise ValidationError({"business_unit_id": "Plusieurs BU actives existent ; indiquez explicitement la BU à conserver."})
    return units[0] if units else None


def validate_supervisor(business_unit, supervisor):
    if supervisor and (not business_unit or not business_unit.is_active or not eligible_supervisors_for_business_unit(business_unit).filter(pk=supervisor.pk).exists()):
        raise ValidationError({"supervisor": "L'encadrant doit être actif, avoir un rôle autorisé et appartenir à la BU du stage. Réaffectez ou détachez explicitement l'encadrant avant ce changement."})


def validate_supervised_interns(user):
    for profile in user.supervised_interns.filter(user__role=UserRole.INTERN, user__is_active=True).select_related("business_unit"):
        validate_supervisor(profile.business_unit, user)


def audit_business_unit_change(user, previous, current, request=None):
    if getattr(previous, "pk", None) == getattr(current, "pk", None) or request is None:
        return
    from apps.notifications.models import AuditLog
    def metadata(unit):
        return {"id": unit.pk, "code": unit.code, "name": unit.name} if unit else None
    AuditLog.objects.create(
        actor=request.user, actor_email=request.user.email, method=request.method,
        path=request.path[:500], action="USER_BUSINESS_UNIT_CHANGED",
        target_type="users", target_id=str(user.pk),
        status_code=201 if request.method == "POST" else 200,
        metadata={"user_id": user.pk, "user_email": user.email,
                  "old_business_unit": metadata(previous), "new_business_unit": metadata(current)},
    )


@transaction.atomic
def assign_business_unit(user, business_unit_id, *, request=None, supervisor=UNSET, previous=UNSET):
    # All API assignment paths serialize changes for the same person.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    if previous is UNSET:
        previous = current_business_unit(user)
    unit = None
    if business_unit_id is not None:
        unit = BusinessUnit.objects.select_for_update().filter(pk=business_unit_id, is_active=True).first()
        if not unit:
            raise ValidationError({"business_unit_id": "La Business Unit doit être active."})
    if user.role == UserRole.CLIENT and unit:
        raise ValidationError({"business_unit_id": "Un client externe ne peut pas avoir de BU interne. Fournissez explicitement null pour détacher la BU."})

    profile = None
    if user.role == UserRole.INTERN:
        from apps.recruitment.models import InternProfile
        profile = InternProfile.objects.select_for_update().filter(user=user).first()
        if not profile:
            raise ValidationError({"role": "Le dossier stagiaire doit être créé par le parcours métier (conversion ou import)."})
        supervisor = profile.supervisor if supervisor is UNSET else supervisor
        validate_supervisor(unit, supervisor)

    displaced = unit.manager if unit and user.role == UserRole.BU_MANAGER and unit.manager_id != user.pk else None
    BusinessUnit.objects.filter(manager=user).exclude(pk=business_unit_id if user.role == UserRole.BU_MANAGER else None).update(manager=None)
    memberships = BusinessUnitMembership.objects.filter(user=user, is_active=True)
    memberships.exclude(business_unit_id=business_unit_id if user.role != UserRole.BU_MANAGER else None).update(is_active=False)
    if user.role == UserRole.BU_MANAGER:
        memberships.update(is_active=False)
        if unit:
            BusinessUnit.objects.filter(pk=unit.pk).update(manager=user)
    elif unit and not memberships.filter(business_unit=unit).exists():
        # Rejoining creates a new period instead of reopening a historical row.
        BusinessUnitMembership.objects.create(user=user, business_unit=unit)
    if profile:
        profile.business_unit = unit
        profile.supervisor = supervisor
        profile.save(update_fields=["business_unit", "supervisor"])
    validate_supervised_interns(user)
    if displaced:
        validate_supervised_interns(displaced)
        audit_business_unit_change(displaced, unit, current_business_unit(displaced), request)
    audit_business_unit_change(user, previous, unit, request)


@transaction.atomic
def retire_membership(membership, request=None):
    get_user_model().objects.select_for_update().get(pk=membership.user_id)
    previous = current_business_unit(membership.user)
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    validate_supervised_interns(membership.user)
    audit_business_unit_change(membership.user, previous, current_business_unit(membership.user), request)
