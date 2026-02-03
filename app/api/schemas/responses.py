"""
Response schemas for API endpoints.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==================== Team Info ====================

class StudentInfo(BaseModel):
    """Student/team member information."""
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")


class TeamInfoResponse(BaseModel):
    """Response for GET /api/team_info."""
    group_batch_order_number: str = Field(
        ...,
        description="Group batch order number",
        examples=["batch_1_order_9"]
    )
    team_name: str = Field(
        ...,
        description="Team name",
        examples=["avi_yehoraz_maya"]
    )
    students: List[StudentInfo] = Field(
        ...,
        description="List of team members"
    )


# ==================== Agent Info ====================

class AgentInfo(BaseModel):
    """Information about a single agent."""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="What the agent does")
    capabilities: List[str] = Field(..., description="List of capabilities")


class AgentInfoResponse(BaseModel):
    """Response for GET /api/agent_info."""
    agents: List[AgentInfo] = Field(..., description="List of all agents")
    total_agents: int = Field(..., description="Total number of agents")


# ==================== Model Architecture ====================

class ModelArchitectureResponse(BaseModel):
    """Response for GET /api/model_architecture."""
    architecture_diagram_url: str = Field(
        ...,
        description="URL to architecture diagram image"
    )
    description: str = Field(
        ...,
        description="Text description of the architecture"
    )
    components: Dict[str, str] = Field(
        ...,
        description="Map of component names to descriptions"
    )
    data_flow: List[str] = Field(
        ...,
        description="Description of data flow between components"
    )


# ==================== Execute ====================

class StepInfo(BaseModel):
    """Information about a single processing step."""
    module: str = Field(
        ...,
        description="Module that processed this step",
        examples=["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT", "ADMIN_AGENT"]
    )
    prompt: Dict[str, Any] = Field(
        ...,
        description="Summary of the prompt/input for this step"
    )
    response: Dict[str, Any] = Field(
        ...,
        description="Summary of the response/output for this step"
    )


class ExecuteResponse(BaseModel):
    """Response for POST /api/execute."""
    status: str = Field(
        ...,
        description="Status of the request",
        examples=["ok", "error"]
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if status is 'error'"
    )
    response: str = Field(
        ...,
        description="The main response text"
    )
    steps: List[StepInfo] = Field(
        ...,
        description="List of processing steps taken"
    )
    student_updated: Optional[str] = Field(
        default=None,
        description="Name of student whose profile was updated, if any"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "error": None,
                "response": "Based on Alex's profile, here are some strategies...",
                "steps": [
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {"action": "route_query", "query": "..."},
                        "response": {"routed_to": "STUDENT_AGENT", "confidence": 0.9}
                    },
                    {
                        "module": "STUDENT_AGENT",
                        "prompt": {"action": "profile_query", "student": "Alex"},
                        "response": {"found": True, "content": "..."}
                    }
                ]
            }
        }


# ==================== Error ====================

class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = Field(default="error", description="Always 'error'")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional details")
