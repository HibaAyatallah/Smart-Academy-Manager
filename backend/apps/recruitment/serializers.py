from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit

from .choices import ApplicationDocumentType, ApplicationStatus, ApplicationType, StudyLevel, OfferStatus
from .models import (
    Application,
    ApplicationDocument,
    ApplicationStatusHistory,
    CandidateProfile,
    InternProfile,
    InternDocument,
    InternDocumentRequirement,
    InternEvaluation,
    Interview,
    Offer,
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


class OfferSerializer(serializers.ModelSerializer):
    business_unit_name = serializers.CharField(source="business_unit.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    application_type_label = serializers.CharField(source="get_application_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "title",
            "description",
            "business_unit",
            "business_unit_name",
            "application_type",
            "application_type_label",
            "required_skills",
            "required_level",
            "number_of_positions",
            "location",
            "start_date",
            "end_date",
            "application_deadline",
            "publication_date",
            "status",
            "status_label",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "business_unit_name",
            "application_type_label",
            "status_label",
            "created_by_email",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        today = timezone.localdate()
        errors = {}
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        deadline = attrs.get("application_deadline", getattr(self.instance, "application_deadline", None))
        
        old_start = getattr(self.instance, "start_date", None) if self.instance else None
        old_end = getattr(self.instance, "end_date", None) if self.instance else None
        old_deadline = getattr(self.instance, "application_deadline", None) if self.instance else None

        if "start_date" in attrs and start and start != old_start and start < today:
            errors["start_date"] = "La date ne peut pas être antérieure à aujourd’hui."
        if "end_date" in attrs and end and end != old_end and end < today:
            errors["end_date"] = "La date ne peut pas être antérieure à aujourd’hui."
        if "application_deadline" in attrs and deadline and deadline != old_deadline and deadline < today:
            errors["application_deadline"] = "La date ne peut pas être antérieure à aujourd’hui."
        if start and end and end < start:
            errors.setdefault("end_date", "La date de fin doit être postérieure ou égale à la date de début.")
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


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
        old_val = getattr(self.instance, "scheduled_at", None) if self.instance else None
        if value != old_val and timezone.localdate(value) < timezone.localdate():
            raise serializers.ValidationError("La date ne peut pas être antérieure à aujourd’hui.")
        return value


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_profile = CandidateProfileSerializer(read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    interviews = InterviewSerializer(many=True, read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    application_type_label = serializers.CharField(source="get_application_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    offer_title = serializers.CharField(source="offer.title", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "candidate_profile",
            "offer",
            "offer_title",
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
    offer = serializers.PrimaryKeyRelatedField(
        queryset=Offer.objects.filter(status=OfferStatus.PUBLISHED),
        required=False,
        allow_null=True,
    )
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

    def validate_offer(self, value):
        if value in (None, ""):
            return None
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
        offer = validated_data.pop("offer", None)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=UserRole.CANDIDATE,
        )
        profile_data = dict(validated_data)
        profile = CandidateProfile.objects.create(user=user, **profile_data)
        application = Application.objects.create(
            candidate_profile=profile,
            offer=offer,
            application_type=application_type,
            motivation_message=motivation_message,
        )
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status="",
            to_status=ApplicationStatus.RECEIVED,
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
        old_val = getattr(self.instance, "scheduled_at", None) if self.instance else None
        if value != old_val and timezone.localdate(value) < timezone.localdate():
            raise serializers.ValidationError("La date ne peut pas être antérieure à aujourd’hui.")
        return value


class AuthenticatedApplicationCreateSerializer(serializers.Serializer):
    offer = serializers.PrimaryKeyRelatedField(
        queryset=Offer.objects.filter(status=OfferStatus.PUBLISHED),
        required=False,
        allow_null=True,
    )
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

    @transaction.atomic
    def create(self, validated_data):
        cv = validated_data.pop("cv")
        cover_letter = validated_data.pop("cover_letter")
        personal_photo = validated_data.pop("personal_photo")
        other_documents = validated_data.pop("other_documents", [])
        offer = validated_data.pop("offer", None)
        application_type = validated_data.pop("application_type")
        motivation_message = validated_data.pop("motivation_message", "")

        user = self.context["request"].user
        profile = user.candidate_profile

        application = Application.objects.create(
            candidate_profile=profile,
            offer=offer,
            application_type=application_type,
            motivation_message=motivation_message,
        )
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status="",
            to_status=ApplicationStatus.RECEIVED,
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


class ApplicationConversionSerializer(serializers.Serializer):
    CONVERSION_CHOICES = (
        ("INTERN", "Stagiaire"),
        ("EMPLOYEE", "Collaborateur"),
    )
    conversion_type = serializers.ChoiceField(choices=CONVERSION_CHOICES)
    business_unit = serializers.PrimaryKeyRelatedField(
        queryset=BusinessUnit.objects.filter(is_active=True)
    )
    supervisor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=[UserRole.EMPLOYEE, UserRole.BU_MANAGER, UserRole.SUPER_ADMIN, UserRole.TRAINER_TUTOR]),
        required=False,
        allow_null=True,
    )
    internship_start = serializers.DateField(required=False, allow_null=True)
    internship_end = serializers.DateField(required=False, allow_null=True)
    internship_type = serializers.CharField(required=False, allow_blank=True, max_length=32)
    school = serializers.CharField(required=False, allow_blank=True, max_length=255)
    specialization = serializers.CharField(required=False, allow_blank=True, max_length=255)
    paid = serializers.BooleanField(required=False, default=False)
    subject_title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    specification_pdf = serializers.FileField(required=False, allow_null=True)

    def validate(self, data):
        from datetime import date
        today = date.today()
        errors = {}
        conversion_type = data.get("conversion_type")
        if conversion_type == "INTERN" and not data.get("supervisor"):
            errors["supervisor"] = "Le superviseur est requis pour un stagiaire."
        start = data.get("internship_start")
        end = data.get("internship_end")
        if start and start < today:
            errors["internship_start"] = "La date ne peut pas être antérieure à aujourd'hui."
        if end and end < today:
            errors["internship_end"] = "La date ne peut pas être antérieure à aujourd'hui."
        if start and end and start > end:
            errors.setdefault("internship_end", "La date de fin doit être postérieure ou égale à la date de début.")
        if errors:
            raise serializers.ValidationError(errors)
        return data


class InternDocumentSerializer(serializers.ModelSerializer):
    validator_email = serializers.EmailField(source="validator.email", read_only=True)

    class Meta:
        model = InternDocument
        fields = [
            "id",
            "intern",
            "document_type",
            "requirement",
            "file",
            "original_name",
            "content_type",
            "size",
            "status",
            "is_validated",
            "validated_at",
            "validator",
            "validator_email",
            "comment",
            "uploaded_at",
        ]
        read_only_fields = ["id", "document_type", "original_name", "content_type", "size", "status", "is_validated", "validated_at", "validator", "validator_email", "uploaded_at"]
        extra_kwargs = {"file": {"write_only": True}}

    def validate_file(self, uploaded_file):
        from pathlib import Path
        allowed = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in allowed or getattr(uploaded_file, "content_type", "") != allowed[extension]:
            raise serializers.ValidationError("Formats autorisés : PDF, PNG, JPG.")
        max_size_mb = getattr(settings, "INTERN_DOCUMENT_MAX_UPLOAD_SIZE_MB", 5)
        if uploaded_file.size > max_size_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Taille maximale : {max_size_mb} Mo.")
        header = uploaded_file.read(12)
        uploaded_file.seek(0)
        signatures = {".pdf": b"%PDF", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff"}
        if not header.startswith(signatures[extension]):
            raise serializers.ValidationError("Le contenu du fichier ne correspond pas au format annoncé.")
        return uploaded_file

    def validate_requirement(self, requirement):
        if not requirement.is_active:
            raise serializers.ValidationError("Ce document n'est plus demandé.")
        return requirement


class InternDocumentRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternDocumentRequirement
        fields = ["id", "document_type", "name", "description", "is_required", "due_date", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class InternEvaluationSerializer(serializers.ModelSerializer):
    evaluator_email = serializers.EmailField(source="evaluator.email", read_only=True)

    class Meta:
        model = InternEvaluation
        fields = [
            "id",
            "intern",
            "evaluation_type",
            "technical_skills",
            "autonomy",
            "communication",
            "teamwork",
            "deadline_respect",
            "work_quality",
            "professionalism",
            "overall_score",
            "comments",
            "evaluator",
            "evaluator_email",
            "created_at",
        ]
        read_only_fields = ["id", "evaluator", "evaluator_email", "created_at"]

    def validate(self, attrs):
        score_fields = [
            "technical_skills", "autonomy", "communication", "teamwork",
            "deadline_respect", "work_quality", "professionalism",
        ]
        for field in score_fields:
            value = attrs.get(field, getattr(self.instance, field, 0))
            if value < 0 or value > 5:
                raise serializers.ValidationError({field: "La note doit être comprise entre 0 et 5."})
        scores = [attrs.get(field, getattr(self.instance, field, 0)) for field in score_fields]
        attrs["overall_score"] = round(sum(scores) / len(scores), 2)
        return attrs


class InternProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    business_unit_name = serializers.CharField(source="business_unit.name", read_only=True)
    supervisor_email = serializers.EmailField(source="supervisor.email", read_only=True)
    documents = InternDocumentSerializer(many=True, read_only=True)
    evaluations = InternEvaluationSerializer(many=True, read_only=True)
    document_requirements = serializers.SerializerMethodField()
    manager_name = serializers.CharField(source="business_unit.manager.full_name", read_only=True)

    class Meta:
        model = InternProfile
        fields = [
            "id",
            "user",
            "user_email",
            "user_full_name",
            "source_application",
            "school",
            "specialization",
            "internship_type",
            "paid",
            "business_unit",
            "business_unit_name",
            "manager_name",
            "supervisor",
            "supervisor_email",
            "subject_title",
            "specification_pdf",
            "internship_start",
            "internship_end",
            "current_status",
            "progress",
            "final_decision",
            "documents",
            "document_requirements",
            "evaluations",
            "created_at",
        ]
        read_only_fields = ["id", "user", "source_application", "created_at"]

    def validate_progress(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La progression doit être comprise entre 0 et 100.")
        return value

    def get_document_requirements(self, obj):
        requirements = InternDocumentRequirement.objects.filter(is_active=True)
        submissions = {}
        for submission in obj.documents.filter(requirement__isnull=False).order_by("requirement_id", "-uploaded_at"):
            submissions.setdefault(submission.requirement_id, submission)
        data = []
        for requirement in requirements:
            item = InternDocumentRequirementSerializer(requirement).data
            submission = submissions.get(requirement.id)
            item["latest_submission"] = InternDocumentSerializer(submission, context=self.context).data if submission else None
            data.append(item)
        return data

    def validate(self, attrs):
        today = timezone.localdate()
        errors = {}
        start = attrs.get("internship_start", getattr(self.instance, "internship_start", None))
        end = attrs.get("internship_end", getattr(self.instance, "internship_end", None))
        # Only reject past dates for values that are actually being changed
        old_start = getattr(self.instance, "internship_start", None) if self.instance else None
        old_end = getattr(self.instance, "internship_end", None) if self.instance else None
        if "internship_start" in attrs and start and start != old_start and start < today:
            errors["internship_start"] = "La date ne peut pas être antérieure à aujourd’hui."
        if "internship_end" in attrs and end and end != old_end and end < today:
            errors["internship_end"] = "La date ne peut pas être antérieure à aujourd’hui."
        if start and end and start > end:
            errors.setdefault("internship_end", "La date de fin doit être postérieure ou égale à la date de début.")
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
