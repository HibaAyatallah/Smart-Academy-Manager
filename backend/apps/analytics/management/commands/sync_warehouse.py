from django.core.management.base import BaseCommand
from django.db import transaction

from apps.business_units.models import BusinessUnit
from apps.recruitment.choices import ApplicationStatus
from apps.recruitment.models import Application
from apps.trainings.models import TrainingEnrollment
from apps.analytics.models import DimBusinessUnit, DimDate, FactApplication, FactTrainingEnrollment

def date_dimension(value):
    item, _ = DimDate.objects.update_or_create(date=value, defaults={"year": value.year, "month": value.month, "quarter": (value.month-1)//3+1})
    return item

class Command(BaseCommand):
    help = "Synchronise de manière idempotente les dimensions et faits KPI."
    @transaction.atomic
    def handle(self, *args, **options):
        dimensions = {}
        for bu in BusinessUnit.objects.all():
            dimensions[bu.id], _ = DimBusinessUnit.objects.update_or_create(source_id=bu.id, defaults={"code":bu.code,"name":bu.name,"is_active":bu.is_active})
        for application in Application.objects.select_related("offer__business_unit"):
            day = date_dimension(application.submitted_at.date())
            bu = application.offer.business_unit if application.offer else None
            end = application.accepted_at or application.rejected_at or application.updated_at
            FactApplication.objects.update_or_create(source_id=application.id, defaults={"date":day,"business_unit":dimensions.get(bu.id) if bu else None,"application_type":application.application_type,"status":application.status,"accepted":application.status==ApplicationStatus.ACCEPTED,"processing_days":max((end.date()-application.submitted_at.date()).days,0)})
        for enrollment in TrainingEnrollment.objects.select_related("training__business_unit", "certificate"):
            day = date_dimension(enrollment.created_at.date()); bu=enrollment.training.business_unit
            FactTrainingEnrollment.objects.update_or_create(source_id=enrollment.id, defaults={"date":day,"business_unit":dimensions.get(bu.id) if bu else None,"status":enrollment.status,"completed":enrollment.status=="COMPLETED","certificate_issued":hasattr(enrollment, "certificate")})
        self.stdout.write(self.style.SUCCESS(f"Warehouse synchronized: {FactApplication.objects.count()} applications, {FactTrainingEnrollment.objects.count()} enrollments."))
