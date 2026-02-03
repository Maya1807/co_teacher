"""
Request schemas for API endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """Request body for POST /api/execute."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The teacher's query or request",
        examples=["What strategies work for ADHD students?"]
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation context",
        examples=["session_abc123"]
    )

    teacher_id: Optional[str] = Field(
        default=None,
        description="Teacher ID for personalization",
        examples=["T001"]
    )

    student_name: Optional[str] = Field(
        default=None,
        description="Optional student name if query is about a specific student",
        examples=["Alex Johnson"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "What are Alex's triggers and what strategies work for him?",
                "session_id": "session_123",
                "teacher_id": "T001",
                "student_name": "Alex"
            }
        }
