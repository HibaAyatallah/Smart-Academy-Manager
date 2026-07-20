from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.business_units.models import BusinessUnit
from .choices import TrainingType, DeliveryMode, TrainingStatus, SessionStatus, EnrollmentStatus


class ClientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_profile"
    )
    company_name = models.CharField(max_length=255)
    project_info = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.company_name} ({self.user.email})"


class Training(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    training_type = models.CharField(max_length=50, choices=TrainingType.choices)
    category = models.CharField(max_length=100)
    objectives = models.TextField()
    prerequisites = models.TextField(blank=True)
    duration = models.PositiveIntegerField(help_text="Durée en heures")
    delivery_mode = models.CharField(max_length=50, choices=DeliveryMode.choices)
    level = models.CharField(max_length=50)
    
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_trainings"
    )
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restricted_trainings"
    )
    external_client = models.ForeignKey(
        ClientProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reserved_trainings"
    )
    project_name = models.CharField(max_length=255, blank=True)
    
    associated_link = models.URLField(blank=True)
    moodle_course_id = models.CharField(max_length=100, blank=True)
    moodle_link = models.URLField(blank=True)
    
    status = models.CharField(
        max_length=50,
        choices=TrainingStatus.choices,
        default=TrainingStatus.DRAFT
    )
    image = models.FileField(upload_to="trainings/", null=True, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_trainings"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class TrainingSession(models.Model):
    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="sessions"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    location = models.CharField(max_length=255, blank=True)
    online_link = models.URLField(blank=True)
    
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_sessions"
    )
    maximum_participants = models.PositiveIntegerField()
    
    status = models.CharField(
        max_length=50,
        choices=SessionStatus.choices,
        default=SessionStatus.PLANNED
    )
    external_client = models.ForeignKey(
        ClientProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_sessions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.training.title} - {self.start_date}"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("La date de début ne peut pas être après la date de fin.")
        
        if self.maximum_participants is not None and self.maximum_participants <= 0:
            raise ValidationError("Le nombre maximum de participants doit être supérieur à zéro.")
        
        if self.training_id:
            delivery_mode = self.training.delivery_mode
            if delivery_mode in [DeliveryMode.REMOTE, DeliveryMode.HYBRID, DeliveryMode.E_LEARNING]:
                if not self.online_link:
                    raise ValidationError("Un lien en ligne est requis pour ce mode de formation.")
            if delivery_mode in [DeliveryMode.ON_SITE, DeliveryMode.HYBRID]:
                if not self.location:
                    raise ValidationError("Un lieu est requis pour ce mode de formation.")


class TrainingEnrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="training_enrollments"
    )
    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING_MANAGER
    )
    manager_decision = models.CharField(
        max_length=50, blank=True, choices=EnrollmentStatus.choices
    )
    manager_comment = models.TextField(blank=True)
    manager_decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_enrollments"
    )
    manager_decided_at = models.DateTimeField(null=True, blank=True)
    
    super_admin_decision = models.CharField(
        max_length=50, blank=True, choices=EnrollmentStatus.choices
    )
    super_admin_comment = models.TextField(blank=True)
    super_admin_decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_managed_enrollments"
    )
    super_admin_decided_at = models.DateTimeField(null=True, blank=True)
    
    final_status = models.CharField(
        max_length=50,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING_MANAGER
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'session'],
                name='unique_active_enrollment',
                condition=~models.Q(status__in=[
                    EnrollmentStatus.REJECTED_BY_MANAGER, 
                    EnrollmentStatus.REJECTED_BY_SUPER_ADMIN, 
                    EnrollmentStatus.CANCELLED
                ])
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.session}"


class EnrollmentHistory(models.Model):
    enrollment = models.ForeignKey(
        TrainingEnrollment,
        on_delete=models.CASCADE,
        related_name="history"
    )
    previous_status = models.CharField(max_length=50, choices=EnrollmentStatus.choices, blank=True)
    new_status = models.CharField(max_length=50, choices=EnrollmentStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.enrollment.id}: {self.previous_status} -> {self.new_status}"
