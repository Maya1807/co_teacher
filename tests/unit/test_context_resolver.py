"""
Unit tests for ContextResolver.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

from app.services.context_resolver import ContextResolver, ResolvedContext
from app.core.router import AgentType


@dataclass
class MockRoutingResult:
    """Mock RoutingResult for testing."""
    agents: List[AgentType]
    confidence: float
    extracted_entities: Dict[str, Any]

    @property
    def is_multi_agent(self) -> bool:
        return len(self.agents) > 1


class TestContextResolver:
    """Tests for ContextResolver."""

    @pytest.fixture
    def mock_student_agent(self):
        """Create a mock student agent."""
        agent = MagicMock()
        agent.get_student_context = AsyncMock(return_value={
            "student_id": "STU001",
            "name": "Alex Johnson",
            "disability_type": "autism",
            "learning_style": "visual",
            "triggers": ["loud noises"],
            "successful_methods": ["visual schedules"],
            "failed_methods": [],
            "profile": {"id": "STU001", "name": "Alex Johnson"}
        })
        return agent

    @pytest.fixture
    def resolver(self, mock_student_agent):
        """Create ContextResolver with mocked dependencies."""
        return ContextResolver(student_agent=mock_student_agent)

    # ==================== extract_conversation_context tests ====================

    def test_extract_context_empty_history(self, resolver):
        """Test with empty history."""
        result = resolver.extract_conversation_context([])

        assert result["recent_student"] is None
        assert result["previous_agents"] == []
        assert result["history_summary"] == ""

    def test_extract_context_single_message(self, resolver):
        """Test with only one message (the current one)."""
        history = [{"role": "user", "content": "Hello"}]
        result = resolver.extract_conversation_context(history)

        assert result["recent_student"] is None
        assert result["previous_agents"] == []

    def test_extract_context_finds_student_name(self, resolver):
        """Test that student names are extracted from history."""
        history = [
            {"role": "user", "content": "Tell me about Alex"},
            {"role": "assistant", "content": "Alex is doing well", "agent_used": "STUDENT_AGENT"},
            {"role": "user", "content": "What works for him?"}
        ]
        result = resolver.extract_conversation_context(history)

        assert result["recent_student"] == "Alex"

    def test_extract_context_finds_student_name_case_insensitive(self, resolver):
        """Test case-insensitive name matching."""
        history = [
            {"role": "user", "content": "What about JORDAN?"},
            {"role": "assistant", "content": "Jordan prefers...", "agent_used": "STUDENT_AGENT"},
            {"role": "user", "content": "Thanks"}
        ]
        result = resolver.extract_conversation_context(history)

        # Should find Jordan (case-insensitive)
        assert result["recent_student"].lower() == "jordan"

    def test_extract_context_tracks_previous_agents(self, resolver):
        """Test that previous agents are tracked."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi", "agent_used": "RAG_AGENT"},
            {"role": "user", "content": "Tell me about Alex"},
            {"role": "assistant", "content": "Alex...", "agent_used": "STUDENT_AGENT"},
            {"role": "user", "content": "Current query"}
        ]
        result = resolver.extract_conversation_context(history)

        assert "RAG_AGENT" in result["previous_agents"]
        assert "STUDENT_AGENT" in result["previous_agents"]

    def test_extract_context_creates_history_summary(self, resolver):
        """Test history summary creation."""
        history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
            {"role": "assistant", "content": "Second response"},
            {"role": "user", "content": "Current query"}
        ]
        result = resolver.extract_conversation_context(history)

        assert "user:" in result["history_summary"].lower()
        assert "assistant:" in result["history_summary"].lower()

    def test_extract_context_truncates_long_content(self, resolver):
        """Test that long content is truncated in summary."""
        long_content = "A" * 200
        history = [
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Current"}
        ]
        result = resolver.extract_conversation_context(history)

        # Summary should contain truncated content (100 chars + "...")
        assert "..." in result["history_summary"]

    # ==================== class-wide detection tests ====================

    def test_extract_context_detects_class_wide_response(self, resolver):
        """3+ student names in assistant message → was_class_wide=True."""
        history = [
            {"role": "user", "content": "Give me tips for all students"},
            {
                "role": "assistant",
                "content": (
                    "Here are tips for your class:\n"
                    "- Alex: Use visual schedules\n"
                    "- Morgan: Provide noise-canceling headphones\n"
                    "- Jordan: Seat near the front\n"
                    "- Casey: Give extra transition time"
                ),
                "agent_used": "RAG_AGENT",
            },
            {"role": "user", "content": "What about the loud sounds?"},
        ]
        result = resolver.extract_conversation_context(history)

        assert result["was_class_wide"] is True
        names_lower = [n.lower() for n in result["mentioned_students"]]
        assert "alex" in names_lower
        assert "morgan" in names_lower
        assert "jordan" in names_lower
        assert "casey" in names_lower

    def test_extract_context_single_student_not_class_wide(self, resolver):
        """1 student name in assistant message → was_class_wide=False."""
        history = [
            {"role": "user", "content": "Tell me about Alex"},
            {
                "role": "assistant",
                "content": "Alex has autism and does well with visual schedules.",
                "agent_used": "STUDENT_AGENT",
            },
            {"role": "user", "content": "What works for him?"},
        ]
        result = resolver.extract_conversation_context(history)

        assert result["was_class_wide"] is False
        assert result["mentioned_students"] == []

    def test_extract_context_class_wide_preserves_recent_student(self, resolver):
        """recent_student is still set alongside was_class_wide=True."""
        history = [
            {"role": "user", "content": "Tips for everyone"},
            {
                "role": "assistant",
                "content": (
                    "- Alex: visual schedules\n"
                    "- Morgan: headphones\n"
                    "- Riley: fidget tools"
                ),
                "agent_used": "RAG_AGENT",
            },
            {"role": "user", "content": "How about Alex with loud sounds?"},
        ]
        result = resolver.extract_conversation_context(history)

        assert result["was_class_wide"] is True
        # recent_student should still be set (first name found scanning backwards)
        assert result["recent_student"] is not None

    def test_extract_context_assistant_summary_longer_truncation(self, resolver):
        """Assistant messages get 300 chars in summary, user messages get 100."""
        assistant_content = "A" * 250  # > 100 but < 300
        user_content = "B" * 150
        history = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": "Current query"},
        ]
        result = resolver.extract_conversation_context(history)

        summary = result["history_summary"]
        # Assistant's 250-char content should survive (not truncated at 100)
        assert "A" * 250 in summary
        # User's 150-char content should be truncated to 100
        assert "B" * 150 not in summary
        assert "B" * 100 in summary

    # ==================== resolve_student tests ====================

    @pytest.mark.asyncio
    async def test_resolve_student_from_routing(self, resolver, mock_student_agent):
        """Test resolving student from routing result."""
        result = await resolver.resolve_student(
            student_name_from_routing="Alex",
            conversation_context={},
            should_resolve=True
        )

        assert result["name"] == "Alex Johnson"
        mock_student_agent.get_student_context.assert_called_once_with(
            student_name="Alex"
        )

    @pytest.mark.asyncio
    async def test_resolve_student_from_context(self, resolver, mock_student_agent):
        """Test resolving student from conversation context when not in routing."""
        result = await resolver.resolve_student(
            student_name_from_routing=None,
            conversation_context={"recent_student": "Alex"},
            should_resolve=True
        )

        assert result["name"] == "Alex Johnson"
        mock_student_agent.get_student_context.assert_called_once_with(
            student_name="Alex"
        )

    @pytest.mark.asyncio
    async def test_resolve_student_routing_takes_precedence(self, resolver, mock_student_agent):
        """Test that routing entity takes precedence over context."""
        await resolver.resolve_student(
            student_name_from_routing="Jordan",
            conversation_context={"recent_student": "Alex"},
            should_resolve=True
        )

        # Should use Jordan from routing, not Alex from context
        mock_student_agent.get_student_context.assert_called_once_with(
            student_name="Jordan"
        )

    @pytest.mark.asyncio
    async def test_resolve_student_no_name_no_resolve(self, resolver, mock_student_agent):
        """Test that None is returned when no name and should_resolve=False."""
        result = await resolver.resolve_student(
            student_name_from_routing=None,
            conversation_context={},
            should_resolve=False
        )

        assert result is None
        mock_student_agent.get_student_context.assert_not_called()

    # ==================== resolve (combined) tests ====================

    @pytest.mark.asyncio
    async def test_resolve_full_flow(self, resolver, mock_student_agent):
        """Test complete resolution flow."""
        history = [
            {"role": "user", "content": "Tell me about Alex"},
            {"role": "assistant", "content": "Alex is...", "agent_used": "STUDENT_AGENT"},
            {"role": "user", "content": "What works?"}
        ]
        routing = MockRoutingResult(
            agents=[AgentType.STUDENT_AGENT, AgentType.RAG_AGENT],
            confidence=0.9,
            extracted_entities={"name": "Alex"}
        )

        result = await resolver.resolve(
            history=history,
            routing_result=routing,
            should_get_student=True
        )

        assert isinstance(result, ResolvedContext)
        assert result.conversation_context["recent_student"] == "Alex"
        assert result.student_context is not None
        assert result.student_name == "Alex Johnson"

    @pytest.mark.asyncio
    async def test_resolve_without_student(self, resolver, mock_student_agent):
        """Test resolution when student is not needed."""
        history = [
            {"role": "user", "content": "What strategies work for ADHD?"},
            {"role": "assistant", "content": "Here are some...", "agent_used": "RAG_AGENT"},
            {"role": "user", "content": "Tell me more"}
        ]
        routing = MockRoutingResult(
            agents=[AgentType.RAG_AGENT],
            confidence=0.9,
            extracted_entities={}
        )

        result = await resolver.resolve(
            history=history,
            routing_result=routing,
            should_get_student=False
        )

        assert result.student_context is None
        mock_student_agent.get_student_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_uses_context_student_as_fallback(self, resolver, mock_student_agent):
        """Test that conversation context student is used as fallback."""
        history = [
            {"role": "user", "content": "Tell me about Alex"},
            {"role": "assistant", "content": "Alex...", "agent_used": "STUDENT_AGENT"},
            {"role": "user", "content": "What else works for him?"}  # No name but references student
        ]
        routing = MockRoutingResult(
            agents=[AgentType.RAG_AGENT],
            confidence=0.7,
            extracted_entities={}  # No name extracted
        )

        result = await resolver.resolve(
            history=history,
            routing_result=routing,
            should_get_student=True
        )

        # Should still get student context from conversation history
        assert result.student_context is not None
        mock_student_agent.get_student_context.assert_called()
