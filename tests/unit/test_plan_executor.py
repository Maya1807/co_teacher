"""
Unit tests for PlanExecutor.
Tests step execution, dependency enrichment, synthesis, and presentation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.planner import PlanStep, ExecutionPlan
from app.core.router import AgentType
from app.services.plan_executor import PlanExecutor


# ==================== Fixtures ====================

@pytest.fixture
def mock_student_agent():
    agent = MagicMock()
    agent.process = AsyncMock(return_value={
        "response": "Alex is a 4th grader with autism.",
        "action_taken": "profile_retrieved",
        "student_name": "Alex",
    })
    return agent


@pytest.fixture
def mock_rag_agent():
    agent = MagicMock()
    agent.process = AsyncMock(return_value={
        "response": "Visual schedules and social stories work well for autism.",
        "methods_retrieved": [],
    })
    return agent


@pytest.fixture
def mock_admin_agent():
    agent = MagicMock()
    agent.process = AsyncMock(return_value={
        "response": "Draft IEP report here.",
        "document_type": "iep",
    })
    return agent


@pytest.fixture
def mock_predict_agent():
    agent = MagicMock()
    agent.process = AsyncMock(return_value={
        "response": "Watch for fire drill concerns.",
    })
    return agent


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.complete = AsyncMock(return_value={
        "content": "Synthesized response combining all results.",
        "tokens_used": {"input": 100, "output": 50},
    })
    return client


@pytest.fixture
def mock_step_tracker():
    tracker = MagicMock()
    tracker.add_step = MagicMock()
    return tracker


@pytest.fixture
def mock_presenter():
    presenter = MagicMock()
    presenter.present = AsyncMock(side_effect=lambda q, r, **kw: r)
    return presenter


@pytest.fixture
def executor(
    mock_student_agent,
    mock_rag_agent,
    mock_admin_agent,
    mock_predict_agent,
    mock_llm_client,
    mock_step_tracker,
    mock_presenter,
):
    return PlanExecutor(
        student_agent=mock_student_agent,
        rag_agent=mock_rag_agent,
        admin_agent=mock_admin_agent,
        predict_agent=mock_predict_agent,
        llm_client=mock_llm_client,
        step_tracker=mock_step_tracker,
        presenter=mock_presenter,
    )


# ==================== Tests ====================

class TestExecuteSingleStep:
    """Tests for single-step plan execution."""

    @pytest.mark.asyncio
    async def test_execute_single_step(self, executor, mock_rag_agent):
        """Single agent is called with the step's task as prompt."""
        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.RAG_AGENT, task="Find ADHD strategies")],
            student_name=None,
            original_query="ADHD strategies",
        )

        result = await executor.execute(plan)

        mock_rag_agent.process.assert_called_once()
        call_args = mock_rag_agent.process.call_args
        input_data = call_args[0][0]
        assert input_data["prompt"] == "Find ADHD strategies"
        assert "RAG_AGENT" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_execute_passes_original_query(self, executor, mock_student_agent):
        """original_query is passed in input_data for update detection."""
        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Get Alex's profile")],
            student_name="Alex",
            original_query="Tell me about Alex",
        )

        await executor.execute(plan)

        call_args = mock_student_agent.process.call_args
        input_data = call_args[0][0]
        assert input_data["original_query"] == "Tell me about Alex"

    @pytest.mark.asyncio
    async def test_execute_passes_student_context(self, executor, mock_student_agent):
        """Student context flows to agents."""
        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Get profile")],
            student_name="Alex",
            original_query="Tell me about Alex",
        )

        student_ctx = {
            "name": "Alex",
            "student_id": "STU001",
            "disability_type": "autism",
            "profile": {"name": "Alex", "disability_type": "autism"},
        }

        await executor.execute(plan, student_context=student_ctx)

        call_args = mock_student_agent.process.call_args
        input_data = call_args[0][0]
        assert input_data["student_name"] == "Alex"
        assert input_data["student_id"] == "STU001"
        assert input_data["student_context"] == student_ctx


