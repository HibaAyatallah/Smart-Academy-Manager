import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .analysis_pipeline import process_application_analysis
from .choices import ApplicationDocumentType
from .models import ApplicationDocument, CVAnalysis
from .rag.invalidation import invalidate_cv_index

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ApplicationDocument)
def analyze_new_cv_document(sender, instance, created, **kwargs):
    """Keep every newly added or replacement CV on the same analysis pipeline."""
    if not created or instance.document_type != ApplicationDocumentType.CV:
        return
    # Fail closed immediately. Extraction may be expensive and may fail, so the
    # previous vector index must no longer be authorized before it starts.
    invalidate_cv_index(instance.application_id)
    try:
        instance._analysis_result = process_application_analysis(
            instance.application,
        )
    except Exception as exc:  # The CV must remain stored even when extraction fails.
        logger.exception(
            "Automatic CV processing failed application_id=%s error_type=%s",
            instance.application_id,
            exc.__class__.__name__,
        )
        instance._analysis_result = None


@receiver(post_delete, sender=ApplicationDocument)
def invalidate_deleted_cv_document(sender, instance, **kwargs):
    if instance.document_type == ApplicationDocumentType.CV:
        invalidate_cv_index(instance.application_id)


RAG_ANALYSIS_FIELDS = {
    "skills", "experiences", "diplomas", "full_name", "location", "education",
    "companies", "positions", "languages", "certifications", "raw_text",
    "source_sha256", "extractor_version",
}


@receiver(post_save, sender=CVAnalysis)
def invalidate_changed_cv_analysis(sender, instance, created, update_fields=None, **kwargs):
    if created or update_fields is None or RAG_ANALYSIS_FIELDS.intersection(update_fields):
        invalidate_cv_index(instance.application_id)
