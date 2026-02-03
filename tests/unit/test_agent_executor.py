"""
Unit tests for AgentExecutor.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.agent_executor import AgentExecutor
from app.core.router import AgentType


class TestAgentExecutor:
    """Tests for AgentExecutor."""

    @pytest.fixture
    def mock_student_agent(self):
        """Create mock student agent."""
        agent = MagicMock()
        agent.process = AsyncMock(return_value={
            "response": "Student agent response",
            "student_profile": {"name": "Alex"},
            "action_taken": "profile_retrieved"
        })
        return agent

    @pytest.fixture
    def mock_rag_agent(self):
        """Create mock RAG agent."""
        agent = MagicMock()
        agent.process = AsyncMock(return_value={
            "response": "RAG agent response",
            "methods_used": ["visual schedules"]
        })
        return agent

    @pytest.fixture
    def mock_admin_agent(self):
        """Create mock admin agent."""
        agent = MagicMock()
        agent.process = AsyncMock(return_value={
            "response": "Admin agent response",
            "doc_type": "iep"
        })
        return agent

    @pytest.fixture
    def mock_predict_agent(self):
        """Create mock predict agent."""
        agent = MagicMock()
        agent.process = AsyncMock(return_value={
            "response": "Predict agent response",
            "risks_identified": []
        })
        return agent

    @pytest.fixture
    def executor(self, mock_student_agent, mock_rag_agent, mock_admin_agent, mock_predict_agent):
        """Create AgentExecutor with all mock agents."""
        return AgentExecutor(
            student_agent=mock_student_agent,
            rag_agent=mock_rag_agent,
            admin_agent=mock_admin_agent,
            predict_agent=mock_predict_agent
        )

    @pytest.mark.asyncio
    async def test_execute_student_agent(self, executor, mock_student_agent):
        """Test executing student agent."""
        result = await executor.execute(
            agent_type=AgentType.STUDENT_AGENT,
            query="Tell me about Alex"
        )

        assert result["response"] == "Student agent response"
        mock_student_agent.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_rag_agent(self, executor, mock_rag_agent):
        """Test executing RAG agent."""
        result = await executor.execute(
            agent_type=AgentType.RAG_AGENT,
            query="What strategies work for autism?"
        )

        assert result["response"] == "RAG agent response"
        mock_rag_agent.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_admin_agent(self, executor, mock_admin_agent):
        """Test executing admin agent."""
        result = await executor.execute(
            agent_type=AgentType.ADMIN_AGENT,
            query="Draft an IEP report"
        )

        assert result["response"] == "Admin agent response"
        mock_admin_agent.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_predict_agent(self, executor, mock_predict_agent):
        """Test executing predict agent."""
        result = await executor.execute(
            agent_type=AgentType.PREDICT_AGENT,
            query="What's the daily briefing?"
        )

        assert result["response"] == "Predict agent response"
        mock_predict_agent.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_student_context(self, executor, mock_rag_agent):
        """Test executing with student context."""
        student_context = {
            "student_id": "STU001",
            "name": "Alex Johnson",
            "disability_type": "autism"
        }

        await executor.execute(
            agent_type=AgentType.RAG_AGENT,
            query="What works?",
            student_context=student_context
        )

        # Verify input_data includes student info
        call_args = mock_rag_agent.process.call_args
        input_data = call_args[0][0]
        assert input_data["student_name"] == "Alex Johnson"
        assert input_data["student_id"] == "STU001"
        assert input_data["student_context"] == student_context

    @pytest.mark.asyncio
    async def test_execute_with_context(self, executor, mock_student_agent):
        """Test executing with additional context."""
        context = {"session_id": "test-123", "teacher_id": "T001"}

        await executor.execute(
            agent_type=AgentType.STUDENT_AGENT,
            query="Tell me about Alex",
            context=context
        )

        # Verify context is passed
        call_args = mock_student_agent.process.call_args
        assert call_args[0][1] == context

    @pytest.mark.asyncio
    async def test_execute_unknown_agent_raises(self, executor):
        """Test that unknown agent type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown or unsupported agent type"):
            await executor.execute(
                agent_type=AgentType.ORCHESTRATOR,  # Not a supported execution target
                query="Test"
            )

    def test_get_agent(self, executor, mock_student_agent):
        """Test getting agent by type."""
        agent = executor.get_agent(AgentType.STUDENT_AGENT)
        assert agent is mock_student_agent

    def test_get_agent_unknown_returns_none(self, executor):
        """Test getting unknown agent returns None."""
        agent = executor.get_agent(AgentType.ORCHESTRATOR)
        assert agent is None

    def test_supported_agents(self, executor):
        """Test supported_agents property."""
        supported = executor.supported_agents
        assert AgentType.STUDENT_AGENT in supported
        assert AgentType.RAG_AGENT in supported
        assert AgentType.ADMIN_AGENT in supported
        assert AgentType.PREDICT_AGENT in supported
        assert len(supported) == 4
