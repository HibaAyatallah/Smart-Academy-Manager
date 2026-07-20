from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ProjectCommentViewSet, ProjectDeliverableViewSet, ProjectDocumentViewSet, ProjectViewSet
router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("project-deliverables", ProjectDeliverableViewSet, basename="project-deliverable")
router.register("project-comments", ProjectCommentViewSet, basename="project-comment")
router.register("project-documents", ProjectDocumentViewSet, basename="project-document")
urlpatterns = [path("", include(router.urls))]
