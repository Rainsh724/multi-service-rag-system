
import logging

from services.rag_service.app.clients.llm_client import LLMClient
from services.rag_service.app.clients.retrieval_client import RetrievalClient
from services.rag_service.app.core.config import settings
from services.rag_service.app.graph.state import RAGState


logger = logging.getLogger(__name__)

INSUFFICIENT_ANSWER = (
    "اطلاعات کافی برای پاسخ‌گویی به این سؤال "
    "در اسناد بارگذاری‌شده پیدا نشد."
)


async def query_processing(state: RAGState) -> dict:
    question = state["question"].strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    return {
        "standalone_question": question,
        "error": None,
    }


async def retrieval(state: RAGState) -> dict:
    print("RETRIEVAL FUNCTION CALLED", flush=True)
    client = RetrievalClient()

    response = await client.search(
        query=state["standalone_question"],
        top_k=state.get("top_k", settings.default_top_k),
        document_ids=state.get("document_ids"),
    )

    chunks = [
        chunk.model_dump(mode="json")
        for chunk in response.matches
    ]

    print(
        "RETRIEVAL DEBUG:",
        [chunk.get("similarity") for chunk in chunks],
        flush=True,
    )

    logger.info(
        "Retrieval similarities: %s",
        [
            round(chunk["similarity"], 4)
            for chunk in chunks
            if chunk.get("similarity") is not None
        ],
    )

    logger.info(
        "Semantic retrieval completed: chunks=%d",
        len(chunks),
    )

    return {
        "retrieved_chunks": chunks,
    }


async def context_evaluation(state: RAGState) -> dict:
    print("CONTEXT EVALUATION FUNCTION CALLED", flush=True)
    chunks = state.get("retrieved_chunks", [])

    candidates = [
        chunk
        for chunk in chunks
        if chunk.get("text", "").strip()
    ]

    if not candidates:
        return {
            "retrieved_chunks": [],
            "context": "",
            "is_context_sufficient": False,
            "evaluation_reason": "No chunks retrieved.",
        }

    context = "\n\n".join(
        (
            f"[Source: {chunk['filename']}, "
            f"Page: {chunk['page_number']}]\n"
            f"{chunk['text']}"
        )
        for chunk in candidates
    )

    system_prompt = """
You are a strict context relevance evaluator for a RAG system.

Determine whether the context contains enough evidence
to answer the user's question.

Rules:
1. Evaluate only the supplied context.
2. Do not use external knowledge.
3. Topical similarity alone is not sufficient.
4. If the context does not contain the answer, return NO.
5. If the context contains sufficient evidence, return YES.
6. Return exactly one word: YES or NO.
"""

    print("EVALUATION CONTEXT:\n", context, flush=True)

    user_prompt = f"""
Question:
{state['question']}

Context:
{context}

Does this context contain enough information to answer the question?
"""

    llm = LLMClient()

    try:
        judgment = await llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    finally:
        await llm.client.close()

    sufficient = judgment.strip().upper().startswith("YES")

    print(
        "EVALUATION DEBUG:",
        repr(judgment),
        sufficient,
        flush=True,
    )

    logger.info(
        "Context evaluation: chunks=%d, judgment=%r, sufficient=%s",
        len(candidates),
        judgment,
        sufficient,
    )

    if not sufficient:
        return {
            "retrieved_chunks": [],
            "context": "",
            "is_context_sufficient": False,
            "evaluation_reason": "Context does not contain sufficient evidence.",
        }

    return {
        "retrieved_chunks": candidates,
        "context": context,
        "is_context_sufficient": True,
        "evaluation_reason": "Context contains sufficient evidence.",
    }


async def answer_generation(state: RAGState) -> dict:
    system_prompt = """
You are a Persian question-answering assistant.
Answer the user's question using only the supplied context.

Rules:
1. Do not use external knowledge or unsupported assumptions.
2. If the context does not contain the answer, explicitly say that
   the available documents do not provide enough information.
3. Answer in clear, natural Persian.
4. Preserve important technical terms when necessary.
5. Do not invent facts, numbers, names, or procedures.
6. Do not invent page numbers or source references.
"""

    user_prompt = f"""
Question:
{state['question']}

Retrieved context:
{state['context']}

Write a concise answer based strictly on the retrieved context.
"""

    llm = LLMClient()

    try:
        answer = await llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    finally:
        await llm.client.close()

    return {
        "answer": answer,
    }


async def response_formatting(state: RAGState) -> dict:
    insufficient = not state.get(
        "is_context_sufficient",
        False,
    )

    if insufficient:
        return {
            "answer": INSUFFICIENT_ANSWER,
            "sources": [],
            "insufficient_context": True,
        }

    sources = []
    seen = set()

    for chunk in state.get("retrieved_chunks", []):
        key = (
            chunk["document_id"],
            chunk["page_number"],
            chunk["chunk_id"],
        )

        if key in seen:
            continue

        seen.add(key)

        sources.append({
            "document_id": chunk["document_id"],
            "filename": chunk["filename"],
            "page_number": chunk["page_number"],
            "chunk_id": chunk["chunk_id"],
        })

    return {
        "sources": sources,
        "insufficient_context": False,
    }
