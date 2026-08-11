from django.contrib import admin
from apps.accounts.roles import is_super_admin
from .models import ContactMessage
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "full_name", "email", "subject", "status")
    list_filter = ("status", "request_type", "created_at")
    search_fields = ("full_name", "email", "subject", "message")
    readonly_fields = ("full_name", "email", "request_type", "subject", "message", "created_at")

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_super_admin(request.user)
