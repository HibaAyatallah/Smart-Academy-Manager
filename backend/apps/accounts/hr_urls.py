from django.urls import path

from .hr_views import HRCollaboratorsByBUView, HRInternDetailView, HRInternListView

urlpatterns = [
    path("hr/interns/", HRInternListView.as_view(), name="hr-intern-list"),
    path("hr/interns/<int:pk>/", HRInternDetailView.as_view(), name="hr-intern-detail"),
    path("hr/collaborators/", HRCollaboratorsByBUView.as_view(), name="hr-collaborators-by-bu"),
]
