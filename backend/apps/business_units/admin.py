from django.contrib import admin

from .models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed


class BusinessUnitMembershipInline(admin.TabularInline):
    model = BusinessUnitMembership
    extra = 1
    autocomplete_fields = ["user"]


class BusinessUnitNeedInline(admin.TabularInline):
    model = BusinessUnitNeed
    extra = 1
    autocomplete_fields = ["created_by"]


@admin.register(BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "manager", "is_active", "created_at"]
    list_filter = ["is_active", "manager"]
    search_fields = ["name", "code", "manager__email", "manager__first_name", "manager__last_name"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["manager"]
    inlines = [BusinessUnitMembershipInline, BusinessUnitNeedInline]
    fieldsets = (
        ("Informations principales", {"fields": ("name", "code", "description")}),
        ("Gestion", {"fields": ("manager", "is_active")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(BusinessUnitMembership)
class BusinessUnitMembershipAdmin(admin.ModelAdmin):
    list_display = ["business_unit", "user", "position", "is_active", "joined_at"]
    list_filter = ["is_active", "business_unit"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "business_unit__name", "position"]
    autocomplete_fields = ["business_unit", "user"]


@admin.register(BusinessUnitNeed)
class BusinessUnitNeedAdmin(admin.ModelAdmin):
    list_display = ["title", "business_unit", "need_type", "priority", "status", "created_at"]
    list_filter = ["status", "priority", "need_type", "required_level", "business_unit"]
    search_fields = ["title", "description", "business_unit__name"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["business_unit", "created_by"]
    fieldsets = (
        ("Informations principales", {"fields": ("business_unit", "title", "description")}),
        ("Détails du besoin", {"fields": ("need_type", "required_skills", "required_level", "number_of_profiles")}),
        ("Planification & Statut", {"fields": ("priority", "expected_date", "status")}),
        ("Traçabilité", {"fields": ("created_by", "created_at", "updated_at")}),
    )
