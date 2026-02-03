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
    # Validate input
    if not request.prompt or not request.prompt.strip():
        return ExecuteResponse(
            status="error",
            error="Query cannot be empty",
            response="",
            steps=[]
        )

    try:
        # Reset step tracker for new request
        tracker = reset_step_tracker()

        # Create orchestrator with fresh tracker
        orchestrator = Orchestrator(
            step_tracker=tracker
        )

        # Build context from request
        context = {}
        if request.session_id:
            context["session_id"] = request.session_id
        if request.teacher_id:
            context["teacher_id"] = request.teacher_id

        # Build input data
        input_data = {
            "prompt": request.prompt.strip(),
            "session_id": request.session_id or f"session_{uuid.uuid4().hex[:8]}"
        }

        if request.student_name:
            input_data["student_name"] = request.student_name

        # Process through orchestrator
        result = await orchestrator.process(input_data, context)

        # Get steps from tracker
        steps = [
            StepInfo(
                module=step["module"],
                prompt=step["prompt"],
                response=step["response"]
            )
            for step in tracker.get_steps()
        ]

        # Check if a student was updated
        student_updated = None
        if result.get("updates_applied"):
            student_updated = result.get("student_name")
            print(f"[DEBUG] Execute endpoint: student_updated={student_updated}, updates={result.get('updates_applied')}")

        return ExecuteResponse(
            status="ok",
            error=None,
            response=result.get("response", ""),
            steps=steps,
            student_updated=student_updated
        )

    except Exception as e:
        # Log the error (in production, use proper logging)
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
