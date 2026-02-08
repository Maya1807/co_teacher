"""
Unit tests for all agents.
Uses mocks to avoid actual LLM/database calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from app.agents.student_agent import StudentAgent
from app.agents.rag_agent import RAGAgent
from app.agents.admin_agent import AdminAgent
from app.agents.orchestrator import Orchestrator, reset_orchestrator
from app.core.router import AgentType


# ==================== Fixtures ====================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.complete = AsyncMock(return_value={
        "content": "Mock LLM response",
        "tokens_used": {"input": 100, "output": 50},
        "cost": 0.001
    })
    client.embed = AsyncMock(return_value=[0.1] * 1536)
    return client


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager."""
    manager = MagicMock()

    # Student operations
    manager.get_student_profile = AsyncMock(return_value={
        "student_id": "STU001",
        "name": "Alex Johnson",
        "grade": "4",
        "disability_type": "autism",
        "learning_style": "visual",
        "triggers": ["loud noises", "schedule changes"],
        "successful_methods": ["visual schedules", "fidget tools"],
        "failed_methods": ["group work without support"]
    })
    manager.search_student_by_name = AsyncMock(return_value=[{
        "student_id": "STU001",
        "name": "Alex Johnson",
        "grade": "4",
        "disability_type": "autism"
    }])
    manager.find_similar_students = AsyncMock(return_value=[])
    manager.get_daily_context = AsyncMock(return_value=[])

    # Teaching methods operations
    manager.search_teaching_methods = AsyncMock(return_value=[
        {
            "method_id": "M001",
            "method_name": "Visual Schedules",
            "category": "Autism Support",
            "description": "Use visual cues to show daily schedule",
            "score": 0.95
        },
        {
            "method_id": "M002",
            "method_name": "Social Stories",
            "category": "Autism Support",
            "description": "Short stories explaining social situations",
            "score": 0.87
        }
    ])

    # Conversation operations (needed by Orchestrator)
    manager.get_or_create_conversation = AsyncMock(return_value={
        "id": "conv-123",
        "session_id": "default",
        "teacher_id": "T001"
    })
    manager.add_message = AsyncMock(return_value={"id": "msg-123"})
    manager.get_conversation_history = AsyncMock(return_value=[])

    # Events operations (needed by PredictAgent)
    manager.get_todays_events = AsyncMock(return_value=[])
    manager.get_upcoming_events = AsyncMock(return_value=[])
    manager.list_students = AsyncMock(return_value=[])

    return manager


@pytest.fixture
def mock_step_tracker():
    """Create a mock step tracker."""
    tracker = MagicMock()
    tracker.add_step = MagicMock()
    tracker.get_steps = MagicMock(return_value=[])
    return tracker


