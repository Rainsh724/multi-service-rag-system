from typing import TypedDict


class RAGState(TypedDict, total=False):
    # Input
    question: str
    document_ids: list[str] | None
    top_k: int

    # Query processing
    standalone_question: str
    retrieval_strategy: str

    # Retrieval
    retrieved_chunks: list[dict]
    context: str

    # Context evaluation
    is_context_sufficient: bool
    evaluation_reason: str

    # Answer generation
    answer: str

    # Response formatting
    sources: list[dict]
    insufficient_context: bool

    # Error handling
    error: str | None