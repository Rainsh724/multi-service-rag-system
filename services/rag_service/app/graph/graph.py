
from langgraph.graph import END, START, StateGraph

from services.rag_service.app.graph.nodes import (
    answer_generation,
    context_evaluation,
    query_processing,
    response_formatting,
    retrieval,
)
from services.rag_service.app.graph.state import RAGState


def route_after_evaluation(state: RAGState) -> str:
    if state.get("is_context_sufficient", False):
        return "answer_generation"

    return "response_formatting"


def build_graph():
    builder = StateGraph(RAGState)

    builder.add_node("query_processing", query_processing)
    builder.add_node("retrieval", retrieval)
    builder.add_node("context_evaluation", context_evaluation)
    builder.add_node("answer_generation", answer_generation)
    builder.add_node("response_formatting", response_formatting)

    builder.add_edge(START, "query_processing")
    builder.add_edge("query_processing", "retrieval")
    builder.add_edge("retrieval", "context_evaluation")

    builder.add_conditional_edges(
        "context_evaluation",
        route_after_evaluation,
        {
            "answer_generation": "answer_generation",
            "response_formatting": "response_formatting",
        },
    )

    builder.add_edge("answer_generation", "response_formatting")
    builder.add_edge("response_formatting", END)

    return builder.compile()


rag_graph = build_graph()
