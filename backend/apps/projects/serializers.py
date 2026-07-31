from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnitMembership
from apps.recruitment.models import InternProfile
from .models import Project, ProjectComment, ProjectDeliverable, ProjectDocument

User = get_user_model()


class ProjectDeliverableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDeliverable
        fields = ["id", "project", "title", "description", "due_date", "status", "created_by", "updated_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]

    def validate_due_date(self, value):
        from django.utils import timezone
        old_val = getattr(self.instance, "due_date", None) if self.instance else None
        if value and value != old_val and value < timezone.localdate():
            raise serializers.ValidationError("La date ne peut pas être antérieure à aujourd’hui.")
        return value


class ProjectCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = ProjectComment
        fields = ["id", "project", "author", "author_name", "author_email", "content", "created_at"]
        read_only_fields = ["id", "author", "author_name", "author_email", "created_at"]


class ProjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = ProjectDocument
        fields = ["id", "project", "file", "original_name", "uploaded_by", "uploaded_by_email", "uploaded_at"]
        read_only_fields = ["id", "original_name", "uploaded_by", "uploaded_by_email", "uploaded_at"]


class ProjectSerializer(serializers.ModelSerializer):
    business_unit_name = serializers.CharField(source="business_unit.name", read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.full_name", read_only=True)
    supervisor_email = serializers.EmailField(source="supervisor.email", read_only=True)
    assignee_ids = serializers.PrimaryKeyRelatedField(source="assignees", many=True, queryset=User.objects.all(), required=False)
    assignees = serializers.SerializerMethodField()
    deliverables = ProjectDeliverableSerializer(many=True, read_only=True)
    comments = ProjectCommentSerializer(many=True, read_only=True)
    documents = ProjectDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "title", "description", "business_unit", "business_unit_name", "supervisor", "supervisor_name", "supervisor_email", "assignee_ids", "assignees", "start_date", "end_date", "status", "progress", "deliverables", "comments", "documents", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "assignees", "created_by", "created_at", "updated_at"]

    def get_assignees(self, obj):
        return [{"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role} for user in obj.assignees.all()]

    def validate_progress(self, value):
        if value > 100:
            raise serializers.ValidationError("La progression doit être comprise entre 0 et 100.")
        return value

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
        if start and end and start > end:
            errors.setdefault("end_date", "La date de fin doit être postérieure ou égale à la date de début.")
        if errors:
            raise serializers.ValidationError(errors)
        supervisor = attrs.get("supervisor", getattr(self.instance, "supervisor", None))
        if supervisor and supervisor.role != UserRole.EMPLOYEE:
            raise serializers.ValidationError({"supervisor": "Le superviseur doit être un collaborateur."})
        business_unit = attrs.get("business_unit", getattr(self.instance, "business_unit", None))
        assignees = attrs.get("assignees")
        if assignees is not None:
            for user in assignees:
                if user.role not in {UserRole.EMPLOYEE, UserRole.INTERN}:
                    raise serializers.ValidationError({"assignee_ids": "Seuls les collaborateurs et stagiaires peuvent être affectés."})
                if user.role == UserRole.EMPLOYEE and not BusinessUnitMembership.objects.filter(user=user, business_unit=business_unit, is_active=True).exists():
                    raise serializers.ValidationError({"assignee_ids": f"{user.email} n'appartient pas à cette Business Unit."})
                if user.role == UserRole.INTERN and not InternProfile.objects.filter(user=user, business_unit=business_unit).exists():
                    raise serializers.ValidationError({"assignee_ids": f"Le stagiaire {user.email} n'est pas affecté à cette Business Unit."})
        return attrs

    def create(self, validated_data):
        assignees = validated_data.pop("assignees", [])
        project = super().create(validated_data)
        project.assignees.set(assignees)
        return project

    def update(self, instance, validated_data):
        assignees = validated_data.pop("assignees", None)
        instance = super().update(instance, validated_data)
        if assignees is not None:
            instance.assignees.set(assignees)
        return instance
