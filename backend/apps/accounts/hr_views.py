"""HR-specific read-only API views.

HR has a restricted read-only scope:
  - Accepted interns: personal and administrative information.
  - Collaborators: grouped by Business Unit.

HR must NOT access user management, applications, BUs, offers,
conversions, enrollments, certificates, or audit logs.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.choices import UserRole
from apps.accounts.permissions import IsHROnly
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.recruitment.models import InternProfile

User = get_user_model()


# ---------------------------------------------------------------------------
# Serializers (HR-scoped — no sensitive management fields)
# ---------------------------------------------------------------------------

class HRInternProfileSerializer(serializers.ModelSerializer):
    """Intern personal and administrative data visible to HR."""
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    business_unit = serializers.SerializerMethodField()
    supervisor = serializers.SerializerMethodField()
    document_submission_status = serializers.SerializerMethodField()

    class Meta:
        model = InternProfile
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "school",
            "specialization",
            "internship_type",
            "paid",
            "internship_start",
            "internship_end",
            "business_unit",
            "supervisor",
            "subject_title",
            "document_submission_status",
        ]

    def get_business_unit(self, obj):
        if not obj.business_unit:
            return None
        return {"id": obj.business_unit_id, "name": obj.business_unit.name, "code": obj.business_unit.code}

    def get_supervisor(self, obj):
        if not obj.supervisor:
            return None
        return {"id": obj.supervisor_id, "full_name": obj.supervisor.full_name, "email": obj.supervisor.email}

    def get_document_submission_status(self, obj):
        documents = list(obj.documents.all())
        return {
            "submitted_count": len(documents),
            "validated_count": sum(1 for document in documents if document.is_validated),
            "has_documents": bool(documents),
            "all_validated": bool(documents) and all(document.is_validated for document in documents),
        }


class HRCollaboratorSerializer(serializers.ModelSerializer):
    """Collaborator data visible to HR (read-only)."""
    full_name = serializers.CharField(read_only=True)
    position = serializers.SerializerMethodField()
    joined_at = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "is_active",
            "created_at",
            "position",
            "joined_at",
        ]

    def _get_membership(self, obj):
        bu = self.context.get("current_bu")
        if bu:
            return BusinessUnitMembership.objects.filter(
                user=obj, business_unit=bu, is_active=True
            ).first()
        return None

    def get_position(self, obj):
        m = self._get_membership(obj)
        return m.position if m else ""

    def get_joined_at(self, obj):
        m = self._get_membership(obj)
        return m.joined_at if m else None


class HRBUGroupSerializer(serializers.Serializer):
    """A Business Unit with its list of active collaborators (HR view)."""
    bu_id = serializers.IntegerField()
    bu_name = serializers.CharField()
    bu_code = serializers.CharField()
    manager_name = serializers.CharField()
    members = HRCollaboratorSerializer(many=True)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class HRInternListView(ListAPIView):
    """
    GET /api/hr/interns/

    Lists all users with role=INTERN (accepted interns).
    HR read-only. Super Admin should use /api/users/?role=INTERN instead.
    """
    permission_classes = [IsHROnly]
    serializer_class = HRInternProfileSerializer

    def get_queryset(self):
        return InternProfile.objects.filter(
            user__role=UserRole.INTERN,
            user__is_active=True,
        ).select_related("user", "business_unit", "supervisor").prefetch_related("documents").order_by("user__last_name", "user__first_name")


class HRInternDetailView(RetrieveAPIView):
    """
    GET /api/hr/interns/:id/

    Detail view for one intern. HR read-only.
    """
    permission_classes = [IsHROnly]
    serializer_class = HRInternProfileSerializer

    def get_queryset(self):
        return InternProfile.objects.filter(
            user__role=UserRole.INTERN,
            user__is_active=True,
        ).select_related("user", "business_unit", "supervisor").prefetch_related("documents")


class HRCollaboratorsByBUView(APIView):
    """
    GET /api/hr/collaborators/

    Returns all active collaborators (EMPLOYEE role) grouped by Business Unit.

    Response shape:
    [
      {
        "bu_id": 1,
        "bu_name": "Data",
        "bu_code": "DATA",
        "manager_name": "Alice Martin",
        "members": [
          { "id": 5, "full_name": "Bob Dupont", "email": "...", ... }
        ]
      },
      ...
    ]

    Collaborators who are not assigned to any active BU appear in a
    separate "Sans Business Unit" group.
    """
    permission_classes = [IsHROnly]

    def get(self, request):
        groups = []

        bus = BusinessUnit.objects.filter(is_active=True).select_related("manager").order_by("name")
        for bu in bus:
            memberships = BusinessUnitMembership.objects.filter(
                business_unit=bu, is_active=True
            ).select_related("user").order_by("user__last_name", "user__first_name")
            members_data = []
            for m in memberships:
                if m.user.role == UserRole.EMPLOYEE:
                    serializer = HRCollaboratorSerializer(
                        m.user, context={"request": request, "current_bu": bu}
                    )
                    members_data.append(serializer.data)

            if members_data:
                groups.append({
                    "bu_id": bu.id,
                    "bu_name": bu.name,
                    "bu_code": bu.code,
                    "manager_name": bu.manager.full_name if bu.manager else "",
                    "members": members_data,
                })

        # Collaborators without any active BU membership
        unassigned = User.objects.filter(
            role=UserRole.EMPLOYEE,
            is_active=True,
        ).exclude(
            bu_memberships__is_active=True
        ).order_by("last_name", "first_name")

        if unassigned.exists():
            members_data = []
            for user in unassigned:
                serializer = HRCollaboratorSerializer(user, context={"request": request})
                members_data.append(serializer.data)
            groups.append({
                "bu_id": None,
                "bu_name": "Sans Business Unit",
                "bu_code": "",
                "manager_name": "",
                "members": members_data,
            })

        return Response(groups)
