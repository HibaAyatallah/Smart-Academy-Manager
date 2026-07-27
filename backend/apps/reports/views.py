import csv
from io import StringIO
from django.db.models import Count, Avg
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.projects.models import Project
from apps.recruitment.models import Application, InternProfile
from apps.trainings.models import SessionAttendance, Training, TrainingCertificate, TrainingEnrollment, TrainingSession

def grouped(qs, field): return [{"label":str(row[field] or "UNSPECIFIED"),"value":row["value"]} for row in qs.values(field).annotate(value=Count("id")).order_by(field)]
def dated(qs, field, start, end):
    if start: qs=qs.filter(**{f"{field}__date__gte":start})
    if end: qs=qs.filter(**{f"{field}__date__lte":end})
    return qs

def report_data(params):
    start,end,bu=params.get("date_from"),params.get("date_to"),params.get("business_unit")
    applications=dated(Application.objects.all(),"submitted_at",start,end); interns=dated(InternProfile.objects.all(),"created_at",start,end); projects=dated(Project.objects.all(),"created_at",start,end)
    trainings=dated(Training.objects.all(),"created_at",start,end); sessions=dated(TrainingSession.objects.all(),"created_at",start,end); enrollments=dated(TrainingEnrollment.objects.all(),"created_at",start,end)
    attendance=dated(SessionAttendance.objects.all(),"created_at",start,end); certificates=dated(TrainingCertificate.objects.all(),"issued_at",start,end); users=dated(User.objects.all(),"created_at",start,end); bus=BusinessUnit.objects.all()
    if bu:
        applications=applications.filter(offer__business_unit_id=bu); interns=interns.filter(business_unit_id=bu); projects=projects.filter(business_unit_id=bu); trainings=trainings.filter(business_unit_id=bu); sessions=sessions.filter(training__business_unit_id=bu); enrollments=enrollments.filter(training__business_unit_id=bu); attendance=attendance.filter(enrollment__training__business_unit_id=bu); certificates=certificates.filter(enrollment__training__business_unit_id=bu); users=users.filter(bu_memberships__business_unit_id=bu,bu_memberships__is_active=True).distinct(); bus=bus.filter(id=bu)
    return {"filters":{"date_from":start or "","date_to":end or "","business_unit":bu or ""},"cards":{"applications":applications.count(),"interns":interns.count(),"projects":projects.count(),"trainings":trainings.count(),"sessions":sessions.count(),"enrollments":enrollments.count(),"attendance_records":attendance.count(),"certificates":certificates.count(),"business_units":bus.count(),"users":users.count()},"series":{"recruitment":grouped(applications,"status"),"internships":grouped(interns,"current_status"),"projects":grouped(projects,"status"),"trainings":grouped(trainings,"status"),"sessions":grouped(sessions,"status"),"enrollments":grouped(enrollments,"status"),"attendance":grouped(attendance,"status"),"users":grouped(users,"role"),"business_units":[{"label":"ACTIVE","value":bus.filter(is_active=True).count()},{"label":"INACTIVE","value":bus.filter(is_active=False).count()}]},"kpis":{"average_project_progress":round(projects.aggregate(v=Avg("progress"))["v"] or 0,1),"attendance_validation_rate":round(100*attendance.filter(validated=True).count()/max(attendance.count(),1),1),"certificate_rate":round(100*certificates.count()/max(enrollments.count(),1),1),"active_memberships":BusinessUnitMembership.objects.filter(is_active=True,**({"business_unit_id":bu} if bu else {})).count()}}

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
        data=report_data(request.query_params); rows=[("section","label","value")]+[("cards",k,v) for k,v in data["cards"].items()]+[(section,item["label"],item["value"]) for section,items in data["series"].items() for item in items]+[("kpis",k,v) for k,v in data["kpis"].items()]
        if export_format=="csv":
            output=StringIO(); writer=csv.writer(output); writer.writerows(rows); response=HttpResponse(output.getvalue(),content_type="text/csv"); response["Content-Disposition"]='attachment; filename="smart-academy-report.csv"'; return response
        if export_format=="pdf":
            response=HttpResponse(pdf_bytes(["Smart Academy Manager report"]+[f"{a}: {b} = {c}" for a,b,c in rows[1:]]),content_type="application/pdf"); response["Content-Disposition"]='attachment; filename="smart-academy-report.pdf"'; return response
        return Response({"detail":"Unsupported format."},status=status.HTTP_400_BAD_REQUEST)
