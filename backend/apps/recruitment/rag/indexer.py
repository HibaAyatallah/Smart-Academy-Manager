"""Idempotent CV indexing orchestration."""

import hashlib
import json
import logging

from django.conf import settings

from apps.recruitment.analysis_pipeline import analysis_is_stale
from apps.recruitment.choices import ApplicationDocumentType
from apps.recruitment.embeddings import (
    EmbeddingError,
    embedding_model_identifier,
    expected_embedding_dimensions,
    get_or_create_embedding,
)
from apps.recruitment.models import Application, CVRAGIndexState

from .chunking import chunk_sections, cv_sections
from .errors import RAGEmbeddingError, RAGIndexingError, RAGValidationError, VectorStoreError
from .vector_store import VectorRecord, get_vector_store

logger = logging.getLogger(__name__)


def current_index_fingerprint(application, analysis, document) -> str:
    data = {
        "application_id": application.pk,
        "cv_sha256": analysis.source_sha256,
        "extractor_version": analysis.extractor_version,
        "rag_index_version": settings.RAG_INDEX_VERSION,
        "embedding_model": embedding_model_identifier(),
        "chunk_size": settings.RAG_CHUNK_SIZE,
        "chunk_overlap": settings.RAG_CHUNK_OVERLAP,
        "sections": cv_sections(analysis),
        "document_id": document.pk if document else None,
    }
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunk_id(application_id: int, fingerprint: str, section: str, index: int, content_hash: str) -> str:
    raw = f"{application_id}:{fingerprint}:{section}:{index}:{content_hash}"
    return "cv-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def current_index_material(application):
    """Return the current document, analysis, fingerprint, chunks and stable ids."""
    document = application.documents.filter(
        document_type=ApplicationDocumentType.CV,
    ).order_by("-uploaded_at", "-id").first()
    if document is None:
        raise RAGValidationError("Aucun CV n’est associé à cette candidature.")
    analysis = getattr(application, "cv_analysis", None)
    if analysis is None:
        raise RAGValidationError("Le CV n’a pas encore d’analyse exploitable.")
    if analysis_is_stale(application, analysis):
        raise RAGValidationError("L’analyse du CV est obsolète et doit être actualisée avant indexation.")

    fingerprint = current_index_fingerprint(application, analysis, document)
    chunks = chunk_sections(
        cv_sections(analysis),
        size=settings.RAG_CHUNK_SIZE,
        overlap=settings.RAG_CHUNK_OVERLAP,
    )
    if not chunks:
        raise RAGValidationError("L’analyse du CV ne contient aucun texte indexable.")
    expected_ids = {
        chunk_id(application.pk, fingerprint, chunk.section, chunk.chunk_index, chunk.content_hash)
        for chunk in chunks
    }
    return document, analysis, fingerprint, chunks, expected_ids


def index_candidate_cv(application_or_id, *, force=False, vector_store=None) -> dict:
    application_id = getattr(application_or_id, "pk", application_or_id)
    try:
        application = Application.objects.select_related(
            "candidate_profile__user", "cv_analysis"
        ).get(pk=application_id)
    except (Application.DoesNotExist, TypeError, ValueError) as exc:
        raise RAGValidationError("Candidature introuvable.") from exc

    document, analysis, fingerprint, chunks, expected_ids = current_index_material(application)

    store = vector_store or get_vector_store()
    application_filter = {"application_id": application.pk}
    state = CVRAGIndexState.objects.filter(application=application).first()
    if (
        not force
        and state is not None
        and state.content_fingerprint == fingerprint
        and store.ids(application_filter) == expected_ids
    ):
        return {
            "application_id": application.pk,
            "status": "already_indexed",
            "chunk_count": len(chunks),
            "content_fingerprint": fingerprint,
        }

    records = []
    try:
        for chunk in chunks:
            record_id = chunk_id(
                application.pk, fingerprint, chunk.section, chunk.chunk_index, chunk.content_hash
            )
            metadata = {
                "candidate_profile_id": application.candidate_profile_id,
                "application_id": application.pk,
                "application_document_id": document.pk,
                "candidate_name": application.candidate_profile.display_full_name,
                "source_type": "CV",
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
                "cv_sha256": analysis.source_sha256,
                "extractor_version": analysis.extractor_version,
                "rag_index_version": settings.RAG_INDEX_VERSION,
                "embedding_model": settings.RECRUITMENT_EMBEDDING_MODEL,
                "embedding_version": settings.RECRUITMENT_EMBEDDING_VERSION,
                "embedding_dimensions": expected_embedding_dimensions(),
                "content_fingerprint": fingerprint,
            }
            records.append(VectorRecord(
                id=record_id,
                text=chunk.text,
                embedding=get_or_create_embedding(chunk.text),
                metadata=metadata,
            ))
    except EmbeddingError as exc:
        logger.warning(
            "RAG indexing embedding failure application_id=%s code=%s",
            application.pk,
            exc.code,
        )
        raise RAGEmbeddingError("Le modèle d’embedding RAG est indisponible.") from exc

    old_ids = store.ids(application_filter)
    try:
        store.upsert(records)
        store.delete(sorted(old_ids - expected_ids))
    except VectorStoreError:
        logger.warning("RAG vector store failure application_id=%s", application.pk)
        raise

    CVRAGIndexState.objects.update_or_create(
        application=application,
        defaults={
            "application_document": document,
            "cv_sha256": analysis.source_sha256,
            "extractor_version": analysis.extractor_version,
            "rag_index_version": settings.RAG_INDEX_VERSION,
            "embedding_model": embedding_model_identifier(),
            "content_fingerprint": fingerprint,
            "chunk_count": len(records),
        },
    )
    return {
        "application_id": application.pk,
        "status": "indexed",
        "chunk_count": len(records),
        "content_fingerprint": fingerprint,
    }
