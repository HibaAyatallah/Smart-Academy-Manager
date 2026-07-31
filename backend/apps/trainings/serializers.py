from rest_framework import serializers
from .models import ClientProfile, Training, TrainingSession, TrainingEnrollment, EnrollmentHistory, SessionAttendance, AttendanceHistory, TrainingCertificate
from .choices import EnrollmentStatus, SessionStatus
from apps.accounts.choices import UserRole

class ClientProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ClientProfile
        fields = ["id", "company_name", "project_info", "email", "created_at"]
        read_only_fields = ["id", "created_at"]


class TrainingSessionSerializer(serializers.ModelSerializer):
    participant_count = serializers.IntegerField(read_only=True, default=0)
    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = TrainingSession
        fields = [
            "id", "training", "start_date", "end_date", "start_time", "end_time",
            "location", "online_link", "trainer", "maximum_participants",
            "status", "external_client", "participant_count", "remaining_capacity",
            "created_by", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "status", "created_by", "created_at", "updated_at"]

    def get_remaining_capacity(self, obj):
        if hasattr(obj, 'participant_count'):
            count = obj.participant_count
        else:
            count = obj.enrollments.filter(status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]).count()
        return max(0, obj.maximum_participants - count)
        
    def validate(self, attrs):
        from django.utils import timezone
        today = timezone.localdate()
        errors = {}
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        old_start = getattr(self.instance, "start_date", None) if self.instance else None
        old_end = getattr(self.instance, "end_date", None) if self.instance else None
        if "start_date" in attrs and start and start != old_start and start < today:
            errors["start_date"] = "La date ne peut pas être antérieure à aujourd’hui."
        if "end_date" in attrs and end and end != old_end and end < today:
            errors["end_date"] = "La date ne peut pas être antérieure à aujourd’hui."
        if start and end and end < start:
            errors.setdefault("end_date", "La date de fin doit être postérieure ou égale à la date de début.")
        if errors:
            raise serializers.ValidationError(errors)

        # Merge with existing instance data if it's an update
        instance = TrainingSession(**attrs) if not self.instance else self.instance
        for attr, value in attrs.items():
            setattr(instance, attr, value)
            
        try:
            instance.clean()
        except Exception as e:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(e)
            
        return attrs


class TrainingSerializer(serializers.ModelSerializer):
    # We might not want to embed all sessions, but it's useful. Let's make it optional or read_only.
    sessions = TrainingSessionSerializer(many=True, read_only=True)

    class Meta:
        model = Training
        fields = [
            "id", "title", "description", "training_type", "category",
            "objectives", "prerequisites", "duration", "delivery_mode", "level",
            "trainer", "business_unit", "external_client", "project_name",
            "associated_link", "status", "image",
            "sessions", "created_by", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "status", "created_by", "created_at", "updated_at"]


class ClientTrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = [
            "id", "start_date", "end_date", "start_time", "end_time",
            "location", "online_link", "status"
        ]


class ClientTrainingSerializer(serializers.ModelSerializer):
    sessions = ClientTrainingSessionSerializer(many=True, read_only=True)

    class Meta:
        model = Training
        fields = [
            "id", "title", "project_name", "associated_link", "sessions"
        ]


class EnrollmentHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)
    
    class Meta:
        model = EnrollmentHistory
        fields = ["id", "previous_status", "new_status", "changed_by_email", "comment", "timestamp"]


