"""Idempotent orchestration for CV extraction and application matching."""

from dataclasses import asdict, dataclass
import logging

from django.db.models import QuerySet

from .choices import ApplicationDocumentType
from .intelligence import (
    CVExtractionError,
    EXTRACTOR_VERSION,
    cv_document_sha256,
    extract_cv,
    match_application,
    match_is_stale,
)
from .models import Application, ApplicationMatch, CVAnalysis, Offer

logger = logging.getLogger(__name__)


NO_CV_ERROR = "Aucun CV n’est associé à cette candidature."


@dataclass
class ApplicationAnalysisResult:
    application_id: int
    status: str
    analysis_created: bool = False
    analysis_updated: bool = False
    matching_created: bool = False
    matching_updated: bool = False
    error: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _latest_cv(application: Application):
    return application.documents.filter(
        document_type=ApplicationDocumentType.CV,
    ).order_by("-uploaded_at", "-id").first()


def _current_analysis(application: Application):
    return CVAnalysis.objects.filter(application=application).first()


def analysis_is_stale(application: Application, analysis: CVAnalysis | None = None) -> bool:
    """Validate the extraction cache against content and extractor version."""
    analysis = analysis or _current_analysis(application)
    latest_cv = _latest_cv(application)
    if analysis is None:
        return False
    if latest_cv is None:
        return True
    if analysis.extractor_version != EXTRACTOR_VERSION:
        return True
    try:
        return analysis.source_sha256 != cv_document_sha256(latest_cv)
    except (OSError, ValueError):
        return True


def process_application_analysis(
    application: Application,
    *,
    force_analysis: bool = False,
    force_matching: bool = False,
    include_recommendations: bool = False,
) -> ApplicationAnalysisResult:
    """Create only the missing/stale derived data for one application.

    CVs, applications and human corrections are never deleted. Existing current
    analyses and matches are reused unless a caller explicitly requests a refresh
    or a newer CV document makes the analysis stale.
    """
    result = ApplicationAnalysisResult(application_id=application.pk, status="ignored")
    latest_cv = _latest_cv(application)
    if latest_cv is None:
        result.status = "no_cv"
        result.error = NO_CV_ERROR
        return result

    analysis = _current_analysis(application)
    stale_analysis = analysis_is_stale(application, analysis)
    should_extract = analysis is None or force_analysis or stale_analysis

    if analysis is not None and analysis.human_validated and stale_analysis and not force_analysis:
        result.status = "stale_human_validated"
        return result

    if should_extract:
        analysis_existed = analysis is not None
        try:
            analysis = extract_cv(application, force=force_analysis or stale_analysis)
        except (CVExtractionError, ValueError, OSError) as exc:
            result.status = "error"
            result.error = str(exc)
            logger.warning(
                "CV analysis failed application_id=%s error_type=%s",
                application.pk,
                exc.__class__.__name__,
            )
            return result
        result.analysis_created = not analysis_existed
        result.analysis_updated = analysis_existed

    if application.offer_id is None and not include_recommendations:
        result.status = "analyzed_without_offer" if should_extract else "ignored"
        return result

    existing_match = ApplicationMatch.objects.filter(
        application=application,
        offer_id=application.offer_id,
    ).first()
    should_match = (
        existing_match is None
        or force_matching
        or should_extract
        or match_is_stale(existing_match, application=application, offer=application.offer, analysis=analysis)
    )
    if should_match:
        try:
            matches = match_application(
                application,
                include_recommendations=include_recommendations,
            )
        except (CVExtractionError, ValueError, IndexError) as exc:
            result.status = "error"
            result.error = str(exc)
            logger.warning(
                "Application matching failed application_id=%s error_type=%s",
                application.pk,
                exc.__class__.__name__,
            )
            return result
        if not matches:
            result.status = "error"
            result.error = "Aucune offre disponible pour calculer le matching."
            return result
        result.matching_created = existing_match is None
        result.matching_updated = existing_match is not None
    elif include_recommendations:
        from .intelligence import update_training_recommendations
        update_training_recommendations(application, [existing_match])

    if result.analysis_created or result.analysis_updated or result.matching_created or result.matching_updated:
        result.status = "processed"
    else:
        result.status = "already_complete"
    return result


def analyze_application_batch(
    queryset: QuerySet | None = None,
    *,
    force_analysis: bool = False,
    force_matching: bool = False,
) -> dict:
    """Analyze a queryset independently so one invalid CV never stops the batch."""
    if queryset is None:
        queryset = Application.objects.all()
    applications = queryset.select_related("offer").prefetch_related("documents")
    summary = {
        "total": applications.count(),
        "already_analyzed": 0,
        "analyses_created": 0,
        "analyses_updated": 0,
        "matchings_created": 0,
        "matchings_updated": 0,
        "without_cv": 0,
        "errors": 0,
        "ignored": 0,
        "details": [],
    }
    for application in applications.iterator(chunk_size=100):
        try:
            result = process_application_analysis(
                application,
                force_analysis=force_analysis,
                force_matching=force_matching,
            )
        except Exception as exc:  # pragma: no cover - protects long operational batches
            logger.exception("Unexpected application analysis failure application_id=%s", application.pk)
            result = ApplicationAnalysisResult(
                application_id=application.pk,
                status="error",
                error=f"Erreur inattendue ({exc.__class__.__name__}).",
            )
        if result.status == "already_complete":
            summary["already_analyzed"] += 1
        elif result.status == "no_cv":
            summary["without_cv"] += 1
        elif result.status == "error":
            summary["errors"] += 1
        elif result.status in {"ignored", "analyzed_without_offer", "stale_human_validated"}:
            summary["ignored"] += 1
        summary["analyses_created"] += int(result.analysis_created)
        summary["analyses_updated"] += int(result.analysis_updated)
        summary["matchings_created"] += int(result.matching_created)
        summary["matchings_updated"] += int(result.matching_updated)
        if result.error:
            summary["details"].append(result.as_dict())
    return summary


def recalculate_offer_matches(offer: Offer) -> dict:
    """Recalculate the offer against every representative candidate in the pool."""
    from .intelligence import rank_offer_candidates

    rows = rank_offer_candidates(offer, force=True)
    summary = {
        "offer": offer.pk,
        "total": len(rows),
        "updated": sum(row["match"] is not None for row in rows),
        "without_analysis": sum(row["match"] is None for row in rows),
        "errors": 0,
        "details": [],
    }
    return summary
