from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet, NotificationPreferenceViewSet, NotificationViewSet
router=DefaultRouter(); router.register("notifications",NotificationViewSet,basename="notification"); router.register("notification-preferences",NotificationPreferenceViewSet,basename="notification-preference"); router.register("audit-logs",AuditLogViewSet,basename="audit-log")
urlpatterns=router.urls
