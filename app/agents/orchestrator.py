"""
Orchestrator Agent.
Coordinates between agents and services to process teacher queries.

Refactored to use separated services:
- ConversationService: Conversation CRUD
- ContextResolver: Context extraction and student resolution
- Router: Query routing with LLM fallback
- AgentExecutor: Agent dispatch
- ResponseCombiner: Multi-agent synthesis
- Presenter: Voice transformation
"""
from typing import Dict, Any, Optional

from app.agents.base_agent import BaseAgent
from app.agents.student_agent import StudentAgent
from app.agents.rag_agent import RAGAgent
from app.agents.admin_agent import AdminAgent
from app.agents.predict_agent import PredictAgent
from app.core.router import RuleBasedRouter, AgentType
from app.services.conversation_service import ConversationService
from app.services.context_resolver import ContextResolver
from app.services.agent_executor import AgentExecutor
from app.services.response_combiner import ResponseCombiner
from app.services.presenter import Presenter


# Maximum number of previous messages to include for context
MAX_HISTORY_MESSAGES = 6

# Set to True to always use LLM routing (bypass rule-based router)
USE_LLM_ROUTING = True


class Orchestrator(BaseAgent):
    """
    Central orchestrator for the Co-Teacher system.

    Simplified coordinator that delegates to specialized services:
    - ConversationService: Handles conversation persistence
    - ContextResolver: Extracts context and resolves student identity
    - Router: Routes queries to appropriate agents
    - AgentExecutor: Executes individual agents
    - ResponseCombiner: Synthesizes multi-agent responses
    - Presenter: Applies voice transformation

    Flow: Query -> Route -> Resolve -> Execute -> Present -> Response
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
        self._router: Optional[RuleBasedRouter] = None
        self._conversation_service: Optional[ConversationService] = None
        self._context_resolver: Optional[ContextResolver] = None
        self._agent_executor: Optional[AgentExecutor] = None
        self._response_combiner: Optional[ResponseCombiner] = None
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
    def router(self) -> RuleBasedRouter:
        if self._router is None:
            self._router = RuleBasedRouter(
                llm_client=self.llm,
                step_tracker=self.tracker
            )
        return self._router

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
    def agent_executor(self) -> AgentExecutor:
        if self._agent_executor is None:
            self._agent_executor = AgentExecutor(
                student_agent=self.student_agent,
                rag_agent=self.rag_agent,
                admin_agent=self.admin_agent,
                predict_agent=self.predict_agent
            )
        return self._agent_executor

    @property
    def presenter(self) -> Presenter:
        if self._presenter is None:
            self._presenter = Presenter(
                llm_client=self.llm,
                step_tracker=self.tracker,
                enabled=self._presentation_enabled
            )
        return self._presenter

    @property
    def response_combiner(self) -> ResponseCombiner:
        if self._response_combiner is None:
            self._response_combiner = ResponseCombiner(
                llm_client=self.llm,
                step_tracker=self.tracker,
                student_agent=self.student_agent,
                rag_agent=self.rag_agent,
                presenter=self.presenter
            )
        return self._response_combiner

    # ==================== Main Process Method ====================

    async def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a teacher query through the multi-agent system.

        Simplified flow:
        1. Validate input
        2. Manage conversation (get/create, store user message)
        3. Route query
        4. Resolve context (conversation + student)
        5. Execute agent(s)
        6. Present response (optional voice transformation)
        7. Store response

        Args:
            input_data: Contains 'prompt' and optional 'session_id'
            context: Optional context with teacher_id, previous_agents

        Returns:
            Dict with 'response', 'agents_used', 'steps', etc.
        """
        query = input_data.get("prompt", "")
        session_id = input_data.get("session_id", "default")
        teacher_id = context.get("teacher_id") if context else None

        # Clear steps from previous request
        self.tracker.clear()

        # Step 1: Validate input
        if not query.strip():
            return self._empty_query_response()

        # Step 2: Conversation management
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

        # Step 3: Route query
        conv_context = self.context_resolver.extract_conversation_context(history)

        if USE_LLM_ROUTING:
            # Always use LLM routing (for testing/demo)
            routing_result = await self.router.route_with_fallback(
                query,
                conversation_context=conv_context,
                context=context,
                use_llm_fallback=True
            )
        else:
            # Rule-based with LLM fallback
            routing_result = await self.router.route_with_fallback(
                query,
                conversation_context=conv_context,
                context=context,
                use_llm_fallback=True
            )

        # Step 4: Resolve student context
        student_name = routing_result.extracted_entities.get("name")
        if not student_name and conv_context.get("recent_student"):
            student_name = conv_context["recent_student"]

        student_context = None
        should_get_student = (
            student_name or AgentType.STUDENT_AGENT in routing_result.agents
        )

        if should_get_student:
            student_context = await self.student_agent.get_student_context(
                student_name=student_name
            )

        # Step 5: Execute agent(s)
        if routing_result.is_multi_agent and student_context:
            # Multi-agent: use ResponseCombiner
            combined_result = await self.response_combiner.combine_personalized_response(
                query=query,
                routing_result=routing_result,
                student_context=student_context,
                context=context
            )
            final_response = combined_result.response
            agents_used = [self.MODULE_NAME] + [a.value for a in routing_result.agents]
            updates_applied = combined_result.updates_applied
            result_student_name = combined_result.student_name
        else:
            # Single agent: use AgentExecutor
            agent_result = await self.agent_executor.execute(
                agent_type=routing_result.agent,
                query=query,
                student_context=student_context,
                context=context
            )
            raw_response = agent_result.get("response", "")

            # Apply presentation (skip for update confirmations)
            skip_presentation = agent_result.get("action_taken") == "update_applied"
            final_response = await self.presenter.present(
                query, raw_response, skip_for_updates=skip_presentation
            )

            agents_used = [self.MODULE_NAME, routing_result.agent.value]
            updates_applied = agent_result.get("updates_applied")
            result_student_name = agent_result.get("student_name")

        # Step 6: Store assistant response
        await self.conversation_service.add_assistant_message(
            conversation_id=conversation_id,
            content=final_response,
            agent_used=agents_used[-1] if agents_used else None
        )

        # Step 7: Build and return result
        return {
            "response": final_response,
            "agents_used": agents_used,
            "agent_used": agents_used[-1] if agents_used else None,
            "router_confidence": routing_result.confidence,
            "routing": {
                "agents": [a.value for a in routing_result.agents],
                "is_multi_agent": routing_result.is_multi_agent,
                "confidence": routing_result.confidence,
                "student_name": student_name
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
            "routing": {"reason": "empty_query"}
        }

    def _conversation_error_response(self) -> Dict[str, Any]:
        """Return response for conversation error."""
        return {
            "response": "I'm having trouble maintaining our conversation. Please try again.",
            "agents_used": [self.MODULE_NAME],
            "routing": {"reason": "conversation_error"}
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
