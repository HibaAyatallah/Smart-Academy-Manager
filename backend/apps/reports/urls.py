from django.urls import path
from .views import ReportExportView, ReportView, HRDashboardView

urlpatterns=[
    path("reports/summary/", ReportView.as_view(), name="report-summary"),
    path("reports/hr-dashboard/", HRDashboardView.as_view(), name="hr-dashboard"),
    path("reports/export/<str:export_format>/", ReportExportView.as_view(), name="report-export")
]
