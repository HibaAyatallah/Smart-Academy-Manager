"""Semantic retrieval over indexed CV chunks, without answer generation."""

import logging

from django.conf import settings

from apps.recruitment.embeddings import EmbeddingError, embedding_model_identifier, get_or_create_embedding
from apps.recruitment.models import Application, CVRAGIndexState

from .errors import RAGEmbeddingError, RAGStaleIndexError, RAGValidationError, VectorStoreError
from .indexer import current_index_material
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


def _application(application_id, candidate_profile_id=None):
    if application_id is None:
        raise RAGValidationError("application_id est obligatoire pour isoler la recherche CV.")
    try:
        application_id = int(application_id)
    except (TypeError, ValueError) as exc:
        raise RAGValidationError("application_id doit être un entier.") from exc
    try:
        application = Application.objects.select_related("cv_analysis").get(pk=application_id)
    except Application.DoesNotExist as exc:
        raise RAGValidationError("Candidature introuvable.") from exc
    if candidate_profile_id is not None:
        try:
            candidate_profile_id = int(candidate_profile_id)
        except (TypeError, ValueError) as exc:
            raise RAGValidationError("candidate_profile_id doit être un entier.") from exc
        if application.candidate_profile_id != candidate_profile_id:
            raise RAGValidationError("La candidature n’appartient pas au candidat demandé.")
    return application


def _fresh_index(application):
    try:
        document, analysis, fingerprint, chunks, expected_ids = current_index_material(application)
    except RAGValidationError as exc:
        raise RAGStaleIndexError(
            "L’index RAG CV est absent ou obsolète. Réindexez la candidature."
        ) from exc
    state = CVRAGIndexState.objects.filter(application=application).first()
    fresh = (
        state is not None
        and state.application_document_id == document.pk
        and state.cv_sha256 == analysis.source_sha256
        and state.extractor_version == analysis.extractor_version
        and state.rag_index_version == settings.RAG_INDEX_VERSION
        and state.embedding_model == embedding_model_identifier()
        and state.content_fingerprint == fingerprint
        and state.chunk_count == len(chunks)
    )
    if not fresh:
        raise RAGStaleIndexError(
            "L’index RAG CV est absent ou obsolète. Réindexez la candidature."
        )
    return fingerprint, expected_ids


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
    application = _application(application_id, candidate_profile_id)
    fingerprint, expected_ids = _fresh_index(application)
    store = vector_store or get_vector_store()
    try:
        if store.ids({"application_id": application.pk}) != expected_ids:
            raise RAGStaleIndexError(
                "L’index Chroma du CV est incomplet ou obsolète. Réindexez la candidature."
            )
    except VectorStoreError:
        logger.warning("RAG freshness check vector store failure application_id=%s", application.pk)
        raise
    try:
        query_embedding = get_or_create_embedding(query)
    except EmbeddingError as exc:
        logger.warning("RAG retrieval embedding failure code=%s", exc.code)
        raise RAGEmbeddingError("Le modèle d’embedding RAG est indisponible.") from exc
    try:
        return store.query(
            query_embedding,
            top_k=top_k,
            where={"$and": [
                {"application_id": application.pk},
                {"content_fingerprint": fingerprint},
            ]},
        )
    except VectorStoreError:
        logger.warning("RAG retrieval vector store failure")
        raise
