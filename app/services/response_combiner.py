"""
Response Combiner.
Synthesizes responses from multiple agents for personalized queries.
"""
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

from app.core.router import AgentType, RoutingResult
from app.utils.prompts import PERSONALIZED_STRATEGY_PROMPT

if TYPE_CHECKING:
    from app.core.llm_client import LLMClient
    from app.core.step_tracker import StepTracker
    from app.agents.student_agent import StudentAgent
    from app.agents.rag_agent import RAGAgent
    from app.services.presenter import Presenter


@dataclass
class CombinedResult:
    """Result of multi-agent synthesis."""
    response: str
    updates_applied: Optional[Dict[str, Any]] = None
    student_name: Optional[str] = None


class ResponseCombiner:
    """
    Synthesizes responses from multiple agents for personalized queries.

    Handles the complex case where StudentAgent + RAGAgent need to work
    together to provide personalized teaching strategy recommendations.

    Extracted from orchestrator to separate multi-agent synthesis concerns.
    """

    MODULE_NAME = "ORCHESTRATOR"  # Steps tracked under orchestrator

    def __init__(
        self,
        llm_client: "LLMClient",
        step_tracker: "StepTracker",
        student_agent: "StudentAgent",
        rag_agent: "RAGAgent",
        presenter: "Presenter"
    ):
        """
        Initialize with required dependencies.

        Args:
            llm_client: LLM client for synthesis
            step_tracker: Step tracker for logging
            student_agent: StudentAgent for profile updates
            rag_agent: RAGAgent for teaching methods
            presenter: Presenter for voice transformation
        """
        self.llm = llm_client
        self.tracker = step_tracker
        self.student_agent = student_agent
        self.rag_agent = rag_agent
        self.presenter = presenter

    async def combine_personalized_response(
        self,
        query: str,
        routing_result: RoutingResult,
        student_context: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CombinedResult:
        """
        Handle queries needing both student info and RAG methods.
        Creates a unified, personalized response.

        Args:
            query: The user's query
            routing_result: Result from router with agent list
            student_context: Student profile and context
            context: Optional additional context

        Returns:
            CombinedResult with response, updates_applied, student_name
        """
        profile = student_context.get("profile", {})
        student_name = profile.get("name", "the student")
        student_id = student_context.get("student_id")

        # Step 1: Check if query contains update info via student agent
        updates_applied = None
        update_confirmation = ""

        if AgentType.STUDENT_AGENT in routing_result.agents and student_id:
            student_result = await self.student_agent.process(
                {
                    "prompt": query,
                    "student_id": student_id,
                    "action": "query"  # Will auto-detect updates
                },
                context
            )

            updates_applied = student_result.get("updates_applied")
            student_action = student_result.get("action_taken")

            if updates_applied:
                update_confirmation = student_result.get("response", "")
                # Use updated profile
                profile = student_result.get("student_profile", profile)
                student_context["profile"] = profile

            # If items already exist in profile, return early
            if student_action == "already_exists":
                return CombinedResult(
                    response=student_result.get("response", ""),
                    updates_applied=None,
                    student_name=student_name
                )

        # Step 2: If updates applied and not asking a question, just confirm
        if updates_applied and not self._is_asking_question(query):
            return CombinedResult(
                response=update_confirmation,
                updates_applied=updates_applied,
                student_name=student_name
            )

        # Step 3: Get relevant teaching methods if RAG_AGENT is needed
        methods_info = ""
        if AgentType.RAG_AGENT in routing_result.agents:
            rag_result = await self.rag_agent.get_relevant_methods(
                query=query,
                student_context=student_context
            )
            methods_info = rag_result.get("methods_summary", "")

        # Step 4: Format student profile for the prompt
        student_summary = self._format_student_summary(profile)

        # Step 5: Synthesize using LLM
        prompt = PERSONALIZED_STRATEGY_PROMPT.format(
            query=query,
            student_name=student_name,
            student_profile=student_summary,
            methods=methods_info
        )

        response = await self.llm.complete(
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )

        raw_content = response.get("content", "")

        # Track step
        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt={
                "action": "synthesize_personalized_content",
                "student": student_name,
                "query_snippet": query[:100]
            },
            response={
                "content": raw_content[:200],
                "tokens_used": response.get("tokens_used")
            }
        )

        # Step 6: Apply voice through presentation layer
        final_response = await self.presenter.present(query, raw_content)

        # Step 7: Prepend update confirmation if updates were applied
        if update_confirmation and updates_applied:
            final_response = f"{update_confirmation}\n\n{final_response}"

        return CombinedResult(
            response=final_response,
            updates_applied=updates_applied,
            student_name=student_name
        )

    def _format_student_summary(self, profile: Dict[str, Any]) -> str:
        """
        Format student profile into a concise summary for prompts.

        Args:
            profile: Student profile dict

        Returns:
            Formatted summary string
        """
        if not profile:
            return "No profile available"

        parts = []
        if profile.get("disability_type"):
            parts.append(f"- Has {profile['disability_type']}")
        if profile.get("learning_style"):
            parts.append(f"- {profile['learning_style']} learner")
        if profile.get("successful_methods"):
            methods = profile["successful_methods"][:3]  # Top 3
            parts.append(f"- Responds well to: {', '.join(methods)}")
        if profile.get("triggers"):
            triggers = profile["triggers"][:2]  # Top 2
            parts.append(f"- Triggers: {', '.join(triggers)}")
        if profile.get("failed_methods"):
            avoid = profile["failed_methods"][:2]  # Top 2
            parts.append(f"- Avoid: {', '.join(avoid)}")

        return "\n".join(parts) if parts else "Limited profile information"

    def _is_asking_question(self, query: str) -> bool:
        """
        Check if query is asking a question vs just sharing information.

        Args:
            query: The user's query

        Returns:
            True if the query is asking a question
        """
        question_starters = ["how", "what", "can you", "could you", "help me"]
        return "?" in query or any(
            query.lower().startswith(w) for w in question_starters
        )
