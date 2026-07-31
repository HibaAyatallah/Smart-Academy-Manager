import csv
from io import StringIO
from datetime import datetime, timedelta
from django.db.models import Count, Avg, F
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.projects.models import Project
from apps.recruitment.models import Application, InternProfile
from apps.trainings.models import SessionAttendance, Training, TrainingCertificate, TrainingEnrollment, TrainingSession
from apps.notifications.models import AuditLog
from apps.accounts.permissions import IsHROnly

def grouped(qs, field): 
    return [{"label":str(row[field] or "UNSPECIFIED"),"value":row["value"]} for row in qs.values(field).annotate(value=Count("id")).order_by(field)]

def dated(qs, field, start, end):
    if start: qs=qs.filter(**{f"{field}__date__gte":start})
    if end: qs=qs.filter(**{f"{field}__date__lte":end})
    return qs

def report_data(params):
    start,end,bu=params.get("date_from"),params.get("date_to"),params.get("business_unit")
    
    applications = dated(Application.objects.all(), "submitted_at", start, end)
    interns = dated(InternProfile.objects.all(), "created_at", start, end)
    projects = dated(Project.objects.all(), "created_at", start, end)
    trainings = dated(Training.objects.all(), "created_at", start, end)
    sessions = dated(TrainingSession.objects.all(), "created_at", start, end)
    enrollments = dated(TrainingEnrollment.objects.all(), "created_at", start, end)
    attendance = dated(SessionAttendance.objects.all(), "created_at", start, end)
    certificates = dated(TrainingCertificate.objects.all(), "issued_at", start, end)
    users = dated(User.objects.all(), "created_at", start, end)
    bus = BusinessUnit.objects.all()
    needs = dated(BusinessUnitNeed.objects.all(), "created_at", start, end)
    
    if bu:
        applications = applications.filter(offer__business_unit_id=bu)
        interns = interns.filter(business_unit_id=bu)
        projects = projects.filter(business_unit_id=bu)
        trainings = trainings.filter(business_unit_id=bu)
        sessions = sessions.filter(training__business_unit_id=bu)
        enrollments = enrollments.filter(training__business_unit_id=bu)
        attendance = attendance.filter(enrollment__training__business_unit_id=bu)
        certificates = certificates.filter(enrollment__training__business_unit_id=bu)
        users = users.filter(bu_memberships__business_unit_id=bu, bu_memberships__is_active=True).distinct()
        bus = bus.filter(id=bu)
        needs = needs.filter(business_unit_id=bu)

    active_interns = interns.filter(user__is_active=True, user__role=UserRole.INTERN)
    active_collaborators = users.filter(is_active=True, role=UserRole.EMPLOYEE)
    
    recent_activities = [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.target_type,
            "actor_name": f"{log.actor.first_name} {log.actor.last_name}" if log.actor else log.actor_email,
            "created_at": log.created_at
        }
        for log in AuditLog.objects.select_related("actor").order_by("-created_at")[:10]
    ]

    twelve_months_ago = datetime.now().date() - timedelta(days=365)
    monthly_apps_qs = applications.filter(submitted_at__date__gte=twelve_months_ago) \
        .annotate(month=TruncMonth("submitted_at")) \
        .values("month") \
        .annotate(count=Count("id")) \
        .order_by("month")

    monthly_applications = [
        {"label": row["month"].strftime("%Y-%m"), "value": row["count"]}
        for row in monthly_apps_qs if row["month"]
    ]

    recent_apps_qs = applications.select_related("candidate_profile", "candidate_profile__user", "offer", "offer__business_unit").order_by("-submitted_at")[:10]
    recent_applications = [
        {
            "id": app.id,
            "candidate_name": app.candidate_profile.user.full_name if (hasattr(app, 'candidate_profile') and app.candidate_profile and hasattr(app.candidate_profile, 'user') and app.candidate_profile.user) else "UNSPECIFIED",
            "offer_title": app.offer.title if app.offer else "UNSPECIFIED",
            "business_unit": app.offer.business_unit.name if app.offer and app.offer.business_unit else "UNSPECIFIED",
            "submitted_at": app.submitted_at,
            "status": app.status
        }
        for app in recent_apps_qs
    ]

    apps_bu_status_qs = applications.values("offer__business_unit__name", "status").annotate(count=Count("id"))
    applications_by_bu_status = [
        {
            "business_unit": row["offer__business_unit__name"] or "UNSPECIFIED",
            "status": row["status"],
            "count": row["count"]
        }
        for row in apps_bu_status_qs
    ]

    interns_bu = active_interns.values("business_unit__name").annotate(count=Count("id"))
    collabs_bu = BusinessUnitMembership.objects.filter(is_active=True, user__in=active_collaborators).values("business_unit__name").annotate(count=Count("id"))
    workforce_dict = {}
    for row in interns_bu:
        bu_name = row["business_unit__name"] or "UNSPECIFIED"
        if bu_name not in workforce_dict:
            workforce_dict[bu_name] = {"business_unit": bu_name, "interns": 0, "collaborators": 0}
        workforce_dict[bu_name]["interns"] = row["count"]
    for row in collabs_bu:
        bu_name = row["business_unit__name"] or "UNSPECIFIED"
        if bu_name not in workforce_dict:
            workforce_dict[bu_name] = {"business_unit": bu_name, "interns": 0, "collaborators": 0}
        workforce_dict[bu_name]["collaborators"] = row["count"]
    workforce_by_bu = list(workforce_dict.values())

    return {
        "filters": {"date_from": start or "", "date_to": end or "", "business_unit": bu or ""},
        "cards": {
            "applications": applications.count(),
            "interns": interns.count(),
            "projects": projects.count(),
            "trainings": trainings.count(),
            "sessions": sessions.count(),
            "enrollments": enrollments.count(),
            "attendance_records": attendance.count(),
            "certificates": certificates.count(),
            "business_units": bus.count(),
            "users": users.count(),
            "active_interns": active_interns.count(),
            "active_collaborators": active_collaborators.count(),
            "open_bu_needs": needs.filter(status__in=["SUBMITTED", "ACCEPTED"]).count(),
        },
        "series": {
            "recruitment": grouped(applications, "status"),
            "internships": grouped(interns, "current_status"),
            "projects": grouped(projects, "status"),
            "trainings": grouped(trainings, "status"),
            "sessions": grouped(sessions, "status"),
            "enrollments": grouped(enrollments, "status"),
            "attendance": grouped(attendance, "status"),
            "users": grouped(users, "role"),
            "business_units": [
                {"label": "ACTIVE", "value": bus.filter(is_active=True).count()},
                {"label": "INACTIVE", "value": bus.filter(is_active=False).count()}
            ],
            "candidates_by_bu": grouped(applications, "offer__business_unit__name"),
            "monthly_applications": monthly_applications,
            "applications_by_bu_status": applications_by_bu_status,
            "workforce_by_bu": workforce_by_bu,
        },
        "recent_activities": recent_activities,
        "recent_applications": recent_applications,
        "kpis": {
            "average_project_progress": round(projects.aggregate(v=Avg("progress"))["v"] or 0, 1),
            "attendance_validation_rate": round(100 * attendance.filter(validated=True).count() / max(attendance.count(), 1), 1),
            "certificate_rate": round(100 * certificates.count() / max(enrollments.count(), 1), 1),
            "active_memberships": BusinessUnitMembership.objects.filter(is_active=True, **({"business_unit_id": bu} if bu else {})).count()
        }
    }

