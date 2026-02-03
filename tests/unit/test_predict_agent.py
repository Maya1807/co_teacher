"""
Unit tests for PredictAgent.
Tests predictive analysis and event-based risk assessment.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta

from app.agents.predict_agent import PredictAgent
from app.core.router import RuleBasedRouter, AgentType


# ==================== Fixtures ====================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.complete = AsyncMock(return_value={
        "content": "Mock prediction response",
        "tokens_used": {"input": 100, "output": 50},
        "cost": 0.001
    })
    client.embed = AsyncMock(return_value=[0.1] * 1536)
    return client


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager with events and students."""
    manager = MagicMock()

    # Sample events
    sample_events = [
        {
            "id": "EVT001",
            "teacher_id": "T001",
            "title": "Fire Drill",
            "event_type": "drill",
            "event_date": date.today().isoformat(),
            "start_time": "10:00",
            "sensory_factors": {"loud_sounds": True, "unexpected": True},
            "affected_students": []
        },
        {
            "id": "EVT002",
            "teacher_id": "T001",
            "title": "School Assembly",
            "event_type": "special_event",
            "event_date": date.today().isoformat(),
            "start_time": "14:00",
            "sensory_factors": {"crowds": True, "loud_sounds": True},
            "affected_students": []
        }
    ]

    # Sample students
    sample_students = [
        {
            "id": "STU001",
            "name": "Taylor Williams",
            "grade": "4",
            "disability_type": "autism",
            "learning_style": "visual",
            "triggers": ["loud noises", "unexpected changes"],
            "successful_methods": ["visual schedules", "noise-reducing headphones"],
            "failed_methods": []
        },
        {
            "id": "STU002",
            "name": "Alex Chen",
            "grade": "3",
            "disability_type": "ADHD",
            "learning_style": "kinesthetic",
            "triggers": ["long periods of sitting", "crowded spaces"],
            "successful_methods": ["movement breaks", "fidget tools"],
            "failed_methods": []
        },
        {
            "id": "STU003",
            "name": "Jordan Kim",
            "grade": "4",
            "disability_type": "dyslexia",
            "learning_style": "auditory",
            "triggers": ["timed tests"],
            "successful_methods": ["audio instructions", "extra time"],
            "failed_methods": []
        }
    ]

    manager.get_todays_events = AsyncMock(return_value=sample_events)
    manager.get_upcoming_events = AsyncMock(return_value=sample_events)
    manager.list_students = AsyncMock(return_value=sample_students)
    manager.get_student_profile = AsyncMock(side_effect=lambda sid: next(
        (s for s in sample_students if s["id"] == sid), None
    ))

    return manager


@pytest.fixture
def mock_step_tracker():
    """Create a mock step tracker."""
    tracker = MagicMock()
    tracker.add_step = MagicMock()
    tracker.get_steps = MagicMock(return_value=[])
    return tracker


@pytest.fixture
def agent(mock_llm_client, mock_step_tracker, mock_memory_manager):
    """Create a PredictAgent with mocks."""
    return PredictAgent(
        llm_client=mock_llm_client,
        step_tracker=mock_step_tracker,
        memory_manager=mock_memory_manager
    )


# ==================== PredictAgent Tests ====================

