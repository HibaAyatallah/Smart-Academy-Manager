from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BusinessUnitMembershipViewSet,
    BusinessUnitNeedViewSet,
    BusinessUnitViewSet,
)

router = DefaultRouter()
router.register(r"business-units", BusinessUnitViewSet, basename="business-unit")
router.register(r"business-unit-memberships", BusinessUnitMembershipViewSet, basename="business-unit-membership")
router.register(r"business-unit-needs", BusinessUnitNeedViewSet, basename="business-unit-need")

urlpatterns = [
    path("", include(router.urls)),
]
