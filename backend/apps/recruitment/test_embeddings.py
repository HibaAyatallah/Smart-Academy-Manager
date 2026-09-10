import math
import socket
from urllib.error import HTTPError, URLError

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, override_settings

from apps.business_units.models import BusinessUnit

from .choices import ApplicationType
from .embeddings import (
    EmbeddingTimeoutError,
    EmbeddingUnavailableError,
    EmbeddingModelUnavailableError,
    InvalidEmbeddingError,
    OllamaEmbeddingProvider,
    cosine_score,
    cosine_similarity,
    get_or_create_embedding,
    semantic_score,
)
from .intelligence import (
    MatchingCalculationError,
    calculate_match,
    match_application,
    match_is_stale,
    normalized_weighted_score,
)
from .models import Application, CandidateProfile, CVAnalysis, EmbeddingCache, Offer
from .representations import build_candidate_representation, build_offer_representation


User = get_user_model()


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class CountingEmbeddingProvider:
    calls = []

    def embed(self, text):
        self.__class__.calls.append(text)
        folded = text.casefold()
        return [1.0, 0.05, 0.0] if "python" in folded else [0.0, 1.0, 0.05]


class FailingEmbeddingProvider:
    def embed(self, text):
        raise EmbeddingUnavailableError("offline")


class EmbeddingMathTests(SimpleTestCase):
    def test_cosine_similarity_and_strong_score(self):
        self.assertAlmostEqual(cosine_similarity([1, 0.1], [0.99, 0.1]), 1.0, places=3)
        self.assertGreater(cosine_score([1, 0.1], [0.99, 0.1]), 99)

    def test_empty_zero_dimension_and_non_finite_vectors_are_rejected(self):
        invalid_pairs = [
            ([], [1]),
            ([0, 0], [1, 1]),
            ([1], [1, 2]),
            ([math.nan], [1]),
            ([math.inf], [1]),
        ]
        for left, right in invalid_pairs:
            with self.subTest(left=left, right=right), self.assertRaises(InvalidEmbeddingError):
                cosine_similarity(left, right)

    def test_ollama_provider_returns_valid_embedding(self):
        provider = OllamaEmbeddingProvider(
            base_url="http://ollama.test:11434",
            model="bge-m3",
            urlopen_func=lambda request, timeout: FakeResponse(b'{"embeddings":[[0.1,0.2,0.3]]}'),
        )
        self.assertEqual(provider.embed("Python"), [0.1, 0.2, 0.3])

    def test_ollama_unavailable_timeout_and_empty_vector_are_typed(self):
        unavailable = OllamaEmbeddingProvider(urlopen_func=lambda request, timeout: (_ for _ in ()).throw(URLError("down")))
        timeout = OllamaEmbeddingProvider(urlopen_func=lambda request, timeout: (_ for _ in ()).throw(socket.timeout()))
        empty = OllamaEmbeddingProvider(urlopen_func=lambda request, timeout: FakeResponse(b'{"embeddings":[]}'))
        with self.assertRaises(EmbeddingUnavailableError):
            unavailable.embed("text")
        with self.assertRaises(EmbeddingTimeoutError):
            timeout.embed("text")
        with self.assertRaises(InvalidEmbeddingError):
            empty.embed("text")

    def test_missing_ollama_model_is_typed(self):
        def missing_model(request, timeout):
            raise HTTPError(request.full_url, 404, "not found", {}, None)

        provider = OllamaEmbeddingProvider(urlopen_func=missing_model)
        with self.assertRaises(EmbeddingModelUnavailableError):
            provider.embed("text")

    def test_ollama_http_failure_preserves_status_for_diagnostics(self):
        def server_failure(request, timeout):
            raise HTTPError(request.full_url, 503, "unavailable", {}, None)

        provider = OllamaEmbeddingProvider(urlopen_func=server_failure)
        with self.assertRaisesRegex(EmbeddingUnavailableError, "HTTP 503"):
            provider.embed("text")

    def test_all_available_weights_are_normalized_from_120_to_100(self):
        score, total_weight = normalized_weighted_score(
            [(100, 50), (100, 25), (100, 15), (100, 30)]
        )

        self.assertEqual(total_weight, 120)
        self.assertEqual(score, 100)

    def test_missing_component_is_excluded_instead_of_counting_as_zero(self):
        # The absent experience/education criteria are omitted. With only a
        # 50-point skill score and an 80-point semantic score, the result is
        # (50*50 + 80*30) / (50+30) = 61.25, not 40.83 over all 120 points.
        score, total_weight = normalized_weighted_score([(50, 50), (80, 30)])

        self.assertEqual(total_weight, 80)
        self.assertEqual(score, 61.25)

    def test_weighted_score_is_always_between_zero_and_one_hundred(self):
        for components in (
            [(0, 50)],
            [(100, 30)],
            [(0, 50), (100, 30)],
            [(33.33, 50), (75, 25), (20, 15), (91.5, 30)],
        ):
            with self.subTest(components=components):
                score, _ = normalized_weighted_score(components)
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)

    def test_no_available_component_does_not_invent_zero_score(self):
        with self.assertRaises(MatchingCalculationError):
            normalized_weighted_score([])


