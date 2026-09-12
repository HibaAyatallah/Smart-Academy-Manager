"""Immediate SQL invalidation and best-effort post-commit Chroma cleanup."""

import logging

from django.db import transaction

from apps.recruitment.models import CVRAGIndexState

from .errors import VectorStoreError
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


def _cleanup_if_still_invalid(application_id: int) -> None:
    # A controlled reindex may have completed before this callback executes. In
    # that case the indexer has already replaced obsolete ids and owns cleanup.
    if CVRAGIndexState.objects.filter(application_id=application_id).exists():
        return
    try:
        store = get_vector_store()
        stale_ids = store.ids({"application_id": application_id})
        store.delete(sorted(stale_ids))
    except VectorStoreError:
        # The missing SQL manifest remains the fail-closed freshness gate.
        logger.warning("Deferred RAG cleanup failed application_id=%s", application_id)


def invalidate_cv_index(application_id: int) -> bool:
    """Invalidate synchronously; remove external vectors safely after commit."""
    deleted, _ = CVRAGIndexState.objects.filter(application_id=application_id).delete()
    if deleted:
        transaction.on_commit(lambda: _cleanup_if_still_invalid(application_id))
    return bool(deleted)
