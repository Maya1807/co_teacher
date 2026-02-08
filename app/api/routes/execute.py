"""
POST /api/execute endpoint.
Main entry point for agent execution.
"""
import uuid
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

from app.api.schemas.requests import ExecuteRequest
from app.api.schemas.responses import ExecuteResponse, StepInfo
from app.agents.orchestrator import Orchestrator
from app.core.step_tracker import reset_step_tracker
from app.core.llm_client import get_llm_client

router = APIRouter()


@router.post("/execute", response_model=ExecuteResponse)
async def execute_agent(request: ExecuteRequest):
    """
    Main entry point for agent execution.

    User sends an input prompt, API returns response + traced steps.

    The system:
    1. Routes the query to appropriate agent(s)
    2. Processes through the agent pipeline
    3. Returns the response with all processing steps traced

    Args:
        request: ExecuteRequest with query and optional context

    Returns:
        ExecuteResponse with status, response text, and steps array
    """
    # --- 1. Input validation ---
    # Guard against empty/whitespace-only prompts before doing any real work.
    if not request.prompt or not request.prompt.strip():
        return ExecuteResponse(
            status="error",
            error="Query cannot be empty",
            response="",
            steps=[]
        )

    try:
        # --- 2. Fresh step tracker ---
        # Each request gets its own StepTracker so the traced steps
        # (routing decisions, LLM calls, memory lookups) don't leak
        # between concurrent requests.
        tracker = reset_step_tracker()

        # --- 3. Create the orchestrator ---
        # The orchestrator is the central coordinator: it receives the
        # teacher's query, uses the RuleBasedRouter to pick the right
        # agent (StudentAgent / RAGAgent / AdminAgent), and returns
        # the combined result. Sub-agents are lazily initialised inside.
        orchestrator = Orchestrator(
            step_tracker=tracker
        )

        # --- 4. Build context dict ---
        # Optional session/teacher IDs that let agents personalise
        # responses and maintain conversation continuity in Supabase.
        context = {}
        if request.session_id:
            context["session_id"] = request.session_id
        if request.teacher_id:
            context["teacher_id"] = request.teacher_id

        # --- 5. Build input_data for the orchestrator ---
        # This is the payload the orchestrator.process() expects.
        # A session_id is always required; generate one if the client
        # didn't supply it so memory lookups still work.
        input_data = {
            "prompt": request.prompt.strip(),
            "session_id": request.session_id or f"session_{uuid.uuid4().hex[:8]}"
        }

        # If the client already knows which student the query is about,
        # pass it explicitly so the router can skip name-extraction.
        if request.student_name:
            input_data["student_name"] = request.student_name

        # --- 6. Run the multi-agent pipeline ---
        # This is where the actual work happens:
        #   Router decides agent(s) -> agent(s) query memory + LLM -> response
        # All intermediate steps are recorded in the tracker automatically.
        result = await orchestrator.process(input_data, context)

        # --- 7. Collect traced steps ---
        # Convert the raw step dicts from the tracker into StepInfo
        # response objects so the frontend can render the trace sidebar.
        steps = [
            StepInfo(
                module=step["module"],
                prompt=step["prompt"],
                response=step["response"]
            )
            for step in tracker.get_steps()
        ]

        # --- 8. Detect student profile updates ---
        # If an agent updated a student profile (e.g. new trigger added),
        # surface the student name so the frontend can refresh the
        # class sidebar to reflect the change.
        student_updated = None
        if result.get("updates_applied"):
            student_updated = result.get("student_name")
            print(f"[DEBUG] Execute endpoint: student_updated={student_updated}, updates={result.get('updates_applied')}")

        # --- 9. Return the final response ---
        return ExecuteResponse(
            status="ok",
            error=None,
            response=result.get("response", ""),
            steps=steps,
            student_updated=student_updated
        )

    except Exception as e:
        # --- Error handling ---
        # Catch-all so the client always gets a valid JSON response
        # instead of a raw 500 error. The traceback is printed
        # server-side for debugging.
        import traceback
        traceback.print_exc()

        return ExecuteResponse(
            status="error",
            error=str(e),
            response="An error occurred while processing your request.",
            steps=[]
        )


@router.get("/execute/budget")
async def get_budget_status():
    """
    Get current LLM budget status.

    Returns:
        Dict with budget information
    """
    try:
        llm = get_llm_client()
        return llm.get_budget_status()
    except Exception as e:
        return {
            "error": str(e),
            "total_cost": 0,
            "budget_limit": 13.00,
            "remaining": 13.00
        }


@router.get("/execute/health")
async def health_check():
    """
    Simple health check endpoint.

    Returns:
        Dict with health status
    """
    return {
        "status": "healthy",
        "service": "co-teacher-api",
        "version": "1.0.0"
    }
