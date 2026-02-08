"""
Unit tests for LLMPlanner.
Tests plan creation, JSON parsing, validation, and fallback behaviour.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.planner import LLMPlanner, ExecutionPlan, PlanStep
from app.core.router import AgentType


# ==================== Fixtures ====================

@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.complete = AsyncMock(return_value={
        "content": "",
        "tokens_used": {"input": 50, "output": 30},
        "cost": 0.001,
    })
    return client


@pytest.fixture
def mock_step_tracker():
    tracker = MagicMock()
    tracker.add_step = MagicMock()
    return tracker


@pytest.fixture
def planner(mock_llm_client, mock_step_tracker):
    return LLMPlanner(llm_client=mock_llm_client, step_tracker=mock_step_tracker)


# ==================== Tests ====================

class TestCreatePlan:
    """Tests for LLMPlanner.create_plan()."""

    @pytest.mark.asyncio
    async def test_create_plan_single_agent(self, planner, mock_llm_client):
        """'Tell me about Alex' produces a 1-step STUDENT_AGENT plan."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": "Alex",
                "steps": [
                    {"step_index": 0, "agent": "STUDENT_AGENT", "task": "Retrieve Alex's profile", "depends_on": []}
                ],
            }),
            "tokens_used": {"input": 50, "output": 30},
        }

        plan = await planner.create_plan("Tell me about Alex")

        assert len(plan.steps) == 1
        assert plan.steps[0].agent == AgentType.STUDENT_AGENT
        assert plan.steps[0].task == "Retrieve Alex's profile"
        assert plan.student_name == "Alex"
        assert plan.is_multi_step is False

    @pytest.mark.asyncio
    async def test_create_plan_multi_agent(self, planner, mock_llm_client):
        """'What strategies work for Alex?' produces a 2-step plan with depends_on."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": "Alex",
                "steps": [
                    {"step_index": 0, "agent": "STUDENT_AGENT", "task": "Retrieve Alex's profile", "depends_on": []},
                    {"step_index": 1, "agent": "RAG_AGENT", "task": "Find strategies for Alex's disability type", "depends_on": [0]},
                ],
            }),
            "tokens_used": {"input": 50, "output": 60},
        }

        plan = await planner.create_plan("What strategies work for Alex?")

        assert len(plan.steps) == 2
        assert plan.steps[0].agent == AgentType.STUDENT_AGENT
        assert plan.steps[1].agent == AgentType.RAG_AGENT
        assert plan.steps[1].depends_on == [0]
        assert plan.is_multi_step is True

    @pytest.mark.asyncio
    async def test_create_plan_extracts_student_name(self, planner, mock_llm_client):
        """student_name field is populated from LLM response."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": "Jordan",
                "steps": [
                    {"step_index": 0, "agent": "STUDENT_AGENT", "task": "Get Jordan's profile", "depends_on": []},
                ],
            }),
            "tokens_used": {"input": 50, "output": 30},
        }

        plan = await planner.create_plan("What are Jordan's triggers?")

        assert plan.student_name == "Jordan"

    @pytest.mark.asyncio
    async def test_create_plan_with_conversation_context(self, planner, mock_llm_client):
        """Context is appended to prompt when conversation context exists."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": "Alex",
                "steps": [
                    {"step_index": 0, "agent": "STUDENT_AGENT", "task": "Get profile", "depends_on": []},
                ],
            }),
            "tokens_used": {"input": 80, "output": 30},
        }

        conv_context = {
            "recent_student": "Alex",
            "previous_agents": ["STUDENT_AGENT"],
            "history_summary": "Discussed Alex's triggers earlier",
        }

        await planner.create_plan("How's he doing?", conversation_context=conv_context)

        # Verify the prompt sent to LLM contains the context addendum
        call_args = mock_llm_client.complete.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "Alex" in user_msg
        assert "Discussed Alex" in user_msg

    @pytest.mark.asyncio
    async def test_create_plan_without_context(self, planner, mock_llm_client):
        """Context section is omitted when conversation context is empty."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": None,
                "steps": [
                    {"step_index": 0, "agent": "RAG_AGENT", "task": "Find ADHD strategies", "depends_on": []},
                ],
            }),
            "tokens_used": {"input": 50, "output": 30},
        }

        await planner.create_plan("ADHD strategies", conversation_context=None)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "Conversation context" not in user_msg

    @pytest.mark.asyncio
    async def test_create_plan_invalid_json_fallback(self, planner, mock_llm_client):
        """Returns fallback single-step plan on bad LLM output."""
        mock_llm_client.complete.return_value = {
            "content": "This is not valid JSON at all",
            "tokens_used": {"input": 50, "output": 10},
        }

        plan = await planner.create_plan("What strategies for ADHD?")

        assert len(plan.steps) == 1
        assert plan.steps[0].agent == AgentType.RAG_AGENT
        assert plan.student_name is None

    @pytest.mark.asyncio
    async def test_create_plan_invalid_agent_fallback(self, planner, mock_llm_client):
        """Returns fallback plan on unknown agent name."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": None,
                "steps": [
                    {"step_index": 0, "agent": "UNKNOWN_AGENT", "task": "Do something", "depends_on": []},
                ],
            }),
            "tokens_used": {"input": 50, "output": 30},
        }

        plan = await planner.create_plan("test query")

        # Should fallback to RAG_AGENT
        assert len(plan.steps) == 1
        assert plan.steps[0].agent == AgentType.RAG_AGENT

    @pytest.mark.asyncio
    async def test_create_plan_with_class_wide_context(self, planner, mock_llm_client):
        """When was_class_wide=True, the planner prompt includes the flag and mentioned students."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": "ALL_STUDENTS",
                "steps": [
                    {"step_index": 0, "agent": "RAG_AGENT", "task": "Find strategies for loud sounds for all students", "depends_on": []},
                ],
            }),
            "tokens_used": {"input": 80, "output": 30},
        }

        conv_context = {
            "recent_student": "Alex",
            "previous_agents": ["RAG_AGENT"],
            "history_summary": "Discussed class-wide strategies",
            "was_class_wide": True,
            "mentioned_students": ["Alex", "Morgan", "Jordan"],
        }

        await planner.create_plan("What about the loud sounds?", conversation_context=conv_context)

        call_args = mock_llm_client.complete.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "class-wide: True" in user_msg
        assert "Alex, Morgan, Jordan" in user_msg

    @pytest.mark.asyncio
    async def test_create_plan_invalid_depends_on(self, planner, mock_llm_client):
        """Returns fallback plan on forward references in depends_on."""
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "student_name": None,
                "steps": [
                    {"step_index": 0, "agent": "RAG_AGENT", "task": "Do A", "depends_on": [1]},
                    {"step_index": 1, "agent": "ADMIN_AGENT", "task": "Do B", "depends_on": []},
                ],
            }),
            "tokens_used": {"input": 50, "output": 40},
        }

        plan = await planner.create_plan("test query")

        # Forward reference should cause fallback
        assert len(plan.steps) == 1
        assert plan.steps[0].agent == AgentType.RAG_AGENT


