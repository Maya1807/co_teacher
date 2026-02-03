"""
Unit tests for ResponseCombiner.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

from app.services.response_combiner import ResponseCombiner, CombinedResult
from app.core.router import AgentType


@dataclass
class MockRoutingResult:
    """Mock RoutingResult for testing."""
    agents: List[AgentType]
    confidence: float = 0.9
    extracted_entities: Dict[str, Any] = None

    def __post_init__(self):
        if self.extracted_entities is None:
            self.extracted_entities = {}

    @property
    def is_multi_agent(self) -> bool:
        return len(self.agents) > 1


class TestResponseCombiner:
    """Tests for ResponseCombiner."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.complete = AsyncMock(return_value={
            "content": "Synthesized response about strategies",
            "tokens_used": {"input": 200, "output": 100}
        })
        return client

    @pytest.fixture
    def mock_tracker(self):
        """Create mock step tracker."""
        tracker = MagicMock()
        tracker.add_step = MagicMock()
        return tracker

    @pytest.fixture
    def mock_student_agent(self):
        """Create mock student agent."""
        agent = MagicMock()
        agent.process = AsyncMock(return_value={
            "response": "Student info retrieved",
            "student_profile": {"name": "Alex", "disability_type": "autism"},
            "action_taken": "profile_retrieved",
            "updates_applied": None
        })
        return agent

    @pytest.fixture
    def mock_rag_agent(self):
        """Create mock RAG agent."""
        agent = MagicMock()
        agent.get_relevant_methods = AsyncMock(return_value={
            "methods": [{"method_name": "Visual Schedules"}],
            "methods_summary": "Visual Schedules: Use visual cues..."
        })
        return agent

    @pytest.fixture
    def mock_presenter(self):
        """Create mock presenter."""
        presenter = MagicMock()
        presenter.present = AsyncMock(return_value="Presented response with voice")
        return presenter

    @pytest.fixture
    def combiner(self, mock_llm_client, mock_tracker, mock_student_agent, mock_rag_agent, mock_presenter):
        """Create ResponseCombiner with all mocks."""
        return ResponseCombiner(
            llm_client=mock_llm_client,
            step_tracker=mock_tracker,
            student_agent=mock_student_agent,
            rag_agent=mock_rag_agent,
            presenter=mock_presenter
        )

    @pytest.fixture
    def student_context(self):
        """Sample student context."""
        return {
            "student_id": "STU001",
            "name": "Alex Johnson",
            "profile": {
                "name": "Alex Johnson",
                "disability_type": "autism",
                "learning_style": "visual",
                "triggers": ["loud noises", "schedule changes"],
                "successful_methods": ["visual schedules", "fidget tools"],
                "failed_methods": ["group work without support"]
            }
        }

    @pytest.mark.asyncio
    async def test_combine_personalized_response_basic(self, combiner, student_context, mock_presenter):
        """Test basic multi-agent synthesis."""
        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT]
        )

        result = await combiner.combine_personalized_response(
            query="What strategies work for Alex?",
            routing_result=routing,
            student_context=student_context
        )

        assert isinstance(result, CombinedResult)
        assert result.response == "Presented response with voice"
        assert result.student_name == "Alex Johnson"
        mock_presenter.present.assert_called_once()

    @pytest.mark.asyncio
    async def test_combine_calls_student_agent(self, combiner, student_context, mock_student_agent):
        """Test that student agent is called when in routing."""
        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT]
        )

        await combiner.combine_personalized_response(
            query="What strategies work for Alex?",
            routing_result=routing,
            student_context=student_context
        )

        mock_student_agent.process.assert_called_once()
        call_args = mock_student_agent.process.call_args[0][0]
        assert call_args["student_id"] == "STU001"

    @pytest.mark.asyncio
    async def test_combine_calls_rag_agent(self, combiner, student_context, mock_rag_agent):
        """Test that RAG agent is called when in routing."""
        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT]
        )

        await combiner.combine_personalized_response(
            query="What strategies work for Alex?",
            routing_result=routing,
            student_context=student_context
        )

        mock_rag_agent.get_relevant_methods.assert_called_once()
        call_args = mock_rag_agent.get_relevant_methods.call_args
        assert call_args.kwargs["query"] == "What strategies work for Alex?"

    @pytest.mark.asyncio
    async def test_combine_skips_student_agent_when_not_in_routing(self, combiner, student_context, mock_student_agent):
        """Test student agent is skipped when not in routing."""
        routing = MockRoutingResult(
            agents=[AgentType.RAG_AGENT]  # No STUDENT_AGENT
        )

        await combiner.combine_personalized_response(
            query="General autism strategies?",
            routing_result=routing,
            student_context=student_context
        )

        mock_student_agent.process.assert_not_called()

    @pytest.mark.asyncio
    async def test_combine_handles_updates_applied(self, combiner, student_context, mock_student_agent, mock_presenter):
        """Test handling when student agent applies updates."""
        mock_student_agent.process.return_value = {
            "response": "Got it, I've noted that Alex has a new trigger.",
            "student_profile": {"name": "Alex Johnson"},
            "action_taken": "update_applied",
            "updates_applied": {"triggers": ["loud noises", "bright lights"]}
        }

        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT]
        )

        result = await combiner.combine_personalized_response(
            query="Alex has a new trigger - bright lights. What can help?",
            routing_result=routing,
            student_context=student_context
        )

        # Updates should be in result
        assert result.updates_applied is not None
        # Confirmation should be prepended
        assert "Got it" in result.response

    @pytest.mark.asyncio
    async def test_combine_returns_early_for_info_sharing(self, combiner, student_context, mock_student_agent, mock_llm_client):
        """Test that info-sharing (no question) returns just confirmation."""
        mock_student_agent.process.return_value = {
            "response": "Got it, I've updated Alex's triggers.",
            "action_taken": "update_applied",
            "updates_applied": {"triggers": ["bright lights"]}
        }

        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT]
        )

        result = await combiner.combine_personalized_response(
            query="Alex has a trigger with bright lights",  # No question mark
            routing_result=routing,
            student_context=student_context
        )

        # Should return just the confirmation without synthesis
        assert result.response == "Got it, I've updated Alex's triggers."
        # LLM should not be called for synthesis
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_combine_returns_early_for_already_exists(self, combiner, student_context, mock_student_agent, mock_llm_client):
        """Test that 'already exists' action returns early."""
        mock_student_agent.process.return_value = {
            "response": "That trigger is already in Alex's profile.",
            "action_taken": "already_exists",
            "updates_applied": None
        }

        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT]
        )

        result = await combiner.combine_personalized_response(
            query="Alex has a trigger with loud noises",
            routing_result=routing,
            student_context=student_context
        )

        assert result.response == "That trigger is already in Alex's profile."
        assert result.updates_applied is None
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_combine_tracks_step(self, combiner, student_context, mock_tracker):
        """Test that synthesis step is tracked."""
        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT]
        )

        await combiner.combine_personalized_response(
            query="What strategies work for Alex?",
            routing_result=routing,
            student_context=student_context
        )

        mock_tracker.add_step.assert_called()
        call_args = mock_tracker.add_step.call_args
        assert call_args.kwargs["module"] == "ORCHESTRATOR"
        assert call_args.kwargs["prompt"]["action"] == "synthesize_personalized_content"

    def test_format_student_summary(self, combiner):
        """Test _format_student_summary method."""
        profile = {
            "disability_type": "autism",
            "learning_style": "visual",
            "triggers": ["loud noises", "changes"],
            "successful_methods": ["visual schedules", "fidgets", "breaks"],
            "failed_methods": ["group work"]
        }

        summary = combiner._format_student_summary(profile)

        assert "autism" in summary
        assert "visual learner" in summary
        assert "loud noises" in summary
        assert "visual schedules" in summary
        assert "group work" in summary

    def test_format_student_summary_empty_profile(self, combiner):
        """Test _format_student_summary with empty profile."""
        summary = combiner._format_student_summary({})
        assert summary == "No profile available"

    def test_format_student_summary_limits_items(self, combiner):
        """Test that summary limits list items."""
        profile = {
            "successful_methods": ["m1", "m2", "m3", "m4", "m5"],  # 5 methods
            "triggers": ["t1", "t2", "t3", "t4"]  # 4 triggers
        }

        summary = combiner._format_student_summary(profile)

        # Should only include top 3 methods and top 2 triggers
        assert "m1" in summary
        assert "m3" in summary
        assert "m4" not in summary  # Should be excluded
        assert "t1" in summary
        assert "t2" in summary
        assert "t3" not in summary  # Should be excluded

    def test_is_asking_question_with_mark(self, combiner):
        """Test _is_asking_question with question mark."""
        assert combiner._is_asking_question("What works for Alex?") is True

    def test_is_asking_question_with_how(self, combiner):
        """Test _is_asking_question starting with 'how'."""
        assert combiner._is_asking_question("How can I help Alex") is True

    def test_is_asking_question_with_what(self, combiner):
        """Test _is_asking_question starting with 'what'."""
        assert combiner._is_asking_question("What strategies work") is True

    def test_is_asking_question_with_help(self, combiner):
        """Test _is_asking_question starting with 'help me'."""
        assert combiner._is_asking_question("Help me with Alex's triggers") is True

    def test_is_asking_question_statement(self, combiner):
        """Test _is_asking_question with statement."""
        assert combiner._is_asking_question("Alex had a meltdown today") is False

    def test_is_asking_question_info_sharing(self, combiner):
        """Test _is_asking_question with info sharing."""
        assert combiner._is_asking_question("I noticed Alex responds well to music") is False