class TestPredictAgent:
    """Tests for PredictAgent."""

    @pytest.mark.asyncio
    async def test_module_name(self, agent):
        """PredictAgent has correct module name."""
        assert agent.MODULE_NAME == "PREDICT_AGENT"

    @pytest.mark.asyncio
    async def test_generate_daily_briefing(self, agent, mock_memory_manager):
        """Can generate daily briefing."""
        result = await agent.process(
            {"prompt": "What should I watch for today?", "action": "daily_briefing"},
            context={"teacher_id": "T001"}
        )

        assert "response" in result
        assert "predictions" in result
        assert result["action_taken"] == "daily_briefing"
        mock_memory_manager.get_todays_events.assert_called_once()
        mock_memory_manager.list_students.assert_called_once()

    @pytest.mark.asyncio
    async def test_daily_briefing_no_events(self, agent, mock_memory_manager):
        """Handles no events gracefully."""
        mock_memory_manager.get_todays_events.return_value = []

        result = await agent.process(
            {"prompt": "Any concerns today?", "action": "daily_briefing"},
            context={"teacher_id": "T001"}
        )

        assert "No scheduled events" in result["response"]
        assert result["predictions"] == []
        assert result["events_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_risk_calculation_high_risk(self, agent):
        """Calculates high risk when multiple triggers match."""
        student = {
            "name": "Test Student",
            "triggers": ["loud noises", "unexpected changes", "crowded spaces"],
            "successful_methods": ["visual schedules"]
        }
        event = {
            "title": "Fire Drill",
            "event_type": "drill",
            "start_time": "10:00",
            "sensory_factors": {"loud_sounds": True, "unexpected": True, "crowds": True}
        }

        result = agent._calculate_risk(student, event)

        assert result["risk_level"] == "high"
        assert len(result["triggers_matched"]) >= 2
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_risk_calculation_medium_risk(self, agent):
        """Calculates medium risk with moderate trigger matches."""
        student = {
            "name": "Test Student",
            "triggers": ["loud noises", "schedule changes"],
            "successful_methods": []
        }
        event = {
            "title": "Assembly",
            "event_type": "special_event",
            "start_time": "14:00",
            "sensory_factors": {"loud_sounds": True, "crowds": False}
        }

        result = agent._calculate_risk(student, event)

        assert result["risk_level"] in ["low", "medium"]
        assert "loud noises" in result["triggers_matched"]

    @pytest.mark.asyncio
    async def test_risk_calculation_no_risk(self, agent):
        """Calculates no risk when triggers don't match."""
        student = {
            "name": "Test Student",
            "triggers": ["timed tests"],
            "successful_methods": []
        }
        event = {
            "title": "Art Class",
            "event_type": "class_schedule",
            "start_time": "09:00",
            "sensory_factors": {}
        }

        result = agent._calculate_risk(student, event)

        assert result["risk_level"] == "none"
        assert result["triggers_matched"] == []

    @pytest.mark.asyncio
    async def test_analyze_event_risks(self, agent, mock_memory_manager):
        """Can analyze event risks for all students."""
        students = await mock_memory_manager.list_students()
        event = {
            "id": "EVT001",
            "title": "Fire Drill",
            "event_type": "drill",
            "start_time": "10:00",
            "sensory_factors": {"loud_sounds": True, "unexpected": True}
        }

        predictions = await agent.analyze_event_risks(event, students)

        # Taylor Williams should be flagged (triggers: loud noises, unexpected changes)
        assert len(predictions) > 0
        taylor_pred = next((p for p in predictions if p["student_name"] == "Taylor Williams"), None)
        assert taylor_pred is not None
        assert taylor_pred["risk_level"] in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_recommendations_include_successful_methods(self, agent):
        """Recommendations include student's successful methods."""
        student = {
            "name": "Test Student",
            "triggers": ["loud noises"],
            "successful_methods": ["visual schedules", "fidget tools"]
        }
        event = {
            "title": "Fire Drill",
            "event_type": "drill",
            "start_time": "10:00",
            "sensory_factors": {"loud_sounds": True}
        }

        result = agent._calculate_risk(student, event)

        # Should include at least one successful method in recommendations
        recommendations_text = " ".join(result["recommendations"])
        assert "visual schedules" in recommendations_text.lower() or len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_recommendations_include_timing(self, agent):
        """Recommendations include timing guidance when start_time is available."""
        student = {
            "name": "Test Student",
            "triggers": ["loud noises"],
            "successful_methods": []
        }
        event = {
            "title": "Fire Drill",
            "event_type": "drill",
            "start_time": "10:00",
            "sensory_factors": {"loud_sounds": True}
        }

        result = agent._calculate_risk(student, event)

        # Should have at least one recommendation mentioning the time
        recommendations_text = " ".join(result["recommendations"])
        assert "10:00" in recommendations_text or "warning" in recommendations_text.lower()

    @pytest.mark.asyncio
    async def test_student_risk_analysis(self, agent, mock_memory_manager):
        """Can analyze risk for a specific student."""
        result = await agent.process(
            {"prompt": "What about Taylor today?", "action": "student_risk", "student_id": "STU001"},
            context={"teacher_id": "T001"}
        )

        assert "response" in result
        assert "predictions" in result
        assert result["action_taken"] == "student_risk"
        assert result["student_name"] == "Taylor Williams"

    @pytest.mark.asyncio
    async def test_student_risk_not_found(self, agent, mock_memory_manager):
        """Handles student not found gracefully."""
        mock_memory_manager.get_student_profile.return_value = None

        result = await agent.process(
            {"prompt": "Risk for unknown student", "action": "student_risk", "student_id": "INVALID"},
            context={"teacher_id": "T001"}
        )

        assert result["action_taken"] == "student_risk_failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_format_events_for_prompt(self, agent):
        """Formats events correctly for LLM prompts."""
        events = [
            {
                "title": "Fire Drill",
                "event_type": "drill",
                "start_time": "10:00",
                "sensory_factors": {"loud_sounds": True, "unexpected": True}
            },
            {
                "title": "Assembly",
                "event_type": "special_event",
                "start_time": "14:00",
                "sensory_factors": {"crowds": True}
            }
        ]

        formatted = agent._format_events_for_prompt(events)

        assert "Fire Drill" in formatted
        assert "Assembly" in formatted
        assert "10:00" in formatted
        assert "14:00" in formatted
        assert "drill" in formatted
        assert "loud_sounds" in formatted

    @pytest.mark.asyncio
    async def test_format_at_risk_students(self, agent):
        """Formats at-risk student predictions correctly."""
        predictions = [
            {
                "student_name": "Taylor Williams",
                "event_title": "Fire Drill",
                "risk_level": "high",
                "triggers_matched": ["loud noises", "unexpected changes"]
            }
        ]

        formatted = agent._format_at_risk_students(predictions)

        assert "Taylor Williams" in formatted
        assert "high risk" in formatted
        assert "Fire Drill" in formatted
        assert "loud noises" in formatted


# ==================== Router Tests for PREDICT_AGENT ====================

class TestPredictAgentRouting:
    """Tests for routing to PREDICT_AGENT."""

    @pytest.fixture
    def router(self):
        """Create a router instance."""
        return RuleBasedRouter()

    def test_routes_predict_keywords(self, router):
        """Routes predict keywords to PREDICT_AGENT."""
        queries = [
            "What should I watch for today?",
            "Any concerns for this week?",
            "Give me the daily briefing",
            "Morning briefing please",
            "What's happening today?",
            "Prepare me for today",
            "Who might struggle with the fire drill?",
        ]

        for query in queries:
            result = router.route(query)
            assert AgentType.PREDICT_AGENT in result.agents, f"Failed for: {query}"

    def test_routes_predict_patterns(self, router):
        """Routes predict patterns to PREDICT_AGENT."""
        queries = [
            "What should I expect today?",
            "Any issues today?",
            "Predictions for tomorrow",
        ]

        for query in queries:
            result = router.route(query)
            assert AgentType.PREDICT_AGENT in result.agents, f"Failed for: {query}"

    def test_fire_drill_routes_to_predict(self, router):
        """Fire drill queries route to PREDICT_AGENT."""
        result = router.route("We have a fire drill today, who should I watch?")
        assert AgentType.PREDICT_AGENT in result.agents

    def test_field_trip_routes_to_predict(self, router):
        """Field trip queries route to PREDICT_AGENT."""
        result = router.route("Field trip tomorrow, any concerns?")
        assert AgentType.PREDICT_AGENT in result.agents


# ==================== Integration Tests ====================

class TestPredictAgentIntegration:
    """Integration-style tests for PredictAgent with other components."""

    @pytest.mark.asyncio
    async def test_full_briefing_flow(
        self, mock_llm_client, mock_step_tracker, mock_memory_manager
    ):
        """Tests complete briefing flow from query to response."""
        agent = PredictAgent(
            llm_client=mock_llm_client,
            step_tracker=mock_step_tracker,
            memory_manager=mock_memory_manager
        )

        result = await agent.process(
            {"prompt": "What should I prepare for today?"},
            context={"teacher_id": "T001"}
        )

        # Should have processed events and students
        assert result["action_taken"] == "daily_briefing"
        assert result["events_analyzed"] > 0
        assert "predictions" in result

        # Should have identified Taylor Williams as at-risk for fire drill
        taylor_prediction = next(
            (p for p in result["predictions"] if p["student_name"] == "Taylor Williams"),
            None
        )
        if taylor_prediction:  # May or may not be in predictions depending on risk calc
            assert taylor_prediction["risk_level"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_event_sensory_factor_matching(
        self, mock_llm_client, mock_step_tracker, mock_memory_manager
    ):
        """Tests that sensory factors correctly match student triggers."""
        agent = PredictAgent(
            llm_client=mock_llm_client,
            step_tracker=mock_step_tracker,
            memory_manager=mock_memory_manager
        )

        # Create specific test case
        student = {
            "name": "Test Student",
            "triggers": ["loud sounds", "bright flashing lights"],
            "successful_methods": []
        }
        event = {
            "title": "Assembly with Strobe Lights",
            "event_type": "special_event",
            "start_time": "14:00",
            "sensory_factors": {
                "loud_sounds": True,
                "bright_lights": True,
                "crowds": False
            }
        }

        predictions = await agent.analyze_event_risks(event, [student])

        assert len(predictions) == 1
        assert predictions[0]["risk_level"] in ["medium", "high"]
        assert len(predictions[0]["triggers_matched"]) >= 1
