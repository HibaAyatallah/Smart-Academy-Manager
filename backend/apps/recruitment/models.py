from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit

from .choices import (
    ApplicationDocumentType,
    ApplicationStatus,
    ApplicationType,
    StudyLevel,
    OfferStatus,
    InternshipStatus,
    InternDocumentType,
    EvaluationType,
)


def application_document_upload_to(instance, filename: str) -> str:
    if instance.application_id:
        candidate_id = instance.application.candidate_profile.user_id
        application_id = instance.application_id
    else:
        candidate_id = "pending"
        application_id = "pending"
    return f"candidates/{candidate_id}/applications/{application_id}/{instance.document_type.lower()}/{filename}"


class CandidateProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
    )
    phone_number = models.CharField(max_length=32)
    current_school = models.CharField(max_length=255)
    study_level = models.CharField(max_length=32, choices=StudyLevel.choices)
    study_level_other = models.CharField(max_length=255, blank=True)
    study_field = models.CharField(max_length=255, default="")
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self) -> str:
        return self.user.email


class Offer(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    business_unit = models.ForeignKey(
        BusinessUnit, on_delete=models.CASCADE, related_name="offers"
    )
    application_type = models.CharField(
        max_length=32, choices=ApplicationType.choices,
        verbose_name="Type d'offre"
    )
    required_skills = models.TextField(blank=True)
    required_level = models.CharField(max_length=32, choices=StudyLevel.choices, blank=True)
    number_of_positions = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=OfferStatus.choices,
        default=OfferStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_offers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Application(models.Model):
    candidate_profile = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    offer = models.ForeignKey(
        Offer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    application_type = models.CharField(max_length=32, choices=ApplicationType.choices)
    status = models.CharField(
        max_length=32,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.RECEIVED,
    )
    motivation_message = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_applications",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    retention_until = models.DateTimeField(null=True, blank=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["application_type", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["submitted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.candidate_profile.user.email} - {self.application_type}"

    @property
    def candidate(self):
        return self.candidate_profile.user

    @property
    def is_final(self) -> bool:
        return self.status in {
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.ARCHIVED,
        }

    def set_retention_deadline(self) -> None:
        days = getattr(settings, "RECRUITMENT_RETENTION_DAYS", 730)
        self.retention_until = timezone.now() + timedelta(days=days)


class ApplicationDocument(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=32, choices=ApplicationDocumentType.choices)
    file = models.FileField(upload_to=application_document_upload_to)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_application_documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_type", "-uploaded_at"]

    def __str__(self) -> str:
        return self.original_name


class Interview(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    meeting_link = models.URLField(blank=True)
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_interviews",
    )
    notes = models.TextField(blank=True)
    result = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_interviews",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self) -> str:
        return f"{self.application_id} - {self.scheduled_at:%Y-%m-%d %H:%M}"


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=32, choices=ApplicationStatus.choices, blank=True)
    to_status = models.CharField(max_length=32, choices=ApplicationStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="application_status_changes",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Application status histories"


class InternProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="intern_profile",
    )
    source_application = models.OneToOneField(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_intern_profile",
    )
    school = models.CharField(max_length=255, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    internship_type = models.CharField(max_length=32, blank=True)
    paid = models.BooleanField(default=False)
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interns",
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_interns",
    )
    subject_title = models.CharField(max_length=255, blank=True)
    specification_pdf = models.FileField(upload_to="internships/specifications/", blank=True, null=True)
    internship_start = models.DateField(null=True, blank=True)
    internship_end = models.DateField(null=True, blank=True)
    current_status = models.CharField(
        max_length=32,
        choices=InternshipStatus.choices,
        default=InternshipStatus.UPCOMING,
    )
    progress = models.IntegerField(default=0)
    final_decision = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.email

class InternDocument(models.Model):
    intern = models.ForeignKey(
        InternProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=32, choices=InternDocumentType.choices)
    file = models.FileField(upload_to="internships/documents/")
    is_validated = models.BooleanField(default=False)
    validated_at = models.DateTimeField(null=True, blank=True)
    validator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_intern_documents",
    )
    comment = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.intern.user.email} - {self.get_document_type_display()}"


class InternEvaluation(models.Model):
    intern = models.ForeignKey(
        InternProfile,
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    evaluation_type = models.CharField(max_length=32, choices=EvaluationType.choices)
    technical_skills = models.IntegerField(default=0)
    autonomy = models.IntegerField(default=0)
    communication = models.IntegerField(default=0)
    teamwork = models.IntegerField(default=0)
    deadline_respect = models.IntegerField(default=0)
    work_quality = models.IntegerField(default=0)
    professionalism = models.IntegerField(default=0)
    overall_score = models.FloatField(default=0.0)
    comments = models.TextField(blank=True)
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intern_evaluations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.intern.user.email} - {self.get_evaluation_type_display()}"


class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    source_application = models.OneToOneField(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_employee_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.email


class SensitiveAuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recruitment_audit_logs",
    )
    application = models.ForeignKey(
        Application,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.action
