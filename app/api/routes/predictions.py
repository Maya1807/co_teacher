"""
Predictions API endpoints.
Provides daily predictions for the frontend sidebar.
"""
import json
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.memory.memory_manager import get_memory_manager
from app.agents.predict_agent import PredictAgent
from app.core.llm_client import get_llm_client
from app.core.step_tracker import get_step_tracker
from app.core.cache import get_cache, ResponseCache

router = APIRouter()


class PredictionItem(BaseModel):
    """A single prediction for a student-event pair."""
    student_id: str
    student_name: str
    event_id: Optional[str] = None
    event_title: str
    event_time: Optional[str] = None
    risk_level: str  # "low", "medium", "high"
    triggers_matched: List[str]
    recommendations: List[str]


class EventItem(BaseModel):
    """An event for the day."""
    id: str
    title: str
    event_type: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    sensory_factors: dict = {}


class DailyPredictionsResponse(BaseModel):
    """Response for daily predictions endpoint."""
    date: str
    events: List[EventItem]
    predictions: List[PredictionItem]
    has_concerns: bool
    summary: Optional[str] = None
    from_cache: bool = False


@router.get("/predictions/today", response_model=DailyPredictionsResponse)
async def get_todays_predictions(
    teacher_id: str = Query("default", description="Teacher ID"),
    refresh: bool = Query(False, description="Force refresh, bypass cache")
):
    """
    Get predictions for today's events.

    Returns events scheduled for today and predictions for students
    who may be affected based on their triggers.
    """
    cache = get_cache()
    today = date.today().isoformat()
    cache_key = f"predictions_{teacher_id}_{today}"

    # Check cache unless refresh requested
    if not refresh:
        cached = await cache.get(cache_key, "PREDICT_AGENT")
        if cached:
            try:
                data = json.loads(cached)
                data["from_cache"] = True
                return DailyPredictionsResponse(**data)
            except (json.JSONDecodeError, TypeError):
                pass  # Cache corrupted, regenerate

    memory = get_memory_manager()

    # Get today's events (handle case where events table doesn't exist yet)
    try:
        events = await memory.get_todays_events(teacher_id)
    except Exception as e:
        print(f"Warning: Could not fetch events: {e}")
        events = []

    # Get all students
    try:
        students = await memory.list_students(limit=50)
    except Exception as e:
        print(f"Warning: Could not fetch students: {e}")
        students = []

    # Create predict agent to analyze risks
    predict_agent = PredictAgent(
        llm_client=get_llm_client(),
        step_tracker=get_step_tracker(),
        memory_manager=memory
    )

    # Collect predictions
    all_predictions = []
    for event in events:
        event_predictions = await predict_agent.analyze_event_risks(event, students)
        all_predictions.extend(event_predictions)

    # Sort by risk level (high first)
    risk_order = {"high": 0, "medium": 1, "low": 2}
    all_predictions.sort(key=lambda p: risk_order.get(p.get("risk_level", "low"), 2))

    # Format events
    event_items = [
        EventItem(
            id=e.get("id", ""),
            title=e.get("title", ""),
            event_type=e.get("event_type", ""),
            start_time=e.get("start_time"),
            end_time=e.get("end_time"),
            sensory_factors=e.get("sensory_factors", {})
        )
        for e in events
    ]

    # Format predictions
    prediction_items = [
        PredictionItem(
            student_id=p.get("student_id", ""),
            student_name=p.get("student_name", ""),
            event_id=p.get("event_id"),
            event_title=p.get("event_title", ""),
            event_time=p.get("event_time"),
            risk_level=p.get("risk_level", "low"),
            triggers_matched=p.get("triggers_matched", []),
            recommendations=p.get("recommendations", [])
        )
        for p in all_predictions
    ]

    # Determine if there are any concerns
    has_concerns = any(p.risk_level in ["medium", "high"] for p in prediction_items)

    # Generate a brief summary
    summary = None
    if has_concerns:
        high_risk = [p for p in prediction_items if p.risk_level == "high"]
        medium_risk = [p for p in prediction_items if p.risk_level == "medium"]
        if high_risk:
            summary = f"{len(high_risk)} high-risk situation(s) to prepare for"
        elif medium_risk:
            summary = f"{len(medium_risk)} student(s) may need extra support"
    elif events:
        summary = "No significant concerns for today's events"
    else:
        summary = "No events scheduled for today"

    # Build response data
    response_data = {
        "date": today,
        "events": [e.model_dump() for e in event_items],
        "predictions": [p.model_dump() for p in prediction_items],
        "has_concerns": has_concerns,
        "summary": summary,
        "from_cache": False
    }

    # Cache the result (expires at midnight)
    ttl_hours = ResponseCache.get_hours_until_midnight()
    await cache.set(cache_key, json.dumps(response_data), "PREDICT_AGENT", ttl_hours)

    return DailyPredictionsResponse(**response_data)
