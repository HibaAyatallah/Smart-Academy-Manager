"""Vector-store boundary and local persistent Chroma implementation."""

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from .errors import VectorStoreError


@dataclass(frozen=True)
class VectorRecord:
    id: str
    text: str
    embedding: list[float]
    metadata: dict


class VectorStore(Protocol):
    def upsert(self, records: list[VectorRecord]) -> None: ...
    def delete(self, ids: list[str]) -> None: ...
    def ids(self, where: dict) -> set[str]: ...
    def query(self, embedding: list[float], *, top_k: int, where: dict | None = None) -> list[dict]: ...


class ChromaVectorStore:
    def __init__(self, *, path=None, collection_name=None):
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(path or settings.RAG_CHROMA_PATH))
            self.collection = client.get_or_create_collection(
                name=collection_name or settings.RAG_CHROMA_COLLECTION,
                embedding_function=None,
                configuration={"hnsw": {"space": "cosine"}},
            )
        except Exception as exc:
            raise VectorStoreError("ChromaDB est indisponible ou mal configuré.") from exc

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        try:
            self.collection.upsert(
                ids=[item.id for item in records],
                embeddings=[item.embedding for item in records],
                documents=[item.text for item in records],
                metadatas=[item.metadata for item in records],
            )
        except Exception as exc:
            raise VectorStoreError("Impossible d’écrire les chunks dans ChromaDB.") from exc

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self.collection.delete(ids=ids)
        except Exception as exc:
            raise VectorStoreError("Impossible de supprimer les anciens chunks ChromaDB.") from exc

    def ids(self, where: dict) -> set[str]:
        try:
            return set(self.collection.get(where=where, include=[]).get("ids") or [])
        except Exception as exc:
            raise VectorStoreError("Impossible de lire l’index ChromaDB.") from exc

    def query(self, embedding: list[float], *, top_k: int, where: dict | None = None) -> list[dict]:
        try:
            available = self.collection.count()
            if available == 0:
                return []
            result = self.collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, available),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError("La recherche ChromaDB a échoué.") from exc
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        rows = []
        for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            similarity = max(-1.0, min(1.0, 1.0 - float(distance)))
            rows.append({
                "id": item_id,
                "text": document,
                "metadata": metadata or {},
                "similarity": similarity,
                "score": round(100 * max(0.0, similarity), 2),
            })
        return rows


def get_vector_store() -> VectorStore:
    store_class = import_string(settings.RAG_VECTOR_STORE)
    try:
        return store_class()
    except VectorStoreError:
        raise
    except Exception as exc:
        raise VectorStoreError("Le vector store RAG est indisponible.") from exc
