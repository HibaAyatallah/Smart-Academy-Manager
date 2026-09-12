from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .choices import UserRole
from .roles import is_super_admin

User = get_user_model()


class UserBusinessUnitMixin:
    business_units = serializers.SerializerMethodField()
    business_unit_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_business_units(self, obj) -> list[dict[str, object]]:
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
        from apps.business_units.choices import ALLOWED_BUSINESS_UNITS
        from apps.business_units.models import BusinessUnit

        if not BusinessUnit.objects.filter(
            pk=value, is_active=True, code__in=ALLOWED_BUSINESS_UNITS
        ).exists():
            raise serializers.ValidationError("Cette Business Unit n'existe pas ou n'est pas active.")
        return value

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", UserRole.CANDIDATE))
        if role == UserRole.INTERN and (self.instance is None or not hasattr(self.instance, "intern_profile")):
            raise serializers.ValidationError({"role": "Créez le dossier stagiaire par conversion de candidature ou par l'import métier ; la création directe d'un compte INTERN est interdite."})
        if role == UserRole.CLIENT and attrs.get("business_unit_id") is not None:
            raise serializers.ValidationError({"business_unit_id": "Un client externe ne peut pas avoir de BU interne."})
        return attrs

    @staticmethod
    def ensure_business_profile(user):
        from apps.trainings.models import ClientProfile
        from apps.recruitment.models import CandidateProfile, EmployeeProfile
        if user.role == UserRole.CLIENT:
            ClientProfile.objects.get_or_create(user=user)
        elif user.role in (UserRole.EMPLOYEE, UserRole.TRAINER_TUTOR, UserRole.BU_MANAGER):
            EmployeeProfile.objects.get_or_create(user=user)
        elif user.role == UserRole.CANDIDATE:
            CandidateProfile.objects.get_or_create(user=user, defaults={"phone_number": user.phone_number})


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
        from apps.business_units.services import UNSET, assign_business_unit, current_business_unit, validate_supervised_interns
        business_unit_id = validated_data.pop("business_unit_id", UNSET)
        with transaction.atomic():
            instance = User.objects.select_for_update().get(pk=instance.pk)
            previous = current_business_unit(instance)
            old_role = instance.role
            instance = super().update(instance, validated_data)
            self.ensure_business_profile(instance)
            if business_unit_id is not UNSET or instance.role != old_role:
                target = getattr(previous, "pk", None) if business_unit_id is UNSET else business_unit_id
                assign_business_unit(instance, target, request=self.context.get("request"), previous=previous)
            validate_supervised_interns(instance)
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
        with transaction.atomic():
            user = User.objects.create_user(
                password=password,
                must_change_password=True,
                **validated_data,
            )
            from apps.business_units.services import assign_business_unit
            self.ensure_business_profile(user)
            assign_business_unit(user, business_unit_id, request=self.context.get("request"))
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
            "must_change_password",
        ]
        read_only_fields = [
            "id",
            "email",
            "phone_number",
            "full_name",
            "role",
            "must_change_password",
        ]


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
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validated_email(self) -> str:
        return User.objects.normalize_email(self.validated_data["email"]).lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {"invalid_token": "Ce lien de réinitialisation est invalide ou expiré."}

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, UnicodeDecodeError):
            self.fail("invalid_token")
        if not default_token_generator.check_token(user, attrs["token"]):
            self.fail("invalid_token")
        if attrs["new_password"] != attrs["confirmation"]:
            raise serializers.ValidationError({"confirmation": "Les mots de passe ne correspondent pas."})
        validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        return user
