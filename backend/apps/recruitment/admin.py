from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, IntegerField, Prefetch, Value, When
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.formats import date_format
from django.utils.html import format_html, format_html_join

from .choices import ApplicationDocumentType, ApplicationStatus, ApplicationType
from .models import (
    Application,
    ApplicationDocument,
    ApplicationStatusHistory,
    CandidateProfile,
    EmployeeProfile,
    InternProfile,
    Interview,
    SensitiveAuditLog,
)
from .permissions import can_access_application_document


APPLICATION_TYPE_ADMIN_LABELS = {
    ApplicationType.PFA_INTERNSHIP: "Stage PFA",
    ApplicationType.PFE_INTERNSHIP: "Stage PFE",
    ApplicationType.HIRING: "Embauche",
}


class ApplicationTypeListFilter(admin.SimpleListFilter):
    title = "Type de candidature"
    parameter_name = "application_type"

    def lookups(self, request, model_admin):
        return APPLICATION_TYPE_ADMIN_LABELS.items()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(applications__application_type=self.value()).distinct()
        return queryset


class CandidateProfileAdminForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = "__all__"
        labels = {
            "user": "Utilisateur",
            "phone_number": "Telephone",
            "current_school": "Ecole / Universite",
            "study_level": "Niveau d'etudes",
            "study_level_other": "Niveau d'etudes personnalise",
            "study_field": "Filiere / Domaine",
            "linkedin_url": "LinkedIn",
            "portfolio_url": "GitHub / site web / portfolio",
            "address": "Adresse",
        }


def document_view_url(document):
    return reverse("admin:recruitment_applicationdocument_view", args=[document.pk])


def secure_document_link(document):
    if not document or not document.pk:
        return "-"
    return format_html(
        '<a class="button" href="{}" target="_blank" rel="noopener">Voir le document</a>',
        document_view_url(document),
    )


def photo_preview(document):
    if (
        not document
        or not document.pk
        or document.document_type != ApplicationDocumentType.PERSONAL_PHOTO
    ):
        return "-"
    return format_html(
        '<img src="{}" alt="Photo personnelle" '
        'style="width:72px;height:72px;object-fit:cover;border-radius:6px;" />',
        document_view_url(document),
    )


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    readonly_fields = (
        "view_document",
        "personal_photo_preview",
        "original_name",
        "content_type",
        "size",
        "uploaded_at",
    )

    @admin.display(description="Document")
    def view_document(self, obj):
        return secure_document_link(obj)

    @admin.display(description="Apercu photo")
    def personal_photo_preview(self, obj):
        return photo_preview(obj)


