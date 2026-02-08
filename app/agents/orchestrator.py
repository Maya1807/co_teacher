"""
Orchestrator Agent.
Coordinates between agents and services to process teacher queries.

Uses an LLM Planner to decompose queries into step-by-step execution
plans, then a PlanExecutor to run them with dependency ordering.

Services:
- ConversationService: Conversation CRUD
- ContextResolver: Context extraction and student resolution
- LLMPlanner: Query → execution plan
- PlanExecutor: Plan → agent results
- Presenter: Voice transformation
"""
from typing import Dict, Any, Optional

from app.agents.base_agent import BaseAgent
from app.agents.student_agent import StudentAgent
from app.agents.rag_agent import RAGAgent
from app.agents.admin_agent import AdminAgent
from app.agents.predict_agent import PredictAgent
from app.core.planner import LLMPlanner
from app.services.conversation_service import ConversationService
from app.services.context_resolver import ContextResolver
from app.services.plan_executor import PlanExecutor
from app.services.presenter import Presenter


# Maximum number of previous messages to include for context
MAX_HISTORY_MESSAGES = 6


class Orchestrator(BaseAgent):
    """
    Central orchestrator for the Co-Teacher system.

    Coordinator that delegates to specialized services:
    - ConversationService: Handles conversation persistence
    - ContextResolver: Extracts context and resolves student identity
    - LLMPlanner: Decomposes queries into execution plans
    - PlanExecutor: Executes plans step-by-step
    - Presenter: Applies voice transformation

    Flow: Query -> Plan -> Resolve student -> Execute plan -> Present -> Response
    """

    MODULE_NAME = "ORCHESTRATOR"

    def __init__(self, *args, presentation_enabled: bool = True, **kwargs):
        super().__init__(*args, **kwargs)

        self._presentation_enabled = presentation_enabled

        # Lazy-initialized agents
        self._student_agent: Optional[StudentAgent] = None
        self._rag_agent: Optional[RAGAgent] = None
        self._admin_agent: Optional[AdminAgent] = None
        self._predict_agent: Optional[PredictAgent] = None

        # Lazy-initialized services
        self._planner: Optional[LLMPlanner] = None
        self._plan_executor: Optional[PlanExecutor] = None
        self._conversation_service: Optional[ConversationService] = None
        self._context_resolver: Optional[ContextResolver] = None
        self._presenter: Optional[Presenter] = None

    # ==================== Lazy Agent Properties ====================

    @property
    def student_agent(self) -> StudentAgent:
        if self._student_agent is None:
            self._student_agent = StudentAgent(
                llm_client=self.llm,
                step_tracker=self.tracker,
                memory_manager=self.memory
            )
        return self._student_agent

    @property
    def rag_agent(self) -> RAGAgent:
        if self._rag_agent is None:
            self._rag_agent = RAGAgent(
                llm_client=self.llm,
                step_tracker=self.tracker,
                memory_manager=self.memory
            )
        return self._rag_agent

    @property
    def admin_agent(self) -> AdminAgent:
        if self._admin_agent is None:
            self._admin_agent = AdminAgent(
                llm_client=self.llm,
                step_tracker=self.tracker,
                memory_manager=self.memory
            )
        return self._admin_agent

    @property
    def predict_agent(self) -> PredictAgent:
        if self._predict_agent is None:
            self._predict_agent = PredictAgent(
                llm_client=self.llm,
                step_tracker=self.tracker,
                memory_manager=self.memory
            )
        return self._predict_agent

    # ==================== Lazy Service Properties ====================

    @property
    def planner(self) -> LLMPlanner:
        if self._planner is None:
            self._planner = LLMPlanner(
                llm_client=self.llm,
                step_tracker=self.tracker
            )
        return self._planner

    @property
    def plan_executor(self) -> PlanExecutor:
        if self._plan_executor is None:
            self._plan_executor = PlanExecutor(
                student_agent=self.student_agent,
                rag_agent=self.rag_agent,
                admin_agent=self.admin_agent,
                predict_agent=self.predict_agent,
                llm_client=self.llm,
                step_tracker=self.tracker,
                presenter=self.presenter,
            )
        return self._plan_executor

    @property
    def conversation_service(self) -> ConversationService:
        if self._conversation_service is None:
            self._conversation_service = ConversationService(self.memory)
        return self._conversation_service

    @property
    def context_resolver(self) -> ContextResolver:
        if self._context_resolver is None:
            self._context_resolver = ContextResolver(self.student_agent)
        return self._context_resolver

    @property
    def presenter(self) -> Presenter:
        if self._presenter is None:
            self._presenter = Presenter(
                llm_client=self.llm,
                step_tracker=self.tracker,
                enabled=self._presentation_enabled
            )
        return self._presenter

    # ==================== Main Process Method ====================

    async def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a teacher query through the multi-agent system.

        Flow:
        1. Validate input
        2. Manage conversation (get/create, store user message)
        3. Extract conversation context
        4. Create execution plan (LLM planner)
        5. Resolve student context
        6. Execute plan
        7. Store response

        Args:
            input_data: Contains 'prompt' and optional 'session_id'
            context: Optional context with teacher_id, previous_agents

        Returns:
            Dict with 'response', 'agents_used', 'steps', etc.
        """
        # --- 1. Extract request parameters ---
        query = input_data.get("prompt", "")
        session_id = input_data.get("session_id", "default")
        teacher_id = context.get("teacher_id") if context else None

        # Wipe any steps left over from a previous call
        self.tracker.clear()

        # --- 2. Validate input ---
        if not query.strip():
            return self._empty_query_response()

        # --- 3. Conversation management (Supabase) ---
        conversation = await self.conversation_service.get_or_create_conversation(
            session_id=session_id,
            teacher_id=teacher_id
        )
        conversation_id = conversation.get("id")

        if not conversation_id:
            return self._conversation_error_response()

        await self.conversation_service.add_user_message(conversation_id, query)
        history = await self.conversation_service.get_history(
            conversation_id, MAX_HISTORY_MESSAGES
        )

        # --- 4. Create execution plan ---
        conv_context = self.context_resolver.extract_conversation_context(history)
        plan = await self.planner.create_plan(query, conv_context)

        # --- 5. Resolve student context ---
        student_name = plan.student_name
        if not student_name and conv_context.get("recent_student"):
            student_name = conv_context["recent_student"]

        student_context = None
        all_students_context = None

        if student_name == "ALL_STUDENTS":
            all_students_context = await self.memory.list_students()
        elif student_name or plan.needs_student_context:
            student_context = await self.student_agent.get_student_context(
                student_name=student_name
            )

        # --- 6. Execute the plan ---
        result = await self.plan_executor.execute(
            plan=plan,
            student_context=student_context,
            all_students_context=all_students_context,
            context=context,
        )

        final_response = result["response"]
        agents_used = [self.MODULE_NAME] + result.get("agents_used", [])
        updates_applied = result.get("updates_applied")
        result_student_name = result.get("student_name")

        # --- 7. Persist the assistant's response ---
        await self.conversation_service.add_assistant_message(
            conversation_id=conversation_id,
            content=final_response,
            agent_used=agents_used[-1] if agents_used else None
        )

        # --- 8. Build and return the result dict ---
        return {
            "response": final_response,
            "agents_used": agents_used,
            "agent_used": agents_used[-1] if agents_used else None,
            "plan": {
                "steps": [
                    {
                        "step_index": s.step_index,
                        "agent": s.agent.value,
                        "task": s.task,
                        "depends_on": s.depends_on,
                    }
                    for s in plan.steps
                ],
                "is_multi_step": plan.is_multi_step,
                "student_name": student_name,
            },
            "student_context": student_context,
            "conversation_id": conversation_id,
            "conversation_context": conv_context,
            "steps": self.tracker.get_steps(),
            "updates_applied": updates_applied,
            "student_name": result_student_name or student_name
        }

    # ==================== Helper Methods ====================

    def _empty_query_response(self) -> Dict[str, Any]:
        """Return response for empty query."""
        return {
            "response": "I didn't receive a message. How can I help you today?",
            "agents_used": [self.MODULE_NAME],
            "plan": {"reason": "empty_query"}
        }

    def _conversation_error_response(self) -> Dict[str, Any]:
        """Return response for conversation error."""
        return {
            "response": "I'm having trouble maintaining our conversation. Please try again.",
            "agents_used": [self.MODULE_NAME],
            "plan": {"reason": "conversation_error"}
        }


# Singleton for easy access
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create the orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def reset_orchestrator() -> Orchestrator:
    """Reset the orchestrator (useful for testing)."""
    global _orchestrator
    _orchestrator = Orchestrator()
    return _orchestrator
