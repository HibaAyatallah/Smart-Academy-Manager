import math
import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from apps.business_units.models import BusinessUnit

from .choices import ApplicationDocumentType, ApplicationType
from .models import Application, ApplicationDocument, CandidateProfile, CVRAGIndexState, Offer
from .rag.chunking import chunk_sections, chunk_text
from .rag.errors import RAGEmbeddingError, VectorStoreError
from .rag.indexer import index_candidate_cv
from .rag.retriever import retrieve_cv_context
from .rag.vector_store import ChromaVectorStore, VectorRecord


User = get_user_model()
MEDIA_ROOT = tempfile.mkdtemp()


def fake_embedding(text):
    folded = text.casefold()
    vector = [
        1.0 + folded.count("python") + folded.count("django"),
        1.0 + folded.count("java") + folded.count("spring"),
        1.0 + folded.count("management") + folded.count("gestion"),
    ]
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector]


class FakeVectorStore:
    def __init__(self):
        self.records = {}
        self.upsert_calls = 0
        self.deleted = []

    def upsert(self, records: list[VectorRecord]):
        self.upsert_calls += 1
        self.records.update({item.id: item for item in records})

    def delete(self, ids):
        self.deleted.extend(ids)
        for item_id in ids:
            self.records.pop(item_id, None)

    def ids(self, where):
        return {item.id for item in self.records.values() if self._matches(item.metadata, where)}

    def query(self, embedding, *, top_k, where=None):
        rows = []
        for item in self.records.values():
            if where and not self._matches(item.metadata, where):
                continue
            similarity = sum(a * b for a, b in zip(embedding, item.embedding))
            rows.append({
                "id": item.id, "text": item.text, "metadata": item.metadata,
                "similarity": similarity, "score": round(100 * max(0, similarity), 2),
            })
        return sorted(rows, key=lambda row: (-row["similarity"], row["id"]))[:top_k]

    @classmethod
    def _matches(cls, metadata, where):
        if not where:
            return True
        if "$and" in where:
            return all(cls._matches(metadata, item) for item in where["$and"])
        return all(metadata.get(key) == value for key, value in where.items())


class BrokenVectorStore(FakeVectorStore):
    def query(self, embedding, *, top_k, where=None):
        raise VectorStoreError("offline")


class RAGChunkingTests(SimpleTestCase):
    def test_chunking_is_deterministic_section_aware_and_overlapping(self):
        text = " ".join(f"token{i}" for i in range(80))
        first = chunk_sections([("EXPERIENCE", text)], size=140, overlap=35)
        second = chunk_sections([("EXPERIENCE", text)], size=140, overlap=35)

        self.assertEqual(first, second)
        self.assertGreater(len(first), 1)
        self.assertTrue(all(item.section == "EXPERIENCE" for item in first))
        self.assertTrue(set(first[0].text.split()) & set(first[1].text.split()))
        self.assertEqual([item.chunk_index for item in first], list(range(len(first))))

    def test_invalid_chunk_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            chunk_text("text", size=50, overlap=10)
        with self.assertRaises(ValueError):
            chunk_text("text", size=100, overlap=100)


class ChromaVectorStoreTests(SimpleTestCase):
    class Collection:
        def __init__(self, count):
            self._count = count
            self.requested = None

        def count(self):
            return self._count

        def query(self, **kwargs):
            self.requested = kwargs["n_results"]
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    def test_query_returns_empty_without_asking_chroma_on_empty_index(self):
        store = object.__new__(ChromaVectorStore)
        store.collection = self.Collection(0)
        self.assertEqual(store.query([1.0], top_k=5), [])
        self.assertIsNone(store.collection.requested)

    def test_query_caps_top_k_to_available_vectors(self):
        store = object.__new__(ChromaVectorStore)
        store.collection = self.Collection(2)
        store.query([1.0], top_k=5)
        self.assertEqual(store.collection.requested, 2)


