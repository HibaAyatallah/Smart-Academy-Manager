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

User = get_user_model()


# ---------------------------------------------------------------------------
# Serializers (HR-scoped — no sensitive management fields)
# ---------------------------------------------------------------------------

class HRInternProfileSerializer(serializers.ModelSerializer):
    """Intern personal and administrative data visible to HR."""
    full_name = serializers.CharField(read_only=True)
    business_units = serializers.SerializerMethodField()
    supervisor = serializers.SerializerMethodField()
    internship_dates = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "role",
            "is_active",
            "created_at",
            "business_units",
            "supervisor",
            "internship_dates",
        ]

    def get_business_units(self, obj):
        return list(
            BusinessUnit.objects.filter(
                memberships__user=obj, memberships__is_active=True
            ).distinct().values("id", "name", "code")
        )

    def get_supervisor(self, obj):
        """Return supervisor info if the intern has a supervised internship record.

        The Internship model will be created in Phase 4. For now we return None
        and this field will be populated once that model exists.
        """
        try:
            from apps.internships.models import Internship  # Phase 4
            internship = obj.internships.filter(
                status__in=["PLANNED", "ACTIVE"]
            ).select_related("supervisor").first()
            if internship and internship.supervisor:
                return {
                    "id": internship.supervisor.id,
                    "full_name": internship.supervisor.full_name,
                    "email": internship.supervisor.email,
                }
        except ImportError:
            pass
        return None

    def get_internship_dates(self, obj):
        """Return internship dates from the Internship model (Phase 4)."""
        try:
            from apps.internships.models import Internship  # Phase 4
            internship = obj.internships.filter(
                status__in=["PLANNED", "ACTIVE"]
            ).first()
            if internship:
                return {
                    "start_date": internship.start_date,
                    "end_date": internship.end_date,
                    "status": internship.status,
                }
        except ImportError:
            pass
        return None


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
        return (
            User.objects.filter(role=UserRole.INTERN, is_active=True)
            .order_by("last_name", "first_name")
        )


class HRInternDetailView(RetrieveAPIView):
    """
    GET /api/hr/interns/:id/

    Detail view for one intern. HR read-only.
    """
    permission_classes = [IsHROnly]
    serializer_class = HRInternProfileSerializer

    def get_queryset(self):
        return User.objects.filter(role=UserRole.INTERN)


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