@pytest.fixture
def mock_cache():
    """Create a mock cache."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    return cache


# ==================== StudentAgent Tests ====================

class TestStudentAgent:
    """Tests for StudentAgent."""

    @pytest.fixture
    def agent(self, mock_llm_client, mock_step_tracker, mock_memory_manager):
        """Create a StudentAgent with mocks."""
        return StudentAgent(
            llm_client=mock_llm_client,
            step_tracker=mock_step_tracker,
            memory_manager=mock_memory_manager
        )

    @pytest.mark.asyncio
    async def test_module_name(self, agent):
        """StudentAgent has correct module name."""
        assert agent.MODULE_NAME == "STUDENT_AGENT"

    @pytest.mark.asyncio
    async def test_process_with_student_name(self, agent, mock_memory_manager):
        """Can process query with student name."""
        result = await agent.process(
            {"prompt": "Tell me about Alex", "student_name": "Alex"},
            context={"teacher_id": "T001"}
        )

        assert result["student_profile"] is not None
        assert result["student_name"] == "Alex Johnson"
        assert result["action_taken"] == "profile_retrieved"
        mock_memory_manager.search_student_by_name.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_student_id(self, agent, mock_memory_manager):
        """Can process query with student ID."""
        result = await agent.process(
            {"prompt": "Show profile", "student_id": "STU001"}
        )

        assert result["student_profile"] is not None
        assert result["student_id"] == "STU001"
        mock_memory_manager.get_student_profile.assert_called_once_with("STU001")

    @pytest.mark.asyncio
    async def test_process_student_not_found(self, agent, mock_memory_manager):
        """Handles student not found gracefully."""
        mock_memory_manager.search_student_by_name.return_value = []

        result = await agent.process(
            {"prompt": "Tell me about Unknown Student", "student_name": "Unknown"}
        )

        assert result["student_profile"] is None
        assert result["action_taken"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_student_context(self, agent, mock_memory_manager):
        """Can get student context for other agents."""
        context = await agent.get_student_context(student_name="Alex")

        assert context is not None
        assert context["name"] == "Alex Johnson"
        assert context["disability_type"] == "autism"
        assert "triggers" in context

    @pytest.mark.asyncio
    async def test_process_update_action(self, agent, mock_memory_manager, mock_llm_client):
        """Can handle update action with actual profile updates."""
        # Mock LLM to return structured update extraction
        mock_llm_client.complete.side_effect = [
            # First call: extract update info
            {
                "content": '{"is_update": true, "reason": "Teacher sharing positive observation", "updates": {"notes": "Had a good day today"}}',
                "tokens_used": {"input": 100, "output": 50},
                "cost": 0.001
            },
            # Second call: confirmation message
            {
                "content": "Got it! I've added that note to Alex's profile.",
                "tokens_used": {"input": 50, "output": 20},
                "cost": 0.0005
            }
        ]

        # Mock the update to succeed
        mock_memory_manager.update_student_profile = AsyncMock(return_value=True)

        result = await agent.process(
            {
                "prompt": "Alex had a good day today",
                "student_id": "STU001",
                "action": "update"
            }
        )

        assert result["action_taken"] == "update_applied"
        assert result["updates_applied"] is not None
        mock_memory_manager.update_student_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_update_not_an_update(self, agent, mock_memory_manager, mock_llm_client):
        """Recognizes when a query is not actually an update request."""
        # Mock LLM to determine this is not an update
        mock_llm_client.complete.return_value = {
            "content": '{"is_update": false, "reason": "This is a question, not new information", "updates": {}}',
            "tokens_used": {"input": 100, "output": 50},
            "cost": 0.001
        }

        result = await agent.process(
            {
                "prompt": "What are Alex's triggers?",
                "student_id": "STU001",
                "action": "update"
            }
        )

        assert result["action_taken"] == "not_an_update"


# ==================== RAGAgent Tests ====================

class TestRAGAgent:
    """Tests for RAGAgent."""

    @pytest.fixture
    def agent(self, mock_llm_client, mock_step_tracker, mock_memory_manager, mock_cache):
        """Create a RAGAgent with mocks."""
        with patch('app.agents.rag_agent.get_cache', return_value=mock_cache):
            return RAGAgent(
                llm_client=mock_llm_client,
                step_tracker=mock_step_tracker,
                memory_manager=mock_memory_manager
            )

    @pytest.mark.asyncio
    async def test_module_name(self, agent):
        """RAGAgent has correct module name."""
        assert agent.MODULE_NAME == "RAG_AGENT"

    @pytest.mark.asyncio
    async def test_process_general_query(self, agent, mock_memory_manager):
        """Can process general strategy query."""
        result = await agent.process(
            {"prompt": "What strategies work for ADHD?"}
        )

        assert "response" in result
        assert "methods_retrieved" in result
        assert len(result["methods_retrieved"]) == 2
        mock_memory_manager.search_teaching_methods.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_student_context(self, agent, mock_memory_manager):
        """Uses student context when provided."""
        result = await agent.process(
            {
                "prompt": "What strategies work?",
                "student_context": {
                    "disability_type": "autism",
                    "learning_style": "visual",
                    "failed_methods": ["group work"]
                }
            }
        )

        assert result["student_context_used"] is True
        # Check that failed methods were passed to exclude
        call_args = mock_memory_manager.search_teaching_methods.call_args
        assert call_args.kwargs.get("exclude_methods") == ["group work"]

    @pytest.mark.asyncio
    async def test_cache_hit(self, agent, mock_cache, mock_llm_client):
        """Returns cached response when available."""
        mock_cache.get.return_value = "Cached strategy response"

        result = await agent.process({"prompt": "ADHD strategies"})

        assert result["from_cache"] is True
        assert result["response"] == "Cached strategy response"
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_stores_response(self, agent, mock_cache):
        """Stores response in cache after generation."""
        result = await agent.process({"prompt": "New query"})

        assert result["from_cache"] is False
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_methods_for_student(self, agent, mock_memory_manager):
        """Can get methods specifically for a student."""
        methods = await agent.get_methods_for_student(
            query="reading strategies",
            student_profile={"name": "Alex", "disability_type": "autism", "failed_methods": []},
            top_k=3
        )

        assert len(methods) == 2  # Only 2 returned by mock


# ==================== AdminAgent Tests ====================

class TestAdminAgent:
    """Tests for AdminAgent."""

    @pytest.fixture
    def agent(self, mock_llm_client, mock_step_tracker, mock_memory_manager, mock_cache):
        """Create an AdminAgent with mocks."""
        with patch('app.agents.admin_agent.get_cache', return_value=mock_cache):
            return AdminAgent(
                llm_client=mock_llm_client,
                step_tracker=mock_step_tracker,
                memory_manager=mock_memory_manager
            )

    @pytest.mark.asyncio
    async def test_module_name(self, agent):
        """AdminAgent has correct module name."""
        assert agent.MODULE_NAME == "ADMIN_AGENT"

    @pytest.mark.asyncio
    async def test_detect_iep_doc_type(self, agent):
        """Detects IEP document type."""
        assert agent._detect_doc_type("Update the IEP goals") == "iep"
        assert agent._detect_doc_type("Progress report for Alex") == "iep"

    @pytest.mark.asyncio
    async def test_detect_email_doc_type(self, agent):
        """Detects email document type."""
        assert agent._detect_doc_type("Write an email to parent") == "email"
        assert agent._detect_doc_type("Parent message about behavior") == "email"

    @pytest.mark.asyncio
    async def test_detect_summary_doc_type(self, agent):
        """Detects summary document type."""
        assert agent._detect_doc_type("Daily summary") == "summary"
        assert agent._detect_doc_type("Weekly overview") == "summary"

    @pytest.mark.asyncio
    async def test_detect_incident_doc_type(self, agent):
        """Detects incident document type."""
        assert agent._detect_doc_type("Incident report") == "incident"

    @pytest.mark.asyncio
    async def test_process_iep_request(self, agent):
        """Can process IEP-related request."""
        result = await agent.process(
            {
                "prompt": "Write IEP goals for Alex",
                "student_context": {"name": "Alex", "disability_type": "autism"}
            }
        )

        assert result["document_type"] == "iep"
        assert "response" in result

    @pytest.mark.asyncio
    async def test_process_email_request(self, agent):
        """Can process parent email request."""
        result = await agent.process(
            {
                "prompt": "Write an email to Alex's parents about his progress",
                "student_context": {"name": "Alex"}
            }
        )

        assert result["document_type"] == "email"

    @pytest.mark.asyncio
    async def test_process_summary_request(self, agent):
        """Can process summary request."""
        result = await agent.process(
            {"prompt": "Give me a daily summary"},
            context={"teacher_id": "T001"}
        )

        assert result["document_type"] == "summary"
        assert result["time_period"] == "daily"

    @pytest.mark.asyncio
    async def test_metadata_includes_date(self, agent):
        """Metadata includes generated date."""
        result = await agent.process({"prompt": "Draft a report"})

        assert "metadata" in result
        assert result["metadata"]["generated_date"] == date.today().isoformat()


# ==================== Orchestrator Tests ====================

class TestOrchestrator:
    """Tests for Orchestrator with refactored service-based architecture."""

    @pytest.fixture
    def orchestrator(self, mock_llm_client, mock_step_tracker, mock_memory_manager):
        """Create an Orchestrator with mocks."""
        orch = Orchestrator(
            llm_client=mock_llm_client,
            step_tracker=mock_step_tracker,
            memory_manager=mock_memory_manager
        )
        return orch

    @pytest.mark.asyncio
    async def test_module_name(self, orchestrator):
        """Orchestrator has correct module name."""
        assert orchestrator.MODULE_NAME == "ORCHESTRATOR"

    @pytest.mark.asyncio
    async def test_lazy_agent_initialization(self, orchestrator):
        """Sub-agents are lazily initialized."""
        assert orchestrator._student_agent is None
        assert orchestrator._rag_agent is None
        assert orchestrator._admin_agent is None

        # Access triggers initialization
        _ = orchestrator.student_agent
        assert orchestrator._student_agent is not None

    @pytest.mark.asyncio
    async def test_lazy_service_initialization(self, orchestrator):
        """Services are lazily initialized."""
        assert orchestrator._planner is None
        assert orchestrator._plan_executor is None
        assert orchestrator._conversation_service is None
        assert orchestrator._context_resolver is None
        assert orchestrator._presenter is None

        # Access triggers initialization
        _ = orchestrator.planner
        _ = orchestrator.conversation_service
        assert orchestrator._planner is not None
        assert orchestrator._conversation_service is not None

    @pytest.mark.asyncio
    async def test_process_empty_query(self, orchestrator):
        """Handles empty query gracefully."""
        result = await orchestrator.process({"prompt": ""})

        assert "response" in result
        assert "didn't receive" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_plans_to_student_agent(self, orchestrator, mock_llm_client, mock_memory_manager):
        """Plans student queries to StudentAgent via planner + plan_executor."""
        from app.core.planner import ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Get Alex's profile")],
            student_name="Alex",
            original_query="Tell me about Alex",
        )

        with patch.object(orchestrator.planner, 'create_plan', new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = plan

            with patch.object(orchestrator.student_agent, 'get_student_context', new_callable=AsyncMock) as mock_context:
                mock_context.return_value = {"name": "Alex", "disability_type": "autism", "student_id": "STU001"}

                with patch.object(orchestrator.plan_executor, 'execute', new_callable=AsyncMock) as mock_exec:
                    mock_exec.return_value = {
                        "response": "Here is Alex's profile",
                        "agents_used": ["STUDENT_AGENT"],
                    }

                    result = await orchestrator.process({"prompt": "Tell me about Alex"})

        assert "STUDENT_AGENT" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_plans_to_rag_agent(self, orchestrator, mock_memory_manager):
        """Plans strategy queries to RAGAgent."""
        from app.core.planner import ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.RAG_AGENT, task="Find ADHD strategies")],
            student_name=None,
            original_query="ADHD strategies",
        )

        with patch.object(orchestrator.planner, 'create_plan', new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = plan

            with patch.object(orchestrator.plan_executor, 'execute', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = {
                    "response": "Here are some strategies",
                    "agents_used": ["RAG_AGENT"],
                }

                result = await orchestrator.process({"prompt": "ADHD strategies"})

        assert "RAG_AGENT" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_plans_to_admin_agent(self, orchestrator, mock_memory_manager):
        """Plans admin queries to AdminAgent."""
        from app.core.planner import ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.ADMIN_AGENT, task="Write a report")],
            student_name=None,
            original_query="Write a report",
        )

        with patch.object(orchestrator.planner, 'create_plan', new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = plan

            with patch.object(orchestrator.plan_executor, 'execute', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = {
                    "response": "Here is your report",
                    "agents_used": ["ADMIN_AGENT"],
                }

                result = await orchestrator.process({"prompt": "Write a report"})

        assert "ADMIN_AGENT" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_multi_agent_plan(self, orchestrator, mock_memory_manager):
        """Multi-agent queries produce multi-step plans."""
        from app.core.planner import ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[
                PlanStep(step_index=0, agent=AgentType.STUDENT_AGENT, task="Get Alex's profile"),
                PlanStep(step_index=1, agent=AgentType.RAG_AGENT, task="Find strategies for Alex", depends_on=[0]),
            ],
            student_name="Alex",
            original_query="What strategies work for Alex?",
        )

        with patch.object(orchestrator.planner, 'create_plan', new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = plan

            with patch.object(orchestrator.student_agent, 'get_student_context', new_callable=AsyncMock) as mock_context:
                mock_context.return_value = {"name": "Alex", "student_id": "STU001", "profile": {}}

                with patch.object(orchestrator.plan_executor, 'execute', new_callable=AsyncMock) as mock_exec:
                    mock_exec.return_value = {
                        "response": "Personalized strategies for Alex",
                        "agents_used": ["STUDENT_AGENT", "RAG_AGENT"],
                        "student_name": "Alex",
                    }

                    result = await orchestrator.process({"prompt": "What strategies work for Alex?"})

        assert "STUDENT_AGENT" in result["agents_used"]
        assert "RAG_AGENT" in result["agents_used"]
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_tracks_steps(self, orchestrator, mock_step_tracker, mock_memory_manager):
        """Orchestrator returns tracked steps."""
        from app.core.planner import ExecutionPlan, PlanStep

        mock_step_tracker.get_steps.return_value = [
            {"module": "PLANNER", "prompt": {}, "response": {}}
        ]

        plan = ExecutionPlan(
            steps=[PlanStep(step_index=0, agent=AgentType.RAG_AGENT, task="Find strategies")],
            student_name=None,
            original_query="Test query",
        )

        with patch.object(orchestrator.planner, 'create_plan', new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = plan

            with patch.object(orchestrator.plan_executor, 'execute', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = {
                    "response": "Response",
                    "agents_used": ["RAG_AGENT"],
                }

                result = await orchestrator.process({"prompt": "Test query"})

        assert "steps" in result
        mock_step_tracker.get_steps.assert_called()


# ==================== Integration-style Tests ====================

class TestAgentInteraction:
    """Tests for agent interaction patterns."""

    @pytest.mark.asyncio
    async def test_student_context_flows_to_rag(
        self, mock_llm_client, mock_step_tracker, mock_memory_manager, mock_cache
    ):
        """Student context is properly passed to RAG agent."""
        with patch('app.agents.rag_agent.get_cache', return_value=mock_cache):
            rag = RAGAgent(
                llm_client=mock_llm_client,
                step_tracker=mock_step_tracker,
                memory_manager=mock_memory_manager
            )

        student_context = {
            "name": "Alex",
            "disability_type": "autism",
            "learning_style": "visual",
            "failed_methods": ["group work"]
        }

        result = await rag.process(
            {
                "prompt": "What strategies work?",
                "student_context": student_context
            }
        )

        # Verify the student context was used
        assert result["student_context_used"] is True

        # Verify methods were searched with correct filters
        call_kwargs = mock_memory_manager.search_teaching_methods.call_args.kwargs
        assert call_kwargs.get("disability_type") == "autism"
        assert call_kwargs.get("exclude_methods") == ["group work"]