class TestExecuteMultiStep:
    """Tests for multi-step plan execution."""

    @pytest.mark.asyncio
    async def test_execute_multi_step_dependencies(
        self, executor, mock_student_agent, mock_rag_agent
    ):
        """Step 1 gets step 0's results enriched into its prompt."""
        plan = ExecutionPlan(
            steps=[
                PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Get Alex's profile"),
                PlanStep(step_index=1, agent=AgentType.RAG_AGENT, task="Find strategies for Alex", depends_on=[0]),
            ],
            student_name="Alex",
            original_query="What strategies work for Alex?",
        )

        await executor.execute(plan)

        # RAG agent should receive enriched prompt with student agent's result
        rag_call = mock_rag_agent.process.call_args
        rag_input = rag_call[0][0]
        prompt = rag_input["prompt"]
        assert "Find strategies for Alex" in prompt
        assert "Alex is a 4th grader" in prompt  # from mock student agent response

    @pytest.mark.asyncio
    async def test_execute_synthesizes_multi_step(
        self, executor, mock_llm_client
    ):
        """Multi-step plans trigger synthesis LLM call."""
        plan = ExecutionPlan(
            steps=[
                PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Get profile"),
                PlanStep(step_index=1, agent=AgentType.RAG_AGENT, task="Find strategies", depends_on=[0]),
            ],
            student_name="Alex",
            original_query="What strategies work for Alex?",
        )

        result = await executor.execute(plan)

        # Synthesis LLM call should have happened
        mock_llm_client.complete.assert_called_once()
        call_args = mock_llm_client.complete.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "What strategies work for Alex?" in user_msg
        assert result["response"] == "Synthesized response combining all results."


class TestPresentation:
    """Tests for presentation handling."""

    @pytest.mark.asyncio
    async def test_execute_applies_presentation(self, executor, mock_presenter):
        """Presenter is called on the final response."""
        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.RAG_AGENT, task="Find strategies")],
            student_name=None,
            original_query="ADHD strategies",
        )

        await executor.execute(plan)

        mock_presenter.present.assert_called_once()
        call_args = mock_presenter.present.call_args
        assert call_args[0][0] == "ADHD strategies"  # query
        assert call_args.kwargs.get("skip_for_updates") is False

    @pytest.mark.asyncio
    async def test_execute_skips_presentation_for_updates(
        self, executor, mock_student_agent, mock_presenter
    ):
        """update_applied responses skip presenter voice transformation."""
        mock_student_agent.process.return_value = {
            "response": "Updated Alex's profile.",
            "action_taken": "update_applied",
            "student_name": "Alex",
            "updates_applied": {"triggers": ["fire drills"]},
        }

        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Update Alex's profile")],
            student_name="Alex",
            original_query="Alex had a meltdown during the fire drill",
        )

        result = await executor.execute(plan)

        mock_presenter.present.assert_called_once()
        call_args = mock_presenter.present.call_args
        assert call_args.kwargs.get("skip_for_updates") is True
        assert result["updates_applied"] == {"triggers": ["fire drills"]}


class TestShortCircuit:
    """Tests for student update short-circuit behavior."""

    @pytest.mark.asyncio
    async def test_execute_short_circuits_on_pure_update(
        self, executor, mock_student_agent, mock_rag_agent
    ):
        """Remaining steps are skipped when a pure update is detected."""
        mock_student_agent.process.return_value = {
            "response": "Updated Alex's triggers.",
            "action_taken": "update_applied",
            "student_name": "Alex",
            "updates_applied": {"triggers": ["fire drills"]},
        }

        plan = ExecutionPlan(
            steps=[
                PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Update Alex's profile"),
                PlanStep(step_index=1, agent=AgentType.RAG_AGENT, task="Find strategies", depends_on=[0]),
            ],
            student_name="Alex",
            # NOT a question (no "?" or question starters) — pure update
            original_query="Alex had a meltdown during the fire drill",
        )

        result = await executor.execute(plan)

        # RAG agent should NOT have been called
        mock_rag_agent.process.assert_not_called()
        assert result["response"] == "Updated Alex's triggers."
        assert result["updates_applied"] == {"triggers": ["fire drills"]}
