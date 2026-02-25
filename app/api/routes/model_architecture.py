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
VALID_MODULES = ["ORCHESTRATOR", "PLANNER", "PLAN_EXECUTOR", "PRESENTER", "STUDENT_AGENT", "RAG_AGENT", "ADMIN_AGENT", "PREDICT_AGENT"]

# Architecture description
ARCHITECTURE_DESCRIPTION = {
    "description": (
        "The Proactive Co-Teacher uses a multi-agent architecture with a central "
        "Orchestrator that coordinates four specialized agents. The Orchestrator "
        "delegates to planning services (ConversationService, ContextResolver, "
        "LLMPlanner) and execution services (PlanExecutor, Presenter). An LLM-based "
        "planner decomposes queries into typed steps, and PlanExecutor dispatches each "
        "step to the appropriate agent. All LLM calls are tracked via StepTracker and "
        "logged to Supabase for cost monitoring."
    ),
    "modules": {
        "note": "Module names match step_tracker.VALID_MODULES for consistency",
        "ORCHESTRATOR": (
            "Central coordinator that receives all requests. Manages the full pipeline: "
            "ConversationService (persistence), ContextResolver (context extraction), "
            "LLMPlanner (query decomposition into typed steps), PlanExecutor (step-by-step "
            "agent dispatch), and Presenter (voice transformation)."
        ),
        "PLANNER": (
            "LLM-based query decomposition layer. Receives the teacher's query and "
            "decomposes it into a typed execution plan (student_lookup, rag_search, "
            "admin_doc, predict steps). Each plan step is logged here."
        ),
        "STUDENT_AGENT": (
            "Manages student profiles. Retrieves and updates triggers, successful "
            "methods, failed methods, and learning styles. Detects implicit profile "
            "updates from teacher queries."
        ),
        "RAG_AGENT": (
            "Searches a teaching methods knowledge base using semantic search via "
            "Pinecone. Provides evidence-based strategy recommendations. Excludes "
            "methods that have failed for the specific student."
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
        "ConversationService": "Handles conversation CRUD and message persistence in Supabase",
        "ContextResolver": "Extracts context from conversation history, resolves student identity",
        "LLMPlanner": "Decomposes teacher queries into typed plan steps (student_lookup, rag_search, admin_doc, predict)",
        "PlanExecutor": "Executes plan steps sequentially, dispatching to appropriate agents and formatting results for Presenter",
        "Presenter": "Merges multi-agent results and applies voice transformation in a single LLM call (two tones: GROUNDING for crisis, STANDARD for normal)",
        "AgentExecutor": "Simple dispatch layer that routes to agents by AgentType"
    },
    "memory": {
        "Supabase (Short-term)": (
            "Students, conversations, messages, daily context, events, "
            "schedule templates, budget tracking, response cache, alerts, pending feedback"
        ),
        "Pinecone (Long-term)": (
            "Student profile embeddings (student-profiles namespace), "
            "teaching methods knowledge base (teaching-methods namespace), "
            "past intervention outcomes (interventions namespace)"
        )
    },
    "data_flow": [
        "1. Teacher sends query via POST /api/execute",
        "2. StepTracker initialized for request-scoped tracing",
        "3. ConversationService stores user message and retrieves history",
        "4. ContextResolver extracts conversation context (recent student, topic, etc.)",
        "5. LLMPlanner decomposes query into typed plan steps via LLM call",
        "6. PlanExecutor iterates plan steps, dispatching each to the appropriate agent",
        "7. For multi-step plans, Presenter merges agent results and applies voice in one LLM call",
        "8. Presenter applies voice transformation to the final response",
        "9. ConversationService stores assistant response",
        "10. All steps (with cost, tokens, timing) returned in response"
    ],
    "cost_optimizations": [
        "LLM-based planning decomposes complex queries into minimal agent calls",
        "Two-tier response caching (Supabase + in-memory) for RAG, Admin, and Predict queries",
        "Budget tracking with hard limits ($13 default) and async lock",
        "All LLM calls logged to Supabase budget_tracking for monitoring",
        "Lazy initialization of agents and services",
        "Optional presentation layer (can skip voice transformation)",
        "Rule-based risk calculation in PredictAgent (LLM only for detailed recommendations)"
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
