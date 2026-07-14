from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.choices import UserRole

from .choices import ApplicationDocumentType, ApplicationStatus, ApplicationType, StudyLevel
from .models import (
    Application,
    ApplicationDocument,
    ApplicationStatusHistory,
    CandidateProfile,
    EmployeeProfile,
    InternProfile,
    Interview,
)
from .validators import validate_application_file

User = get_user_model()


class CandidateProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    study_level_label = serializers.CharField(source="get_study_level_display", read_only=True)

    class Meta:
        model = CandidateProfile
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "phone_number",
            "current_school",
            "study_level",
            "study_level_label",
            "study_level_other",
            "study_field",
            "linkedin_url",
            "portfolio_url",
            "address",
        ]


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "application",
            "document_type",
            "download_url",
            "original_name",
            "content_type",
            "size",
            "uploaded_by_email",
            "uploaded_at",
        ]
        read_only_fields = [
            "id",
            "application",
            "download_url",
            "original_name",
            "content_type",
            "size",
            "uploaded_by_email",
            "uploaded_at",
        ]

    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/application-documents/{obj.pk}/download/"
        if request:
            return request.build_absolute_uri(path)
        return path


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by_email",
            "comment",
            "created_at",
        ]


class InterviewSerializer(serializers.ModelSerializer):
    interviewer_email = serializers.EmailField(source="interviewer.email", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Interview
        fields = [
            "id",
            "application",
            "scheduled_at",
            "location",
            "meeting_link",
            "interviewer",
            "interviewer_email",
            "notes",
            "result",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by_email", "created_at", "updated_at"]

    def validate_scheduled_at(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La date d'entretien doit être future.")
        return value


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_profile = CandidateProfileSerializer(read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    interviews = InterviewSerializer(many=True, read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    application_type_label = serializers.CharField(source="get_application_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "candidate_profile",
            "application_type",
            "application_type_label",
            "status",
            "status_label",
            "motivation_message",
            "rejection_reason",
            "submitted_at",
            "updated_at",
            "accepted_at",
            "rejected_at",
            "cancelled_at",
            "retention_until",
            "documents",
            "interviews",
            "status_history",
        ]
        read_only_fields = fields


class PublicApplicationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=32)
    current_school = serializers.CharField(max_length=255)
    study_level = serializers.ChoiceField(choices=StudyLevel.choices)
    study_level_other = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    study_field = serializers.CharField(max_length=255)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    portfolio_url = serializers.URLField(required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    application_type = serializers.ChoiceField(choices=ApplicationType.choices)
    motivation_message = serializers.CharField(required=False, allow_blank=True)
    cv = serializers.FileField(write_only=True)
    cover_letter = serializers.FileField(write_only=True)
    personal_photo = serializers.FileField(write_only=True)
    other_documents = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return email

    def validate_cv(self, value):
        validate_application_file(value, ApplicationDocumentType.CV)
        return value

    def validate_cover_letter(self, value):
        validate_application_file(value, ApplicationDocumentType.COVER_LETTER)
        return value

    def validate_personal_photo(self, value):
        validate_application_file(value, ApplicationDocumentType.PERSONAL_PHOTO)
        return value

    def validate_other_documents(self, value):
        for document in value:
            validate_application_file(document, ApplicationDocumentType.OTHER)
        return value

    def validate(self, attrs):
        study_level = attrs.get("study_level")
        study_level_other = attrs.get("study_level_other", "").strip()
        if study_level == StudyLevel.OTHER and not study_level_other:
            raise serializers.ValidationError(
                {"study_level_other": "Précisez votre niveau d'études."}
            )
        if study_level != StudyLevel.OTHER:
            attrs["study_level_other"] = ""
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        cv = validated_data.pop("cv")
        cover_letter = validated_data.pop("cover_letter")
        personal_photo = validated_data.pop("personal_photo")
        other_documents = validated_data.pop("other_documents", [])
        password = validated_data.pop("password")
        application_type = validated_data.pop("application_type")
        motivation_message = validated_data.pop("motivation_message", "")
        email = validated_data.pop("email")
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        phone_number = validated_data.get("phone_number", "")

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=UserRole.CANDIDATE,
        )
        profile = CandidateProfile.objects.create(user=user, **validated_data)
        application = Application.objects.create(
            candidate_profile=profile,
            application_type=application_type,
            motivation_message=motivation_message,
        )
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status="",
            to_status=ApplicationStatus.SUBMITTED,
            changed_by=user,
            comment="Candidature déposée.",
        )

        self._create_document(application, cv, ApplicationDocumentType.CV, user)
        self._create_document(
            application,
            cover_letter,
            ApplicationDocumentType.COVER_LETTER,
            user,
        )
        self._create_document(
            application,
            personal_photo,
            ApplicationDocumentType.PERSONAL_PHOTO,
            user,
        )
        for document in other_documents:
            self._create_document(application, document, ApplicationDocumentType.OTHER, user)

        return application

    def _create_document(self, application, uploaded_file, document_type, user):
        return ApplicationDocument.objects.create(
            application=application,
            document_type=document_type,
            file=uploaded_file,
            original_name=uploaded_file.name,
            content_type=getattr(uploaded_file, "content_type", ""),
            size=uploaded_file.size,
            uploaded_by=user,
        )


class ApplicationDocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=ApplicationDocumentType.choices)
    file = serializers.FileField()

    def validate(self, attrs):
        validate_application_file(attrs["file"], attrs["document_type"])
        return attrs


class ApplicationTransitionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)


class ApplicationRejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


class ScheduleInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = [
            "scheduled_at",
            "location",
            "meeting_link",
            "interviewer",
            "notes",
        ]

    def validate_scheduled_at(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La date d'entretien doit être future.")
        return value
