from django.contrib import admin
from .models import AuditLog, Notification, NotificationPreference
admin.site.register(Notification); admin.site.register(NotificationPreference)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_email", "method", "path", "status_code")
    search_fields = ("actor_email", "path", "action")
    readonly_fields = [field.name for field in AuditLog._meta.fields]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
