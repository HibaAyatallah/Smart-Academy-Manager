from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TrainingViewSet,
    TrainingSessionViewSet,
    ClientTrainingViewSet,
    ClientTrainingSessionViewSet,
    TrainingEnrollmentViewSet
)

router = DefaultRouter()
router.register(r'trainings', TrainingViewSet, basename='training')
router.register(r'training-sessions', TrainingSessionViewSet, basename='training-session')
router.register(r'client/trainings', ClientTrainingViewSet, basename='client-training')
router.register(r'client/sessions', ClientTrainingSessionViewSet, basename='client-session')
router.register(r'enrollments', TrainingEnrollmentViewSet, basename='enrollment')

app_name = 'trainings'

urlpatterns = [
    path('', include(router.urls)),
]
