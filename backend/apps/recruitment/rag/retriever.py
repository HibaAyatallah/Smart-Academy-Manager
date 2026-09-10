"""Semantic retrieval over indexed CV chunks, without answer generation."""

import logging

from django.conf import settings

from apps.recruitment.embeddings import EmbeddingError, get_or_create_embedding

from .errors import RAGEmbeddingError, RAGValidationError, VectorStoreError
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


def _where(candidate_profile_id=None, application_id=None):
    filters = []
    if candidate_profile_id is not None:
        try:
            filters.append({"candidate_profile_id": int(candidate_profile_id)})
        except (TypeError, ValueError) as exc:
            raise RAGValidationError("candidate_profile_id doit être un entier.") from exc
    if application_id is not None:
        try:
            filters.append({"application_id": int(application_id)})
        except (TypeError, ValueError) as exc:
            raise RAGValidationError("application_id doit être un entier.") from exc
    if len(filters) == 1:
        return filters[0]
    if len(filters) > 1:
        return {"$and": filters}
    return None


def retrieve_cv_context(
    query,
    *,
    candidate_profile_id=None,
    application_id=None,
    top_k=5,
    vector_store=None,
) -> list[dict]:
    if not isinstance(query, str) or not query.strip():
        raise RAGValidationError("La question ne peut pas être vide.")
    query = " ".join(query.split())
    try:
        top_k = int(top_k)
    except (TypeError, ValueError) as exc:
        raise RAGValidationError("top_k doit être un entier.") from exc
    if top_k < 1 or top_k > settings.RAG_MAX_TOP_K:
        raise RAGValidationError(f"top_k doit être compris entre 1 et {settings.RAG_MAX_TOP_K}.")
    try:
        query_embedding = get_or_create_embedding(query)
    except EmbeddingError as exc:
        logger.warning("RAG retrieval embedding failure code=%s", exc.code)
        raise RAGEmbeddingError("Le modèle d’embedding RAG est indisponible.") from exc
    store = vector_store or get_vector_store()
    try:
        return store.query(
            query_embedding,
            top_k=top_k,
            where=_where(candidate_profile_id, application_id),
        )
    except VectorStoreError:
        logger.warning("RAG retrieval vector store failure")
        raise