class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class CandidateApplicationInline(admin.StackedInline):
    """Read-only recruitment dossier shown from the candidate profile."""

    model = Application
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Candidature"
    verbose_name_plural = "Candidatures (de la plus recente a la plus ancienne)"
    readonly_fields = (
        "reference_display",
        "open_application",
        "application_type_display",
        "status_display",
        "submitted_at_display",
        "updated_at_display",
        "documents_display",
        "status_history_display",
        "interviews_display",
    )
    fieldsets = (
        (
            "Candidature",
            {
                "fields": (
                    "reference_display",
                    "application_type_display",
                    "status_display",
                    "submitted_at_display",
                    "updated_at_display",
                    "open_application",
                )
            },
        ),
        ("Documents", {"fields": ("documents_display",)}),
        ("Historique des statuts", {"fields": ("status_history_display",)}),
        ("Entretiens", {"fields": ("interviews_display",)}),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("reviewed_by")
            .prefetch_related(
                Prefetch(
                    "documents",
                    queryset=ApplicationDocument.objects.order_by("document_type", "-uploaded_at"),
                ),
                Prefetch(
                    "status_history",
                    queryset=ApplicationStatusHistory.objects.select_related("changed_by").order_by(
                        "-created_at"
                    ),
                ),
                Prefetch(
                    "interviews",
                    queryset=Interview.objects.select_related("interviewer").order_by("-scheduled_at"),
                ),
            )
            .order_by("-submitted_at")
        )

    @admin.display(description="Reference")
    def reference_display(self, obj):
        return f"#{obj.pk}"

    @admin.display(description="Type de stage / candidature")
    def application_type_display(self, obj):
        return APPLICATION_TYPE_ADMIN_LABELS.get(
            obj.application_type,
            obj.get_application_type_display(),
        )

    @admin.display(description="Statut actuel")
    def status_display(self, obj):
        return obj.get_status_display()

    @admin.display(description="Date de depot")
    def submitted_at_display(self, obj):
        return obj.submitted_at

    @admin.display(description="Derniere modification")
    def updated_at_display(self, obj):
        return obj.updated_at

    @admin.display(description="Ouvrir la candidature")
    def open_application(self, obj):
        return format_html(
            '<a class="button" href="{}">Ouvrir la candidature complete</a>',
            reverse("admin:recruitment_application_change", args=[obj.pk]),
        )

    @admin.display(description="Documents securises")
    def documents_display(self, obj):
        documents = list(obj.documents.all())
        if not documents:
            return "Aucun document."

        return format_html_join(
            "<br>",
            "{} : {}",
            (
                (
                    document.get_document_type_display(),
                    secure_document_link(document),
                )
                for document in documents
            ),
        )

    @admin.display(description="Changements de statut")
    def status_history_display(self, obj):
        history_entries = list(obj.status_history.all())
        if not history_entries:
            return "Aucun changement de statut."

        return format_html_join(
            "<br>",
            "{} → {} — {} — {} — {}",
            (
                (
                    entry.get_from_status_display() if entry.from_status else "Creation",
                    entry.get_to_status_display(),
                    date_format(entry.created_at, "DATETIME_FORMAT"),
                    entry.changed_by or "Systeme",
                    entry.comment or "-",
                )
                for entry in history_entries
            ),
        )

    @admin.display(description="Entretiens associes")
    def interviews_display(self, obj):
        interviews = list(obj.interviews.all())
        if not interviews:
            return "Aucun entretien."

        return format_html_join(
            "<br>",
            "{} — {} — {} — {}",
            (
                (
                    date_format(interview.scheduled_at, "DATETIME_FORMAT"),
                    interview.location or interview.meeting_link or "Lieu a preciser",
                    interview.interviewer or "Intervenant non assigne",
                    interview.notes or interview.result or "-",
                )
                for interview in interviews
            ),
        )


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    form = CandidateProfileAdminForm
    list_display = (
        "email_display",
        "application_type_display",
        "school_display",
        "study_level_display",
        "study_field_display",
        "cv_display",
        "application_status_display",
        "created_at_display",
    )
    list_filter = (ApplicationTypeListFilter,)
    search_fields = ("user__email", "user__first_name", "user__last_name")
    inlines = [CandidateApplicationInline]
    readonly_fields = (
        "candidate_name_display",
        "candidate_email_display",
        "application_type_display",
        "created_at_display",
        "updated_at_display",
    )
    fieldsets = (
        (
            "Informations personnelles",
            {
                "fields": (
                    "user",
                    "candidate_name_display",
                    "candidate_email_display",
                    "phone_number",
                    "address",
                )
            },
        ),
        (
            "Formation et candidature",
            {
                "fields": (
                    "application_type_display",
                    "current_school",
                    "study_level",
                    "study_level_other",
                    "study_field",
                )
            },
        ),
        (
            "Liens professionnels",
            {
                "fields": (
                    "linkedin_url",
                    "portfolio_url",
                )
            },
        ),
        (
            "Suivi technique",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at_display",
                    "updated_at_display",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related(
                Prefetch(
                    "applications",
                    queryset=Application.objects.prefetch_related(
                        Prefetch(
                            "documents",
                            queryset=ApplicationDocument.objects.filter(
                                document_type=ApplicationDocumentType.CV
                            ),
                            to_attr="cv_documents"
                        )
                    ).order_by("-submitted_at"),
                )
            )
        )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:
            readonly_fields.append("user")
        return readonly_fields

    @admin.display(description="Nom et prenom")
    def candidate_name_display(self, obj):
        if not obj or not obj.user_id:
            return "-"
        return obj.user.full_name

    @admin.display(description="Email")
    def candidate_email_display(self, obj):
        if not obj or not obj.user_id:
            return "-"
        return obj.user.email

    @admin.display(description="Email", ordering="user__email")
    def email_display(self, obj):
        return obj.user.email

    @admin.display(description="Type de candidature")
    def application_type_display(self, obj):
        application = next(iter(obj.applications.all()), None)
        if not application:
            return "-"
        return APPLICATION_TYPE_ADMIN_LABELS.get(
            application.application_type,
            application.get_application_type_display(),
        )

    @admin.display(description="CV")
    def cv_display(self, obj):
        application = next(iter(obj.applications.all()), None)
        if not application:
            return "Aucun CV"
            
        cv_doc = next(iter(getattr(application, "cv_documents", [])), None)
        if not cv_doc:
            cv_doc = application.documents.filter(document_type=ApplicationDocumentType.CV).first()
            if not cv_doc:
                return "Aucun CV"
                
        return format_html(
            '<a class="button" href="{}" target="_blank" rel="noopener" style="white-space: nowrap;">Voir le CV</a>',
            document_view_url(cv_doc)
        )

    @admin.display(description="Statut de la candidature")
    def application_status_display(self, obj):
        application = next(iter(obj.applications.all()), None)
        if not application:
            return "Aucune candidature"
            
        status_label = application.get_status_display()
        color = "inherit"
        if application.status == ApplicationStatus.SUBMITTED:
            color = "#1f6feb"
        elif application.status in [ApplicationStatus.UNDER_REVIEW, ApplicationStatus.PRESELECTED, ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.INTERVIEW_COMPLETED]:
            color = "#d29922"
        elif application.status == ApplicationStatus.ACCEPTED:
            color = "#238636"
        elif application.status in [ApplicationStatus.REJECTED, ApplicationStatus.CANCELLED]:
            color = "#da3633"
            
        return format_html('<strong style="color: {};">{}</strong>', color, status_label)

    @admin.display(description="Ecole / Universite", ordering="current_school")
    def school_display(self, obj):
        return obj.current_school

    @admin.display(description="Niveau d'etudes", ordering="study_level")
    def study_level_display(self, obj):
        return obj.get_study_level_display()

    @admin.display(description="Filiere / Domaine", ordering="study_field")
    def study_field_display(self, obj):
        return obj.study_field

    @admin.display(description="Date de creation", ordering="created_at")
    def created_at_display(self, obj):
        return obj.created_at

    @admin.display(description="Derniere mise a jour", ordering="updated_at")
    def updated_at_display(self, obj):
        return obj.updated_at


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "application_type", "status", "submitted_at")
    list_filter = ("application_type", "status")
    search_fields = (
        "candidate_profile__user__email",
        "candidate_profile__user__first_name",
        "candidate_profile__user__last_name",
    )
    inlines = [ApplicationDocumentInline, InterviewInline]


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "from_status", "to_status", "changed_by", "created_at")
    list_filter = ("to_status",)

    def has_module_permission(self, request):
        return False


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "candidate_email",
        "document_type_display",
        "original_name",
        "view_document",
        "uploaded_at",
    )
    list_filter = ("document_type",)
    search_fields = (
        "application__candidate_profile__user__email",
        "original_name",
    )
    readonly_fields = (
        "candidate_email",
        "document_type_display",
        "view_document",
        "personal_photo_preview",
        "original_name",
        "content_type",
        "size",
        "uploaded_at",
    )

    def has_module_permission(self, request):
        return False

    def get_urls(self):
        return [
            path(
                "<int:document_id>/view/",
                self.admin_site.admin_view(self.view_document_file),
                name="recruitment_applicationdocument_view",
            ),
        ] + super().get_urls()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("application__candidate_profile__user")
            .annotate(
                document_type_order=Case(
                    When(document_type=ApplicationDocumentType.CV, then=Value(1)),
                    When(document_type=ApplicationDocumentType.COVER_LETTER, then=Value(2)),
                    When(document_type=ApplicationDocumentType.PERSONAL_PHOTO, then=Value(3)),
                    When(document_type=ApplicationDocumentType.OTHER, then=Value(4)),
                    default=Value(99),
                    output_field=IntegerField(),
                )
            )
            .order_by(
                "application__candidate_profile__user__email",
                "document_type_order",
                "uploaded_at",
            )
        )

    @admin.display(
        description="Candidat",
        ordering="application__candidate_profile__user__email",
    )
    def candidate_email(self, obj):
        return obj.application.candidate_profile.user.email

    @admin.display(description="Type de document", ordering="document_type_order")
    def document_type_display(self, obj):
        return obj.get_document_type_display()

    @admin.display(description="Document")
    def view_document(self, obj):
        return secure_document_link(obj)

    @admin.display(description="Apercu photo")
    def personal_photo_preview(self, obj):
        return photo_preview(obj)

    def view_document_file(self, request, document_id):
        document = get_object_or_404(
            ApplicationDocument.objects.select_related(
                "application__candidate_profile__user"
            ),
            pk=document_id,
        )
        if not can_access_application_document(request.user, document):
            raise PermissionDenied
        if not document.file:
            raise Http404
        return FileResponse(
            document.file.open("rb"),
            as_attachment=False,
            filename=document.original_name,
            content_type=document.content_type or "application/octet-stream",
        )


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("application", "scheduled_at", "interviewer", "location")
    search_fields = ("application__candidate_profile__user__email",)


@admin.register(InternProfile)
class InternProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "source_application", "created_at")


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "source_application", "created_at")


@admin.register(SensitiveAuditLog)
class SensitiveAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "application", "created_at")
    list_filter = ("action",)
    readonly_fields = ("action", "actor", "application", "details", "created_at")
