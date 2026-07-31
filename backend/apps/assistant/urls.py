from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet
router=DefaultRouter();router.register("assistant/conversations",ConversationViewSet,basename="assistant-conversation");urlpatterns=router.urls
