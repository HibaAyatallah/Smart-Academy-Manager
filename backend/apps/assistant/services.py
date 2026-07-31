from dataclasses import dataclass
from django.conf import settings
from django.utils.module_loading import import_string
from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.recruitment.models import Application, InternProfile, InternDocumentRequirement
from apps.trainings.models import Training, TrainingEnrollment, SessionAttendance

@dataclass(frozen=True)
class SafeContext: facts:list[str]; suggestions:list[str]

def build_safe_context(user):
    facts=[];suggestions=[]
    if user.role==UserRole.CANDIDATE:
        apps=Application.objects.filter(candidate_profile__user=user).select_related("offer")
        facts += [f"Application {a.pk}: {a.offer.title if a.offer else a.get_application_type_display()} — {a.get_status_display()} — {a.submitted_at.date()}" for a in apps]
        suggestions=["Quel est le statut de ma candidature ?","Quelle offre concerne ma candidature ?"]
    elif user.role==UserRole.INTERN:
        intern=InternProfile.objects.filter(user=user).select_related("business_unit","supervisor").first()
        if intern:
            facts=[f"Internship: {intern.subject_title}; dates {intern.internship_start} to {intern.internship_end}; status {intern.get_current_status_display()}; BU {intern.business_unit.name if intern.business_unit else '-'}; supervisor {intern.supervisor.full_name if intern.supervisor else '-'}"]
            submitted=set(intern.documents.values_list("requirement_id",flat=True));missing=InternDocumentRequirement.objects.filter(is_active=True,is_required=True).exclude(id__in=submitted).values_list("name",flat=True)
            facts.append("Missing documents: "+(", ".join(missing) or "none"))
        suggestions=["Quelle est ma période de stage ?","Qui est mon encadrant ?","Quels documents me manquent ?"]
    elif user.role in [UserRole.EMPLOYEE,UserRole.TRAINER_TUTOR]:
        enrollments=TrainingEnrollment.objects.filter(user=user).select_related("training")
        facts += [f"Training: {e.training.title}; status {e.final_status}" for e in enrollments]
        facts.append(f"Attendance: present {SessionAttendance.objects.filter(enrollment__user=user,status='PRESENT').count()}; total {SessionAttendance.objects.filter(enrollment__user=user).count()}")
        suggestions=["Quelles sont mes formations ?","Quel est le statut de mes inscriptions ?"]
    elif user.role==UserRole.BU_MANAGER:
        units=BusinessUnit.objects.filter(manager=user);facts.append(f"BU members: {BusinessUnitMembership.objects.filter(business_unit__in=units,is_active=True).count()}");facts.append(f"BU needs: {BusinessUnitNeed.objects.filter(business_unit__in=units).count()}");facts.append(f"BU interns: {InternProfile.objects.filter(business_unit__in=units).count()}");facts.append(f"BU trainings: {Training.objects.filter(business_unit__in=units).count()}");suggestions=["Combien de collaborateurs dans ma BU ?","Quels sont les besoins de ma BU ?","Combien de formations dans ma BU ?"]
    elif user.role in [UserRole.HR,UserRole.SUPER_ADMIN]:
        facts=[f"Applications: {Application.objects.count()}",f"Interns: {InternProfile.objects.count()}",f"Business units: {BusinessUnit.objects.count()}"]
        suggestions=["Combien de candidatures ?","Combien de stagiaires ?"]
    else: suggestions=["Quelles informations sont disponibles ?"]
    return SafeContext(facts,suggestions)

class ReadOnlyAssistantProvider:
    def answer(self,question,context,language):
        if not context.facts:return {"fr":"Je ne dispose pas de cette information.","en":"I do not have that information.","ar":"لا أملك هذه المعلومة."}[language]
        normalized=question.casefold()
        topic_words={
            "application":["candidature","application","offre","status","statut"],"internship":["stage","internship","période","period","encadrant","supervisor","document"],
            "training":["formation","training","inscription","enrollment"],"attendance":["présence","presence","attendance"],"bu":["bu","business unit","collaborateur","employee","besoin","need","stagiaire","intern","formation","training"],
            "global":["combien","how many","statistique","statistics","candidature","application","stagiaire","intern","business unit"]}
        prefixes={"application":["Application"],"internship":["Internship","Missing documents"],"training":["Training"],"attendance":["Attendance"],"bu":["BU "],"global":["Applications","Interns","Business units"]}
        selected=[]
        for topic,words in topic_words.items():
            if any(word in normalized for word in words):selected.extend(f for f in context.facts if any(f.startswith(prefix) for prefix in prefixes[topic]))
        selected=list(dict.fromkeys(selected))
        if not selected:return {"fr":"Je ne dispose pas de cette information.","en":"I do not have that information.","ar":"لا أملك هذه المعلومة."}[language]
        intro={"fr":"Voici les informations auxquelles vous avez accès :","en":"Here is the information you are allowed to access:","ar":"إليك المعلومات التي يسمح لك بالوصول إليها:"}[language]
        return intro+"\n"+"\n".join(f"• {fact}" for fact in selected)

def get_provider():
    provider_class=import_string(settings.AI_ASSISTANT_PROVIDER)
    return provider_class()
