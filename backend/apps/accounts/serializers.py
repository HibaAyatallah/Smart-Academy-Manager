from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .choices import UserRole
from .roles import is_super_admin

User = get_user_model()


class UserBusinessUnitMixin:
    business_units = serializers.SerializerMethodField()
    business_unit_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    def get_business_units(self, obj):
        from apps.business_units.models import BusinessUnit

        return list(
            BusinessUnit.objects.filter(
                models.Q(manager=obj)
                | models.Q(memberships__user=obj, memberships__is_active=True)
            ).distinct().values("id", "name", "code")
        )

    def validate_business_unit_id(self, value):
        if value is None:
            return value
        from apps.business_units.models import BusinessUnit

        if not BusinessUnit.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Cette Business Unit n'existe pas ou n'est pas active.")
        return value

    def assign_business_unit(self, user, business_unit_id):
        from apps.business_units.models import BusinessUnit, BusinessUnitMembership

        if user.role == UserRole.EMPLOYEE:
            BusinessUnitMembership.objects.filter(user=user, is_active=True).exclude(
                business_unit_id=business_unit_id
            ).update(is_active=False)
            if business_unit_id:
                membership = BusinessUnitMembership.objects.filter(
                    user=user, business_unit_id=business_unit_id, is_active=False
                ).order_by("-joined_at").first()
                if membership:
                    membership.is_active = True
                    membership.save(update_fields=["is_active"])
                else:
                    BusinessUnitMembership.objects.create(
                        user=user, business_unit_id=business_unit_id, is_active=True
                    )
        elif user.role == UserRole.BU_MANAGER and business_unit_id:
            BusinessUnit.objects.filter(pk=business_unit_id).update(manager=user)
        elif user.role != UserRole.BU_MANAGER:
            BusinessUnitMembership.objects.filter(user=user, is_active=True).update(is_active=False)


class SmartAcademyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = user.full_name
        return token


class UserSerializer(UserBusinessUnitMixin, serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    business_units = serializers.SerializerMethodField()
    business_unit_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "role",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
            "business_units",
            "business_unit_id",
        ]
        read_only_fields = ["id", "full_name", "is_staff", "created_at", "updated_at"]

    def validate_role(self, value):
        """Only Super Administrators may assign the SUPER_ADMIN role."""
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        if value == UserRole.SUPER_ADMIN and not is_super_admin(request_user):
            raise serializers.ValidationError(
                "Seul un Super Administrateur peut attribuer ce rôle."
            )
        return value

    def update(self, instance, validated_data):
        business_unit_id = validated_data.pop("business_unit_id", None)
        instance = super().update(instance, validated_data)
        if "business_unit_id" in self.initial_data or "role" in self.initial_data:
            self.assign_business_unit(instance, business_unit_id)
        return instance


class UserCreateSerializer(UserBusinessUnitMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    business_units = serializers.SerializerMethodField()
    business_unit_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "is_active",
            "business_units",
            "business_unit_id",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        business_unit_id = validated_data.pop("business_unit_id", None)
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        self.assign_business_unit(user, business_unit_id)
        return user

    def validate_role(self, value):
        """Only Super Administrators may assign the SUPER_ADMIN role."""
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        if value == UserRole.SUPER_ADMIN and not is_super_admin(request_user):
            raise serializers.ValidationError(
                "Seul un Super Administrateur peut attribuer ce rôle."
            )
        return value


class MeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "role",
            "preferred_language",
        ]
        read_only_fields = ["id", "email", "phone_number", "full_name", "role"]


class ContactDetailsSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.RegexField(r"^\+?[0-9][0-9 .()-]{6,30}$", required=False, allow_blank=True)
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Le mot de passe actuel est incorrect.")
        return value


    def validate_email(self, value):
        normalized = User.objects.normalize_email(value).lower()
        if User.objects.exclude(pk=self.context["request"].user.pk).filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return normalized

    def validate(self, attrs):
        if not {"email", "phone_number"}.intersection(attrs):
            raise serializers.ValidationError("Aucune modification fournie.")
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        changed = []
        for field in ("email", "phone_number"):
            if field in self.validated_data and getattr(user, field) != self.validated_data[field]:
                setattr(user, field, self.validated_data[field])
                changed.append(field)
        if changed:
            user.save(update_fields=[*changed, "updated_at"])
        return user, changed


class PreferredLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["preferred_language"]

    def update(self, instance, validated_data):
        instance.preferred_language = validated_data["preferred_language"]
        instance.save(update_fields=["preferred_language", "updated_at"])
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Le mot de passe actuel est incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirmation"]:
            raise serializers.ValidationError({"confirmation": "Les nouveaux mots de passe ne correspondent pas."})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user