class TrainingEnrollmentSerializer(serializers.ModelSerializer):
    history = EnrollmentHistorySerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    training_title = serializers.CharField(source='training.title', read_only=True)
    user_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='training.project_name', read_only=True)
    business_unit = serializers.IntegerField(source='training.business_unit_id', read_only=True)
    session_start_date = serializers.DateField(source='session.start_date', read_only=True)
    session_end_date = serializers.DateField(source='session.end_date', read_only=True)
    present_days = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingEnrollment
        fields = [
            "id", "user", "user_email", "user_name", "training", "training_title",
            "project_name", "business_unit", "session", "session_start_date",
            "session_end_date", "present_days",
            "requested_at", "status", "manager_decision", "manager_comment",
            "manager_decided_by", "manager_decided_at", "super_admin_decision",
            "super_admin_comment", "super_admin_decided_by", "super_admin_decided_at",
            "final_status", "created_at", "updated_at", "history"
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_present_days(self, obj):
        return obj.attendances.filter(status__in=["PRESENT", "LATE"]).count()
        read_only_fields = [
            "requested_at", "status", "manager_decision", "manager_decided_by",
            "manager_decided_at", "super_admin_decision", "super_admin_decided_by",
            "super_admin_decided_at", "final_status", "created_at", "updated_at"
        ]


class TrainingEnrollmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingEnrollment
        fields = ["id", "training", "session", "status", "requested_at"]
        read_only_fields = ["id", "status", "requested_at"]
        
    def validate(self, attrs):
        user = self.context['request'].user
        session = attrs['session']
        
        # Must be same training
        if session.training != attrs['training']:
            raise serializers.ValidationError("La session ne correspond pas à la formation.")
            
        if user.role == UserRole.EMPLOYEE and not user.bu_memberships.filter(
            is_active=True,
            business_unit_id=attrs["training"].business_unit_id,
        ).exists():
            raise serializers.ValidationError(
                "Vous ne pouvez pas accéder aux formations d'une autre Business Unit."
            )

        if session.status in [SessionStatus.COMPLETED, SessionStatus.CANCELLED, SessionStatus.FULL]:
            raise serializers.ValidationError("La session n'est pas disponible pour l'inscription.")
            
        # Check duplicates
        if TrainingEnrollment.objects.filter(
            user=user, session=session
        ).exclude(
            status__in=[EnrollmentStatus.REJECTED_BY_MANAGER, EnrollmentStatus.REJECTED_BY_SUPER_ADMIN, EnrollmentStatus.CANCELLED]
        ).exists():
            raise serializers.ValidationError("Vous êtes déjà inscrit(e) ou en attente pour cette session.")
            
        # Capacity check is done at approval time, but can also warn here if strictly wanted.
        return attrs


class ManagerDecisionSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    comment = serializers.CharField(required=False, allow_blank=True)


class SuperAdminDecisionSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    comment = serializers.CharField(required=False, allow_blank=True)


class DirectEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingEnrollment
        fields = ["user", "training", "session"]

    def validate(self, attrs):
        session = attrs['session']
        if session.training != attrs['training']:
            raise serializers.ValidationError("La session ne correspond pas à la formation.")
            
        if TrainingEnrollment.objects.filter(
            user=attrs['user'], session=session
        ).exclude(
            status__in=[EnrollmentStatus.REJECTED_BY_MANAGER, EnrollmentStatus.REJECTED_BY_SUPER_ADMIN, EnrollmentStatus.CANCELLED]
        ).exists():
            raise serializers.ValidationError("L'utilisateur a déjà une inscription active pour cette session.")
            
        # Check capacity
        participant_count = session.enrollments.filter(status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]).count()
        if participant_count >= session.maximum_participants:
            raise serializers.ValidationError("Capacité maximale atteinte pour cette session.")
            
        return attrs


class AttendanceHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = AttendanceHistory
        fields = ["id", "status", "validated", "changed_by_email", "note", "timestamp"]


class SessionAttendanceSerializer(serializers.ModelSerializer):
    history = AttendanceHistorySerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="enrollment.user.email", read_only=True)
    training_title = serializers.CharField(source="enrollment.training.title", read_only=True)
    session = serializers.IntegerField(source="enrollment.session_id", read_only=True)
    user_name = serializers.SerializerMethodField()
    validated_by_email = serializers.EmailField(source="validated_by.email", read_only=True)

    class Meta:
        model = SessionAttendance
        fields = ["id", "enrollment", "session", "user_email", "user_name", "training_title", "date", "status", "note", "validated", "recorded_by", "validated_by", "validated_by_email", "validated_at", "created_at", "updated_at", "history"]
        read_only_fields = ["validated", "recorded_by", "validated_by", "validated_at", "created_at", "updated_at"]

    def validate_enrollment(self, enrollment):
        if enrollment.status not in [EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]:
            raise serializers.ValidationError("Attendance is limited to enrolled participants.")
        return enrollment

    def get_user_name(self, obj):
        return obj.enrollment.user.get_full_name() or obj.enrollment.user.email

    def validate(self, attrs):
        attrs = super().validate(attrs)
        enrollment = attrs.get("enrollment", getattr(self.instance, "enrollment", None))
        attendance_date = attrs.get("date", getattr(self.instance, "date", None))
        if enrollment and attendance_date:
            session = enrollment.session
            if attendance_date < session.start_date or attendance_date > session.end_date:
                raise serializers.ValidationError({"date": "La date doit être comprise dans la période de la formation."})
        return attrs


class TrainingCertificateSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="enrollment.user.email", read_only=True)
    training_title = serializers.CharField(source="enrollment.training.title", read_only=True)
    session = serializers.IntegerField(source="enrollment.session_id", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = TrainingCertificate
        fields = ["id", "enrollment", "user_email", "training_title", "session", "certificate_number", "issued_at", "issued_by", "download_url"]
        read_only_fields = fields

    def get_download_url(self, obj):
        return f"/api/certificates/{obj.pk}/download/"
