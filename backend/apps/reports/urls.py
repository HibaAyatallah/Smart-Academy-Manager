from django.urls import path
from .views import ReportExportView,ReportView
urlpatterns=[path("reports/summary/",ReportView.as_view(),name="report-summary"),path("reports/export/<str:export_format>/",ReportExportView.as_view(),name="report-export")]
