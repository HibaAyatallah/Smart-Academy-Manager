import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .analysis_pipeline import process_application_analysis
from .choices import ApplicationDocumentType
from .models import ApplicationDocument

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ApplicationDocument)
def analyze_new_cv_document(sender, instance, created, **kwargs):
    """Keep every newly added or replacement CV on the same analysis pipeline."""
    if not created or instance.document_type != ApplicationDocumentType.CV:
        return
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
