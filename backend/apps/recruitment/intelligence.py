import hashlib
import re
from pathlib import Path

from django.db import transaction

from .choices import ApplicationDocumentType
from .models import Application, ApplicationMatch, CVAnalysis, Offer, TrainingRecommendation

SKILL_VOCABULARY = {
    "angular", "typescript", "javascript", "python", "django", "java", "spring", "sql",
    "postgresql", "docker", "kubernetes", "git", "linux", "power bi", "excel", "react",
    "node.js", "rest", "machine learning", "data analysis", "communication", "scrum",
}


def _extract_pdf(file_object) -> str:
    from pypdf import PdfReader
    file_object.seek(0)
    return "\n".join(page.extract_text() or "" for page in PdfReader(file_object))


def extract_cv(application: Application) -> CVAnalysis:
    document = application.documents.filter(document_type=ApplicationDocumentType.CV).order_by("-uploaded_at").first()
    if not document:
        raise ValueError("Aucun CV n’est associé à cette candidature.")
    with document.file.open("rb") as source:
        raw = source.read()
        source.seek(0)
        suffix = Path(document.original_name or document.file.name).suffix.lower()
        text = _extract_pdf(source) if suffix == ".pdf" else raw.decode("utf-8", errors="ignore")
    normalized = " ".join(text.split())
    if not normalized:
        raise ValueError("Le CV ne contient aucun texte exploitable.")
    lowered = normalized.casefold()
    skills = sorted(skill for skill in SKILL_VOCABULARY if skill in lowered)
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", normalized)))
    phones = sorted(set(re.findall(r"(?:\+?\d[\d .()-]{7,}\d)", normalized)))
    experience_lines = [line.strip() for line in text.splitlines() if re.search(r"\b(expérience|experience|stage|internship|emploi|work)\b", line, re.I)][:20]
    diploma_lines = [line.strip() for line in text.splitlines() if re.search(r"\b(dipl[oô]me|master|licence|bachelor|ingénieur|engineer|doctorat|phd)\b", line, re.I)][:20]
    analysis, _ = CVAnalysis.objects.update_or_create(application=application, defaults={
        "skills": skills, "experiences": experience_lines, "diplomas": diploma_lines,
        "contact_details": {"emails": emails, "phones": phones},
        "source_sha256": hashlib.sha256(raw).hexdigest(), "human_validated": False,
        "validated_by": None, "validated_at": None,
    })
    return analysis


@transaction.atomic
def match_application(application: Application) -> list[ApplicationMatch]:
    analysis = getattr(application, "cv_analysis", None) or extract_cv(application)
    candidate_skills = {skill.casefold() for skill in analysis.skills}
    results = []
    offers = Offer.objects.exclude(required_skills="")
    if application.offer_id:
        offers = offers.filter(pk=application.offer_id)
    for offer in offers:
        required = {item.strip().casefold() for item in re.split(r"[,;\n]", offer.required_skills) if item.strip()}
        matched = sorted(required & candidate_skills)
        missing = sorted(required - candidate_skills)
        score = round(100 * len(matched) / len(required), 2) if required else 0
        item, _ = ApplicationMatch.objects.update_or_create(application=application, offer=offer, defaults={
            "score": score, "matched_skills": matched, "missing_skills": missing,
            "explanation": f"{len(matched)} compétence(s) correspondante(s) sur {len(required)} requise(s).",
            "human_decision": "PENDING", "reviewed_by": None, "reviewed_at": None,
        })
        results.append(item)
    missing_all = {skill for item in results for skill in item.missing_skills}
    from apps.trainings.models import Training
    for training in Training.objects.all():
        searchable = f"{training.title} {training.description} {training.category} {training.objectives}".casefold()
        covered = sorted(skill for skill in missing_all if skill in searchable)
        if not covered:
            continue
        score = round(100 * len(covered) / len(missing_all), 2) if missing_all else 0
        TrainingRecommendation.objects.update_or_create(application=application, training=training, defaults={
            "score": score, "skill_gaps": covered,
            "explanation": f"Cette formation couvre {len(covered)} écart(s) de compétences détecté(s).",
            "human_decision": "PENDING",
        })
    return results
