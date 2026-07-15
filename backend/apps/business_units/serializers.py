from rest_framework import serializers

from apps.accounts.choices import UserRole
from apps.business_units.permissions import is_bu_manager
from .models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed


class BusinessUnitSerializer(serializers.ModelSerializer):
    manager_email = serializers.EmailField(source="manager.email", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)

    class Meta:
        model = BusinessUnit
        fields = [
            "id",
            "name",
            "code",
            "description",
            "manager",
            "manager_email",
            "manager_name",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate_manager(self, value):
        if value.role != UserRole.BU_MANAGER:
            raise serializers.ValidationError("Le manager doit avoir le role BU_MANAGER.")
        request = self.context.get("request")
        if request and is_bu_manager(request.user):
            if self.instance is None or value.pk != self.instance.manager_id:
                raise serializers.ValidationError("Vous ne pouvez pas reassigner la Business Unit.")
        return value


class BusinessUnitMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    business_unit_name = serializers.CharField(source="business_unit.name", read_only=True)

    class Meta:
        model = BusinessUnitMembership
        fields = [
            "id",
            "business_unit",
            "business_unit_name",
            "user",
            "user_email",
            "user_name",
            "position",
            "joined_at",
            "is_active",
        ]

    def validate_business_unit(self, value):
        request = self.context.get("request")
        if request and is_bu_manager(request.user):
            if value.manager != request.user:
                raise serializers.ValidationError("Vous ne pouvez gérer que votre propre Business Unit.")
        return value


class BusinessUnitNeedSerializer(serializers.ModelSerializer):
    business_unit_name = serializers.CharField(source="business_unit.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    need_type_label = serializers.CharField(source="get_need_type_display", read_only=True)
    required_level_label = serializers.CharField(source="get_required_level_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    requester_name = serializers.CharField(
        source="requester.full_name", read_only=True
    )
    trainer_name = serializers.CharField(source="trainer.full_name", read_only=True)

    class Meta:
        model = BusinessUnitNeed
        fields = [
            "id",
            "business_unit",
            "business_unit_name",
            "title",
            "description",
            "need_type",
            "need_type_label",
            "requester",
            "requester_name",
            "required_skills",
            "required_level",
            "required_level_label",
            "number_of_profiles",
            "priority",
            "priority_label",
            "expected_date",
            "training_start_date",
            "training_end_date",
            "training_link",
            "trainer",
            "trainer_name",
            "status",
            "status_label",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]

    def validate_business_unit(self, value):
        request = self.context.get("request")
        if request and is_bu_manager(request.user):
            if value.manager != request.user:
                raise serializers.ValidationError("Vous ne pouvez créer des besoins que pour votre propre Business Unit.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        business_unit = attrs.get("business_unit") or getattr(self.instance, "business_unit", None)
        collaborator = attrs.get(
            "requester",
            getattr(self.instance, "requester", None),
        )

        if collaborator and business_unit:
            is_member = BusinessUnitMembership.objects.filter(
                business_unit=business_unit,
                user=collaborator,
                is_active=True,
            ).exists()
            if not is_member:
                raise serializers.ValidationError({
                    "requester": "Ce demandeur n'appartient pas à cette Business Unit."
                })

        if request and is_bu_manager(request.user):
            protected_fields = {
                "training_start_date",
                "training_end_date",
                "training_link",
                "trainer",
                "status",
            }
            attempted = protected_fields.intersection(self.initial_data)
            if attempted:
                raise serializers.ValidationError(
                    "Les informations d'organisation et le statut sont réservés aux équipes Admin/RH."
                )
            if self.instance is None:
                attrs["status"] = "DRAFT"

        start = attrs.get("training_start_date", getattr(self.instance, "training_start_date", None))
        end = attrs.get("training_end_date", getattr(self.instance, "training_end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({
                "training_end_date": "La date de fin doit être postérieure à la date de début."
            })
        return attrs


class BusinessUnitNeedWorkflowSerializer(BusinessUnitNeedSerializer):
    training_recipient_emails = serializers.SerializerMethodField()
    specific_recipient_emails = serializers.ListField(
        child=serializers.EmailField(), write_only=True, required=False
    )

    class Meta(BusinessUnitNeedSerializer.Meta):
        fields = BusinessUnitNeedSerializer.Meta.fields + [
            "training_audience",
            "training_recipient_emails",
            "specific_recipient_emails",
            "decision_comment",
        ]

    def validate(self, attrs):
        attrs = serializers.ModelSerializer.validate(self, attrs)
        request = self.context.get("request")
        business_unit = attrs.get("business_unit") or getattr(self.instance, "business_unit", None)
        requester_user = attrs.get("requester", getattr(self.instance, "requester", None))

        if requester_user and business_unit and not BusinessUnitMembership.objects.filter(
            business_unit=business_unit, user=requester_user, is_active=True
        ).exists():
            raise serializers.ValidationError({
                "requester": "Ce demandeur n'appartient pas à cette Business Unit."
            })

        recipient_emails = attrs.pop("specific_recipient_emails", None)
        recipient_users = None
        if recipient_emails is not None:
            normalized = list(dict.fromkeys(email.strip().lower() for email in recipient_emails))
            memberships = BusinessUnitMembership.objects.filter(
                business_unit=business_unit, is_active=True, user__email__in=normalized
            ).select_related("user")
            recipient_users = [membership.user for membership in memberships]
            found = {user.email.lower() for user in recipient_users}
            missing = [email for email in normalized if email not in found]
            if missing:
                raise serializers.ValidationError({
                    "specific_recipient_emails": f"Ces emails n'appartiennent pas à cette BU : {', '.join(missing)}"
                })

        audience = attrs.get("training_audience", getattr(self.instance, "training_audience", "ALL"))
        need_type = attrs.get("need_type", getattr(self.instance, "need_type", None))
        if need_type == "TRAINING" and audience == "SPECIFIC":
            existing = self.instance.training_recipients.exists() if self.instance else False
            if (recipient_users is not None and not recipient_users) or (recipient_users is None and not existing):
                raise serializers.ValidationError({
                    "specific_recipient_emails": "Sélectionnez au moins un collaborateur de la BU."
                })
        attrs["_recipient_users"] = recipient_users

        if request and is_bu_manager(request.user):
            if self.instance and self.instance.status in {"CONFIRMED", "REFUSED"}:
                raise serializers.ValidationError("Un besoin déjà traité ne peut plus être modifié.")
            protected = {
                "training_start_date", "training_end_date", "training_link",
                "trainer", "status", "decision_comment",
            }
            if protected.intersection(self.initial_data):
                raise serializers.ValidationError("La décision est réservée au Super Admin.")
            if self.instance is None:
                attrs["status"] = "SUBMITTED"
        elif request and request.user.role != UserRole.SUPER_ADMIN:
            protected = {
                "training_start_date", "training_end_date", "training_link",
                "trainer", "status", "decision_comment",
            }
            if protected.intersection(self.initial_data):
                raise serializers.ValidationError("La décision est réservée au Super Admin.")

        status = attrs.get("status", getattr(self.instance, "status", None))
        if request and request.user.role == UserRole.SUPER_ADMIN and status in {"CONFIRMED", "REFUSED"}:
            comment = attrs.get("decision_comment", getattr(self.instance, "decision_comment", ""))
            if not comment.strip():
                raise serializers.ValidationError({"decision_comment": "Un commentaire est obligatoire."})
            if status == "CONFIRMED" and need_type == "TRAINING":
                required = {
                    "training_start_date": attrs.get("training_start_date", getattr(self.instance, "training_start_date", None)),
                    "training_end_date": attrs.get("training_end_date", getattr(self.instance, "training_end_date", None)),
                    "training_link": attrs.get("training_link", getattr(self.instance, "training_link", "")),
                    "trainer": attrs.get("trainer", getattr(self.instance, "trainer", None)),
                }
                missing = [field for field, value in required.items() if not value]
                if missing:
                    raise serializers.ValidationError({
                        field: "Ce champ est obligatoire pour confirmer une formation."
                        for field in missing
                    })

        start = attrs.get("training_start_date", getattr(self.instance, "training_start_date", None))
        end = attrs.get("training_end_date", getattr(self.instance, "training_end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"training_end_date": "La date de fin doit suivre la date de début."})
        return attrs

    def get_training_recipient_emails(self, obj):
        return list(obj.training_recipients.values_list("email", flat=True))

    def create(self, validated_data):
        recipients = validated_data.pop("_recipient_users", None)
        instance = serializers.ModelSerializer.create(self, validated_data)
        if recipients is not None:
            instance.training_recipients.set(recipients)
        return instance

    def update(self, instance, validated_data):
        recipients = validated_data.pop("_recipient_users", None)
        instance = serializers.ModelSerializer.update(self, instance, validated_data)
        if recipients is not None:
            instance.training_recipients.set(recipients)
        elif instance.training_audience == "ALL":
            instance.training_recipients.clear()
        return instance
