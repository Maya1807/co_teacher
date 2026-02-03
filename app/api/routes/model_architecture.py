"""
GET /api/model_architecture endpoint.
Returns the architecture diagram and description.
"""
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
import os

router = APIRouter()

# Module names must match step_tracker.VALID_MODULES
VALID_MODULES = ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT", "ADMIN_AGENT", "PREDICT_AGENT"]

# Architecture description
ARCHITECTURE_DESCRIPTION = {
    "description": (
        "The Proactive Co-Teacher uses a multi-agent architecture with a central "
        "Orchestrator that coordinates four specialized agents. The Orchestrator "
        "delegates to internal services: ConversationService, ContextResolver, "
        "Router, AgentExecutor, ResponseCombiner, and Presenter. The system uses "
        "rule-based routing to minimize LLM costs, falling back to LLM routing "
        "only when needed."
    ),
    "modules": {
        "note": "Module names match step_tracker.VALID_MODULES for consistency",
        "ORCHESTRATOR": (
            "Central coordinator that receives all requests. Delegates to internal "
            "services: ConversationService (persistence), ContextResolver (context "
            "extraction), Router (query routing), AgentExecutor (agent dispatch), "
            "ResponseCombiner (multi-agent synthesis), and Presenter (voice transformation)."
        ),
        "STUDENT_AGENT": (
            "Manages student profiles. Retrieves and updates triggers, successful "
            "methods, failed methods, and learning styles. Detects implicit profile "
            "updates from teacher queries."
        ),
        "RAG_AGENT": (
            "Searches a teaching methods knowledge base using semantic search. "
            "Provides evidence-based strategy recommendations. Excludes methods "
            "that have failed for the specific student."
        ),
        "ADMIN_AGENT": (
            "Generates administrative documents including IEP reports, parent "
            "communications, daily/weekly summaries, and incident reports."
        ),
        "PREDICT_AGENT": (
            "Provides daily briefings and predictive risk analysis. Matches "
            "scheduled events against student triggers to identify potential issues."
        )
    },
    "services": {
        "ConversationService": "Handles conversation CRUD and message storage",
        "ContextResolver": "Extracts context from history, resolves student identity",
        "Router": "Rule-based routing with LLM fallback for ambiguous queries",
        "AgentExecutor": "Simple dispatch to appropriate agents",
        "ResponseCombiner": "Synthesizes multi-agent responses for personalized queries",
        "Presenter": "Optional voice transformation for user-facing responses"
    },
    "memory": {
        "Supabase (Short-term)": (
            "Conversations, messages, daily context, response cache, student records"
        ),
        "Pinecone (Long-term)": (
            "Student profile embeddings, teaching methods knowledge base, interventions"
        )
    },
    "data_flow": [
        "1. Teacher sends query via POST /api/execute",
        "2. ConversationService stores user message and retrieves history",
        "3. ContextResolver extracts conversation context (recent student, etc.)",
        "4. Router matches patterns/keywords to determine target agent(s)",
        "5. If low confidence, Router uses LLM for routing decision",
        "6. For single-agent: AgentExecutor dispatches to appropriate agent",
        "7. For multi-agent: ResponseCombiner synthesizes personalized response",
        "8. Presenter applies voice transformation (optional)",
        "9. All steps logged to StepTracker and returned in response"
    ],
    "cost_optimizations": [
        "Rule-based routing saves ~40% of LLM routing calls",
        "Response caching for RAG and Admin queries",
        "Optional presentation layer (can skip voice transformation)",
        "Budget tracking with hard limits ($13 default)",
        "Lazy initialization of agents and services"
    ],
    "diagram_source": "/static/architecture.mmd"
}


@router.get("/model_architecture")
async def get_model_architecture(
    format: Optional[str] = Query(
        default="image",
        description="Response format: 'json' for metadata, 'image' for PNG"
    )
):
    """
    Returns the architecture diagram and/or description.

    Args:
        format: 'image' returns PNG file (default), 'json' returns metadata

    Returns:
        PNG image or JSON with architecture details
    """
    if format == "json":
        # Return JSON metadata
        return {
            "architecture_diagram_url": "/static/architecture.png",
            **ARCHITECTURE_DESCRIPTION
        }

    # Default: return the PNG image
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
    architecture_path = os.path.join(static_dir, "architecture.png")

    if os.path.exists(architecture_path):
        return FileResponse(
            architecture_path,
            media_type="image/png",
            filename="architecture.png"
        )
    else:
        return JSONResponse(
            status_code=404,
            content={
                "error": "Architecture diagram not found",
                "hint": "Add static/architecture.png or use format=json"
            }
        )


@router.get("/model_architecture/image")
async def get_model_architecture_image():
    """
    Returns the architecture diagram as PNG image.

    Returns:
        PNG image file or 404 error
    """
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
    architecture_path = os.path.join(static_dir, "architecture.png")

    if os.path.exists(architecture_path):
        return FileResponse(
            architecture_path,
            media_type="image/png",
            filename="architecture.png"
        )

    return JSONResponse(
        status_code=404,
        content={"error": "Architecture diagram not found. Please add static/architecture.png"}
    )