@override_settings(
    RECRUITMENT_EMBEDDING_PROVIDER="apps.recruitment.test_embeddings.CountingEmbeddingProvider",
    RECRUITMENT_EMBEDDING_MODEL="bge-m3",
    RECRUITMENT_EMBEDDING_VERSION="test-v1",
)
class EmbeddingIntegrationTests(TestCase):
    def setUp(self):
        CountingEmbeddingProvider.calls = []
        admin = User.objects.create_superuser(email="embedding-admin@example.com", password="test")
        bu = BusinessUnit.objects.create(name="Embeddings", code="EMB", manager=admin)
        self.offer = Offer.objects.create(
            title="Python backend",
            description="Développer des API Django",
            business_unit=bu,
            application_type=ApplicationType.HIRING,
            required_skills="Python, Django",
            created_by=admin,
        )
        candidate = User.objects.create_user(email="embedding@example.com", password="test")
        profile = CandidateProfile.objects.create(user=candidate)
        self.application = Application.objects.create(
            candidate_profile=profile,
            offer=self.offer,
            application_type=ApplicationType.HIRING,
        )
        self.analysis = CVAnalysis.objects.create(
            application=self.application,
            skills=["Python", "Django"],
            experiences=[],
            raw_text="Projets : moteur de recommandation et API backend.",
            source_sha256="a" * 64,
            extractor_version="structured-v7",
        )

    def test_candidate_representation_contains_full_extracted_cv(self):
        candidate_text = build_candidate_representation(self.application, self.analysis)

        self.assertIn("cv_full_text: Projets : moteur de recommandation", candidate_text)

    def test_candidate_offer_embeddings_are_cached_and_reproducible(self):
        candidate_text = build_candidate_representation(self.application, self.analysis)
        offer_text = build_offer_representation(self.offer)
        first = semantic_score(candidate_text, offer_text)
        second = semantic_score(candidate_text, offer_text)

        self.assertEqual(first, second)
        self.assertGreater(first, 99)
        self.assertEqual(len(CountingEmbeddingProvider.calls), 2)
        self.assertEqual(EmbeddingCache.objects.count(), 2)

    def test_semantic_score_is_integrated_into_application_match(self):
        match = match_application(self.application, include_recommendations=False)[0]
        same_match = match_application(self.application, include_recommendations=False)[0]

        self.assertIsNotNone(match.semantic_score)
        self.assertEqual(match.semantic_model, "ollama:bge-m3@test-v1")
        self.assertTrue(match.score_breakdown["semantic"]["available"])
        self.assertEqual(match.score_breakdown["semantic"]["weight"], 30)
        self.assertEqual(float(match.score), 100.0)
        self.assertEqual(match.id, same_match.id)
        self.assertEqual(self.application.matches.count(), 1)
        self.assertEqual(EmbeddingCache.objects.count(), 2)

    def test_candidate_and_offer_representation_changes_invalidate(self):
        match = match_application(self.application, include_recommendations=False)[0]
        self.assertEqual(len(CountingEmbeddingProvider.calls), 2)
        self.analysis.languages = ["Français"]
        self.analysis.save(update_fields=["languages"])
        self.assertTrue(match_is_stale(match, self.application, self.offer, self.analysis))

        match = match_application(self.application, include_recommendations=False)[0]
        self.assertEqual(len(CountingEmbeddingProvider.calls), 3)
        self.offer.description = "Architecture Java distribuée"
        self.offer.save(update_fields=["description"])
        self.assertTrue(match_is_stale(match, self.application, self.offer, self.analysis))
        match_application(self.application, include_recommendations=False)
        self.assertEqual(len(CountingEmbeddingProvider.calls), 4)

    @override_settings(RECRUITMENT_EMBEDDING_VERSION="test-v2")
    def test_model_version_change_invalidates_match_and_embedding_cache_key(self):
        with override_settings(RECRUITMENT_EMBEDDING_VERSION="test-v1"):
            match = match_application(self.application, include_recommendations=False)[0]
        self.assertTrue(match_is_stale(match, self.application, self.offer, self.analysis))
        match_application(self.application, include_recommendations=False)
        self.assertEqual(EmbeddingCache.objects.filter(model_identifier__endswith="@test-v2").count(), 2)

    @override_settings(RECRUITMENT_EMBEDDING_PROVIDER="apps.recruitment.test_embeddings.FailingEmbeddingProvider")
    def test_ollama_failure_falls_back_to_deterministic_matching(self):
        result = calculate_match(self.application, self.offer, self.analysis)

        self.assertIsNone(result["semantic_score"])
        self.assertFalse(result["score_breakdown"]["semantic"]["available"])
        self.assertEqual(result["score_breakdown"]["semantic"]["error_code"], "embedding_unavailable")
        self.assertEqual(result["score"], 100.0)