@override_settings(MEDIA_ROOT=MEDIA_ROOT, RAG_CHUNK_SIZE=140, RAG_CHUNK_OVERLAP=25, RAG_MAX_TOP_K=10)
class RAGServiceTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.index_embedding = patch(
            "apps.recruitment.rag.indexer.get_or_create_embedding", side_effect=fake_embedding
        )
        self.query_embedding = patch(
            "apps.recruitment.rag.retriever.get_or_create_embedding", side_effect=fake_embedding
        )
        self.index_embedding.start()
        self.query_embedding.start()
        self.addCleanup(self.index_embedding.stop)
        self.addCleanup(self.query_embedding.stop)
        self.store = FakeVectorStore()
        admin = User.objects.create_superuser(email="rag-admin@example.com", password="test")
        bu = BusinessUnit.objects.create(name="RAG", code="RAG", manager=admin)
        self.offer = Offer.objects.create(
            title="Backend", description="Python Django", business_unit=bu,
            application_type=ApplicationType.HIRING, required_skills="Python, Django", created_by=admin,
        )
        self.application = self._application("aya", "Skills: Python Django\nExperience\nBackend APIs Python")

    def _application(self, suffix, content):
        user = User.objects.create_user(
            email=f"{suffix}@example.com", password="test", first_name=suffix.title(), last_name="Candidate"
        )
        profile = CandidateProfile.objects.create(user=user)
        application = Application.objects.create(
            candidate_profile=profile, offer=self.offer, application_type=ApplicationType.HIRING
        )
        raw = content.encode()
        ApplicationDocument.objects.create(
            application=application, document_type=ApplicationDocumentType.CV,
            file=SimpleUploadedFile(f"{suffix}.txt", raw, content_type="text/plain"),
            original_name=f"{suffix}.txt", content_type="text/plain", size=len(raw),
        )
        application.refresh_from_db()
        return application

    def test_index_metadata_and_idempotence(self):
        first = index_candidate_cv(self.application, vector_store=self.store)
        second = index_candidate_cv(self.application, vector_store=self.store)

        self.assertEqual(first["status"], "indexed")
        self.assertEqual(second["status"], "already_indexed")
        self.assertEqual(self.store.upsert_calls, 1)
        self.assertEqual(len(self.store.records), first["chunk_count"])
        metadata = next(iter(self.store.records.values())).metadata
        for key in (
            "candidate_profile_id", "application_id", "application_document_id", "candidate_name",
            "source_type", "section", "chunk_index", "cv_sha256", "extractor_version",
            "rag_index_version", "embedding_model", "embedding_version",
        ):
            self.assertIn(key, metadata)
        self.assertEqual(metadata["source_type"], "CV")
        self.assertEqual(CVRAGIndexState.objects.get(application=self.application).chunk_count, len(self.store.records))

    def test_analysis_content_and_index_version_changes_replace_old_chunks(self):
        first = index_candidate_cv(self.application, vector_store=self.store)
        old_ids = set(self.store.records)
        analysis = self.application.cv_analysis
        analysis.skills = ["Java", "Spring"]
        analysis.save(update_fields=["skills"])
        second = index_candidate_cv(self.application, vector_store=self.store)

        self.assertNotEqual(first["content_fingerprint"], second["content_fingerprint"])
        self.assertTrue(old_ids & set(self.store.deleted))
        current_ids = set(self.store.records)
        with override_settings(RAG_INDEX_VERSION="cv-rag-v2"):
            third = index_candidate_cv(self.application, vector_store=self.store)
        self.assertNotEqual(second["content_fingerprint"], third["content_fingerprint"])
        self.assertTrue(current_ids & set(self.store.deleted))

    def test_replacing_cv_document_reindexes_and_removes_previous_chunks(self):
        first = index_candidate_cv(self.application, vector_store=self.store)
        old_ids = set(self.store.records)
        replacement = b"Skills: Java Spring\nExperience\nBackend Java services"
        ApplicationDocument.objects.create(
            application=self.application,
            document_type=ApplicationDocumentType.CV,
            file=SimpleUploadedFile("aya-v2.txt", replacement, content_type="text/plain"),
            original_name="aya-v2.txt",
            content_type="text/plain",
            size=len(replacement),
        )
        self.application.refresh_from_db()

        second = index_candidate_cv(self.application, vector_store=self.store)

        self.assertNotEqual(first["content_fingerprint"], second["content_fingerprint"])
        self.assertTrue(old_ids.issubset(set(self.store.deleted)))
        self.assertFalse(old_ids & set(self.store.records))
        state = CVRAGIndexState.objects.get(application=self.application)
        current_document = self.application.documents.order_by("-uploaded_at", "-id").first()
        self.assertEqual(state.application_document_id, current_document.id)

    def test_retrieval_is_relevant_filtered_and_honors_top_k(self):
        other = self._application("java", "Skills: Java Spring\nEnterprise Java services")
        index_candidate_cv(self.application, vector_store=self.store)
        index_candidate_cv(other, vector_store=self.store)

        python_rows = retrieve_cv_context(
            "technologies Python backend", application_id=self.application.id,
            top_k=2, vector_store=self.store,
        )
        self.assertLessEqual(len(python_rows), 2)
        self.assertTrue(python_rows)
        self.assertTrue(all(row["metadata"]["application_id"] == self.application.id for row in python_rows))
        self.assertIn("Python", python_rows[0]["text"])

        candidate_rows = retrieve_cv_context(
            "Java Spring", candidate_profile_id=other.candidate_profile_id,
            top_k=1, vector_store=self.store,
        )
        self.assertEqual(len(candidate_rows), 1)
        self.assertEqual(candidate_rows[0]["metadata"]["candidate_profile_id"], other.candidate_profile_id)

    def test_embedding_and_vector_store_failures_are_clear(self):
        with patch(
            "apps.recruitment.rag.retriever.get_or_create_embedding",
            side_effect=__import__("apps.recruitment.embeddings", fromlist=["EmbeddingUnavailableError"]).EmbeddingUnavailableError("offline"),
        ):
            with self.assertRaises(RAGEmbeddingError):
                retrieve_cv_context("Python", vector_store=self.store)
        with self.assertRaises(VectorStoreError):
            retrieve_cv_context("Python", vector_store=BrokenVectorStore())
