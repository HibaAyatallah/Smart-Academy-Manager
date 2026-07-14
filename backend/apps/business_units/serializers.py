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
            "required_skills",
            "required_level",
            "required_level_label",
            "number_of_profiles",
            "priority",
            "priority_label",
            "expected_date",
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
