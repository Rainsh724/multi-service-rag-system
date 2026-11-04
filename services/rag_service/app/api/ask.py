
from fastapi import APIRouter, HTTPException

from services.rag_service.app.graph.graph import rag_graph
from shared.schemas.rag import RAGRequest, RAGResponse


router = APIRouter()


@router.post("/ask/", response_model=RAGResponse)
async def ask_question(request: RAGRequest):
    initial_state = {
        "question": request.question,
        "document_ids": (
            [str(document_id) for document_id in request.document_ids]
            if request.document_ids
            else None
        ),
        "top_k": request.top_k,
    }

    try:
        result = await rag_graph.ainvoke(initial_state)

        return RAGResponse(
            question=request.question,
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            insufficient_context=result.get(
                "insufficient_context",
                False,
            ),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="RAG pipeline execution failed.",
        ) from exc
