"""CV retrieval layer. No generative model is used in this package."""

from .indexer import index_candidate_cv
from .retriever import retrieve_cv_context

__all__ = ["index_candidate_cv", "retrieve_cv_context"]
