from django.db import models

class DimDate(models.Model):
    date = models.DateField(unique=True)
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    quarter = models.PositiveSmallIntegerField()

class DimBusinessUnit(models.Model):
    source_id = models.PositiveBigIntegerField(unique=True)
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    synced_at = models.DateTimeField(auto_now=True)

class FactApplication(models.Model):
    source_id = models.PositiveBigIntegerField(unique=True)
    date = models.ForeignKey(DimDate, on_delete=models.PROTECT)
    business_unit = models.ForeignKey(DimBusinessUnit, null=True, blank=True, on_delete=models.PROTECT)
    application_type = models.CharField(max_length=32)
    status = models.CharField(max_length=32)
    accepted = models.BooleanField(default=False)
    processing_days = models.PositiveIntegerField(default=0)
    synced_at = models.DateTimeField(auto_now=True)

class FactTrainingEnrollment(models.Model):
    source_id = models.PositiveBigIntegerField(unique=True)
    date = models.ForeignKey(DimDate, on_delete=models.PROTECT)
    business_unit = models.ForeignKey(DimBusinessUnit, null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=32)
    completed = models.BooleanField(default=False)
    certificate_issued = models.BooleanField(default=False)
    synced_at = models.DateTimeField(auto_now=True)
