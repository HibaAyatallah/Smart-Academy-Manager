"""Public service facade for future API and Chat Admin integration."""

from .indexer import index_candidate_cv
from .retriever import retrieve_cv_context

__all__ = ["index_candidate_cv", "retrieve_cv_context"]
