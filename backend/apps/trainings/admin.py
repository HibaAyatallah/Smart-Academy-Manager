from django.contrib import admin
from .models import ClientProfile, Training, TrainingSession, TrainingEnrollment, EnrollmentHistory, SessionAttendance, AttendanceHistory, TrainingCertificate

@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "created_at")
    search_fields = ("company_name", "user__email")


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ("title", "training_type", "delivery_mode", "status", "created_at")
    search_fields = ("title", "category")
    list_filter = ("status", "training_type", "delivery_mode", "business_unit", "trainer")
    readonly_fields = ("created_by", "created_at", "updated_at")
    fieldsets = (
        ("Basic Information", {
            "fields": ("title", "description", "training_type", "category", "objectives", "prerequisites", "level")
        }),
        ("Delivery & Duration", {
            "fields": ("duration", "delivery_mode", "image")
        }),
        ("Assignments & Restrictions", {
            "fields": ("trainer", "business_unit", "external_client", "project_name")
        }),
        ("Links", {
            "fields": ("associated_link", "moodle_course_id", "moodle_link")
        }),
        ("Status & Audit", {
            "fields": ("status", "created_by", "created_at", "updated_at")
        }),
    )

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'created_by', None) is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ("training", "start_date", "end_date", "status", "created_at")
    search_fields = ("training__title", "location")
    list_filter = ("status", "trainer")
    readonly_fields = ("created_by", "created_at", "updated_at")
    fieldsets = (
        ("Session details", {
            "fields": ("training", "start_date", "end_date", "start_time", "end_time")
        }),
        ("Delivery", {
            "fields": ("location", "online_link", "trainer", "maximum_participants")
        }),
        ("Assignments & Restrictions", {
            "fields": ("external_client", "status")
        }),
        ("Audit", {
            "fields": ("created_by", "created_at", "updated_at")
        }),
    )

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'created_by', None) is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TrainingEnrollment)
class TrainingEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "training", "session", "status", "final_status", "requested_at")
    search_fields = ("user__email", "training__title")
    list_filter = ("status", "final_status", "manager_decision", "super_admin_decision")
    readonly_fields = ("requested_at", "created_at", "updated_at")
    fieldsets = (
        ("Information", {
            "fields": ("user", "training", "session", "status", "final_status")
        }),
        ("Manager Decision", {
            "fields": ("manager_decision", "manager_comment", "manager_decided_by", "manager_decided_at")
        }),
        ("Super Admin Decision", {
            "fields": ("super_admin_decision", "super_admin_comment", "super_admin_decided_by", "super_admin_decided_at")
        }),
        ("Audit", {
            "fields": ("requested_at", "created_at", "updated_at")
        }),
    )

@admin.register(EnrollmentHistory)
class EnrollmentHistoryAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "previous_status", "new_status", "changed_by", "timestamp")
    search_fields = ("enrollment__user__email",)
    list_filter = ("new_status",)
    readonly_fields = ("timestamp",)

admin.site.register(SessionAttendance)
admin.site.register(AttendanceHistory)
admin.site.register(TrainingCertificate)
