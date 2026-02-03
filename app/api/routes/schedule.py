"""
Schedule API endpoints.
Provides today's schedule for the frontend sidebar.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.memory.memory_manager import get_memory_manager

router = APIRouter()


class ScheduleEvent(BaseModel):
    """A single event in the schedule."""
    id: str
    title: str
    event_type: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    is_recurring: bool = False
    from_template: bool = False
    sensory_factors: dict = {}
    metadata: dict = {}


class TodayScheduleResponse(BaseModel):
    """Response for today's schedule endpoint."""
    date: str
    events: List[ScheduleEvent]
    event_count: int


@router.get("/schedule/today", response_model=TodayScheduleResponse)
async def get_todays_schedule(
    teacher_id: str = Query("default", description="Teacher ID")
):
    """
    Get today's schedule for a teacher.

    Combines recurring events from schedule_templates with
    one-off events from the events table.
    """
    memory = get_memory_manager()

    try:
        events = await memory.get_todays_events(teacher_id)
    except Exception as e:
        print(f"Warning: Could not fetch schedule: {e}")
        events = []

    # Format events for response
    schedule_events = [
        ScheduleEvent(
            id=e.get("id", ""),
            title=e.get("title", ""),
            event_type=e.get("event_type", "class_schedule"),
            start_time=e.get("start_time"),
            end_time=e.get("end_time"),
            description=e.get("description"),
            is_recurring=e.get("is_recurring", False),
            from_template=e.get("from_template", False),
            sensory_factors=e.get("sensory_factors") or {},
            metadata=e.get("metadata") or {}
        )
        for e in events
    ]

    # Sort by start time
    schedule_events.sort(key=lambda e: e.start_time or "00:00")

    return TodayScheduleResponse(
        date=date.today().isoformat(),
        events=schedule_events,
        event_count=len(schedule_events)
    )
