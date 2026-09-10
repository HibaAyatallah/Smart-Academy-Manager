class RAGError(Exception):
    code = "rag_error"


class RAGValidationError(RAGError):
    code = "rag_validation_error"


class RAGIndexingError(RAGError):
    code = "rag_indexing_error"


class RAGEmbeddingError(RAGError):
    code = "rag_embedding_unavailable"


class VectorStoreError(RAGError):
    code = "rag_vector_store_unavailable"