class TestExecutionPlanProperties:
    """Tests for ExecutionPlan dataclass properties."""

    def test_is_multi_step_single(self):
        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="get profile")],
            student_name="Alex",
            original_query="Tell me about Alex",
        )
        assert plan.is_multi_step is False

    def test_is_multi_step_multiple(self):
        plan = ExecutionPlan(
            steps=[
                PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="get profile"),
                PlanStep(step_index=1, agent=AgentType.RAG_AGENT, task="find strategies", depends_on=[0]),
            ],
            student_name="Alex",
            original_query="Strategies for Alex?",
        )
        assert plan.is_multi_step is True

    def test_agents_involved(self):
        plan = ExecutionPlan(
            steps=[
                PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="get profile"),
                PlanStep(step_index=1, agent=AgentType.RAG_AGENT, task="find strategies", depends_on=[0]),
            ],
            student_name="Alex",
            original_query="Strategies for Alex?",
        )
        assert plan.agents_involved == [AgentType.STUDENT_AGENT, AgentType.RAG_AGENT]

    def test_agents_involved_deduplicates(self):
        plan = ExecutionPlan(
            steps=[
                PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="get profile"),
                PlanStep(step_index=1, agent=AgentType.STUDENT_AGENT, task="update profile"),
            ],
            student_name="Alex",
            original_query="Update Alex",
        )
        assert plan.agents_involved == [AgentType.STUDENT_AGENT]

    def test_needs_student_context(self):
        plan_with = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="get profile")],
            student_name="Alex",
            original_query="Tell me about Alex",
        )
        plan_without = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.RAG_AGENT, task="find strategies")],
            student_name=None,
            original_query="ADHD strategies",
        )
        assert plan_with.needs_student_context is True
        assert plan_without.needs_student_context is False
