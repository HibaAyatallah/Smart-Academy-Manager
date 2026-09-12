"""Optional local embeddings for recruitment matching.

Ollama only produces vectors. Cosine similarity and all scoring remain Python
operations. Failures are surfaced as typed errors so callers can safely fall
back to deterministic matching.
"""

import json
import logging
import math
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.module_loading import import_string

from .models import EmbeddingCache
from .representations import text_hash

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    code = "embedding_error"


class EmbeddingUnavailableError(EmbeddingError):
    code = "embedding_unavailable"


class EmbeddingTimeoutError(EmbeddingError):
    code = "embedding_timeout"


class EmbeddingModelUnavailableError(EmbeddingError):
    code = "embedding_model_unavailable"


class InvalidEmbeddingError(EmbeddingError):
    code = "invalid_embedding"


def validate_embedding(vector) -> list[float]:
    if not isinstance(vector, (list, tuple)) or not vector:
        raise InvalidEmbeddingError("Le vecteur d’embedding est vide ou absent.")
    validated = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidEmbeddingError("Le vecteur contient une valeur non numérique.")
        number = float(value)
        if not math.isfinite(number):
            raise InvalidEmbeddingError("Le vecteur contient NaN ou Inf.")
        validated.append(number)
    return validated


def cosine_similarity(left, right) -> float:
    left = validate_embedding(left)
    right = validate_embedding(right)
    if len(left) != len(right):
        raise InvalidEmbeddingError("Les vecteurs n’ont pas la même dimension.")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise InvalidEmbeddingError("La similarité cosinus ne peut pas utiliser un vecteur nul.")
    similarity = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    if not math.isfinite(similarity):
        raise InvalidEmbeddingError("La similarité calculée est invalide.")
    return max(-1.0, min(1.0, similarity))


def cosine_score(left, right) -> float:
    """Convert cosine [-1, 1] to the existing score scale by clipping negatives."""
    return round(100 * max(0.0, cosine_similarity(left, right)), 2)


def embedding_model_identifier() -> str:
    return (
        f"ollama:{settings.RECRUITMENT_EMBEDDING_MODEL}"
        f"@{settings.RECRUITMENT_EMBEDDING_VERSION}/{expected_embedding_dimensions()}d"
    )


def expected_embedding_dimensions() -> int:
    dimensions = getattr(settings, "RECRUITMENT_EMBEDDING_DIMENSIONS", 1024)
    if isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions <= 0:
        raise InvalidEmbeddingError("La dimension d’embedding configurée est invalide.")
    return dimensions


def validate_expected_dimensions(vector) -> list[float]:
    vector = validate_embedding(vector)
    expected = expected_embedding_dimensions()
    if len(vector) != expected:
        raise InvalidEmbeddingError(
            f"Dimension d’embedding inattendue : {len(vector)} reçue, {expected} attendue."
        )
    return vector


class OllamaEmbeddingProvider:
    def __init__(self, *, base_url=None, model=None, timeout=None, urlopen_func=None):
        self.base_url = (base_url or settings.RECRUITMENT_OLLAMA_BASE_URL).rstrip("/") + "/"
        self.model = model or settings.RECRUITMENT_EMBEDDING_MODEL
        self.timeout = timeout or settings.RECRUITMENT_EMBEDDING_TIMEOUT
        self._urlopen = urlopen_func or urlopen
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RECRUITMENT_OLLAMA_BASE_URL must be an absolute HTTP(S) URL.")

    def embed(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise InvalidEmbeddingError("Le texte à encoder est vide.")
        body = json.dumps({"model": self.model, "input": text}).encode("utf-8")
        request = Request(
            urljoin(self.base_url, "api/embed"),
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self._urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise EmbeddingTimeoutError("Ollama n’a pas répondu avant le timeout.") from exc
        except HTTPError as exc:
            if exc.code == 404:
                raise EmbeddingModelUnavailableError(f"Le modèle {self.model} est indisponible.") from exc
            raise EmbeddingUnavailableError(
                f"Ollama a retourné une erreur HTTP {exc.code}."
            ) from exc
        except (URLError, ConnectionError, OSError) as exc:
            raise EmbeddingUnavailableError("Ollama est indisponible.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError) as exc:
            raise InvalidEmbeddingError("La réponse Ollama est invalide.") from exc
        embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        vector = embeddings[0] if isinstance(embeddings, list) and embeddings else None
        return validate_expected_dimensions(vector)


class DisabledEmbeddingProvider:
    """Explicit provider for tests or installations that disable embeddings."""

    def embed(self, text: str) -> list[float]:
        raise EmbeddingUnavailableError("Le fournisseur d’embeddings est désactivé.")


def _provider():
    provider_class = import_string(settings.RECRUITMENT_EMBEDDING_PROVIDER)
    return provider_class()


def get_or_create_embedding(text: str) -> list[float]:
    representation_hash = text_hash(text)
    model_identifier = embedding_model_identifier()
    cached = EmbeddingCache.objects.filter(
        representation_hash=representation_hash,
        model_identifier=model_identifier,
    ).first()
    if cached is not None:
        vector = validate_expected_dimensions(cached.vector)
        if len(vector) != cached.dimensions:
            raise InvalidEmbeddingError("La dimension du vecteur en cache est incohérente.")
        return vector

    vector = validate_expected_dimensions(_provider().embed(text))
    try:
        with transaction.atomic():
            cached, _ = EmbeddingCache.objects.get_or_create(
                representation_hash=representation_hash,
                model_identifier=model_identifier,
                defaults={"vector": vector, "dimensions": len(vector)},
            )
    except IntegrityError:
        cached = EmbeddingCache.objects.get(
            representation_hash=representation_hash,
            model_identifier=model_identifier,
        )
    return validate_expected_dimensions(cached.vector)


def semantic_score(candidate_text: str, offer_text: str) -> float:
    return cosine_score(
        get_or_create_embedding(candidate_text),
        get_or_create_embedding(offer_text),
    )