def pdf_bytes(lines):
    content="BT /F1 10 Tf 40 800 Td "+" ".join(f"({line.replace('(','').replace(')','')}) Tj 0 -16 Td" for line in lines)+" ET"; stream=content.encode("latin-1","replace")
    objects=[b"<< /Type /Catalog /Pages 2 0 R >>",b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",f"<< /Length {len(stream)} >> stream\n".encode()+stream+b"\nendstream"]
    pdf=bytearray(b"%PDF-1.4\n"); offsets=[]
    for i,obj in enumerate(objects,1): offsets.append(len(pdf)); pdf.extend(f"{i} 0 obj\n".encode()+obj+b"\nendobj\n")
    xref=len(pdf); pdf.extend(f"xref\n0 6\n0000000000 65535 f \n".encode()); [pdf.extend(f"{o:010d} 00000 n \n".encode()) for o in offsets]; pdf.extend(f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()); return bytes(pdf)

class ReportView(APIView):
    def initial(self,request,*args,**kwargs):
        super().initial(request,*args,**kwargs)
        if request.user.role != UserRole.SUPER_ADMIN: raise PermissionDenied("Access denied.")
    def get(self,request): return Response(report_data(request.query_params))

class ReportExportView(ReportView):
    def get(self,request,export_format):
        data=report_data(request.query_params); rows=[("section","label","value")]+[("cards",k,v) for k,v in data["cards"].items()]+[(section,item.get("label", str(item)),item.get("value", "")) for section,items in data.get("series", {}).items() for item in items]+[("kpis",k,v) for k,v in data["kpis"].items()]
        if export_format=="csv":
            output=StringIO(); writer=csv.writer(output); writer.writerows(rows); response=HttpResponse(output.getvalue(),content_type="text/csv"); response["Content-Disposition"]='attachment; filename="smart-academy-report.csv"'; return response
        if export_format=="pdf":
            response=HttpResponse(pdf_bytes(["Smart Academy Manager report"]+[f"{a}: {b} = {c}" for a,b,c in rows[1:]]),content_type="application/pdf"); response["Content-Disposition"]='attachment; filename="smart-academy-report.pdf"'; return response
        return Response({"detail":"Unsupported format."},status=status.HTTP_400_BAD_REQUEST)

class HRDashboardView(APIView):
    permission_classes = [IsHROnly]

    def get(self, request):
        active_interns_qs = InternProfile.objects.filter(user__role=UserRole.INTERN, user__is_active=True).prefetch_related("documents")
        active_interns = active_interns_qs.count()

        interns_by_school = grouped(active_interns_qs, "school")
        interns_by_bu = grouped(active_interns_qs, "business_unit__name")
        
        paid_interns = active_interns_qs.filter(paid=True).count()
        unpaid_interns = active_interns_qs.filter(paid=False).count()

        missing_documents_count = 0
        for intern in active_interns_qs:
            docs = list(intern.documents.all())
            has_docs = bool(docs)
            all_validated = has_docs and all(d.is_validated for d in docs)
            if not has_docs or not all_validated:
                missing_documents_count += 1

        active_collaborators = User.objects.filter(role=UserRole.EMPLOYEE, is_active=True)
        collaborators_by_bu = grouped(
            BusinessUnitMembership.objects.filter(user__in=active_collaborators, is_active=True), 
            "business_unit__name"
        )
        
        today = datetime.now().date()
        upcoming_starts = active_interns_qs.filter(internship_start__gte=today).order_by("internship_start")[:5]
        upcoming_ends = active_interns_qs.filter(internship_end__gte=today).order_by("internship_end")[:5]

        internship_timeline = {
            "starts": [
                {
                    "name": intern.user.full_name,
                    "date": intern.internship_start,
                    "bu": intern.business_unit.name if intern.business_unit else "UNSPECIFIED"
                } for intern in upcoming_starts if intern.internship_start
            ],
            "ends": [
                {
                    "name": intern.user.full_name,
                    "date": intern.internship_end,
                    "bu": intern.business_unit.name if intern.business_unit else "UNSPECIFIED"
                } for intern in upcoming_ends if intern.internship_end
            ]
        }

        trainings_overview = {
            "active_trainings": Training.objects.filter(status__in=["PLANNED", "ONGOING"]).count(),
            "upcoming_sessions": TrainingSession.objects.filter(status="PLANNED", start_date__gte=today).count(),
            "ongoing_sessions": TrainingSession.objects.filter(status="ONGOING").count()
        }

        return Response({
            "active_interns": active_interns,
            "interns_by_school": interns_by_school,
            "interns_by_bu": interns_by_bu,
            "paid_interns": paid_interns,
            "unpaid_interns": unpaid_interns,
            "missing_documents": missing_documents_count,
            "collaborators_by_bu": collaborators_by_bu,
            "internship_timeline": internship_timeline,
            "trainings_overview": trainings_overview
        })
