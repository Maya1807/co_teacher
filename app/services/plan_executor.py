"""
Plan Executor.
Executes an ExecutionPlan step-by-step with dependency awareness.
"""
from typing import Dict, Any, Optional, TYPE_CHECKING

from app.core.router import AgentType
from app.core.planner import ExecutionPlan, PlanStep
from app.utils.prompts import PLAN_SYNTHESIS_PROMPT

if TYPE_CHECKING:
    from app.agents.student_agent import StudentAgent
    from app.agents.rag_agent import RAGAgent
    from app.agents.admin_agent import AdminAgent
    from app.agents.predict_agent import PredictAgent
    from app.core.llm_client import LLMClient
    from app.core.step_tracker import StepTracker
    from app.services.presenter import Presenter


class PlanExecutor:
    """
    Executes an ExecutionPlan by running each step's agent
    in dependency order and optionally synthesizing multi-step results.
    """

    MODULE_NAME = "ORCHESTRATOR"

    def __init__(
        self,
        student_agent: "StudentAgent",
        rag_agent: "RAGAgent",
        admin_agent: "AdminAgent",
        predict_agent: "PredictAgent",
        llm_client: "LLMClient",
        step_tracker: "StepTracker",
        presenter: "Presenter",
    ):
        self._agents = {
            AgentType.STUDENT_AGENT: student_agent,
            AgentType.RAG_AGENT: rag_agent,
            AgentType.ADMIN_AGENT: admin_agent,
            AgentType.PREDICT_AGENT: predict_agent,
        }
        self.llm = llm_client
        self.tracker = step_tracker
        self.presenter = presenter

    async def execute(
        self,
        plan: ExecutionPlan,
        student_context: Optional[Dict[str, Any]] = None,
        all_students_context: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute all steps in the plan sequentially (topological order).

        Args:
            plan: The execution plan from LLMPlanner
            student_context: Optional resolved student profile context
            all_students_context: Optional list of all student profiles (for class-wide queries)
            context: Optional request context (teacher_id, etc.)

        Returns:
            Dict with 'response', 'agents_used', 'updates_applied', 'student_name'
        """
        agents_used = []
        updates_applied = None
        result_student_name = None

        for step in plan.steps:
            # Build input_data for this step
            input_data = self._build_input_data(
                step, plan, student_context
            )

            if all_students_context:
                input_data["all_students_context"] = all_students_context

            # Execute the agent
            agent = self._agents.get(step.agent)
            if not agent:
                continue

            result = await agent.process(input_data, context)
            step.result = result

            if step.agent.value not in agents_used:
                agents_used.append(step.agent.value)

            # Track student-related metadata
            if result.get("student_name"):
                result_student_name = result["student_name"]
            if result.get("updates_applied"):
                updates_applied = result["updates_applied"]

            # Short-circuit on pure update (no question asked)
            if (
                step.agent == AgentType.STUDENT_AGENT
                and result.get("action_taken") == "update_applied"
                and not self._is_asking_question(plan.original_query)
            ):
                final_response = await self.presenter.present(
                    plan.original_query,
                    result.get("response", ""),
                    skip_for_updates=True,
                )
                return {
                    "response": final_response,
                    "agents_used": agents_used,
                    "updates_applied": updates_applied,
                    "student_name": result_student_name or plan.student_name,
                }

        # All steps done — produce final response
        if plan.is_multi_step:
            raw_response = await self._synthesize(plan)
        else:
            # Single step — use its response directly
            raw_response = plan.steps[0].result.get("response", "") if plan.steps else ""

        # Apply presentation unless it was a pure update
        skip_presentation = (
            plan.steps
            and plan.steps[-1].result
            and plan.steps[-1].result.get("action_taken") == "update_applied"
        )
        final_response = await self.presenter.present(
            plan.original_query,
            raw_response,
            skip_for_updates=skip_presentation,
        )

        return {
            "response": final_response,
            "agents_used": agents_used,
            "updates_applied": updates_applied,
            "student_name": result_student_name or plan.student_name,
        }

    def _build_input_data(
        self,
        step: PlanStep,
        plan: ExecutionPlan,
        student_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the input_data dict for an agent from the step and prior results."""
        task = step.task

        # Enrich task with prior step results when there are dependencies
        if step.depends_on:
            task = self._enrich_task_with_context(task, step, plan, student_context)

        input_data: Dict[str, Any] = {
            "prompt": task,
            "original_query": plan.original_query,
        }

        if student_context:
            input_data["student_context"] = student_context
            input_data["student_name"] = student_context.get("name")
            input_data["student_id"] = student_context.get("student_id")

        return input_data

    def _enrich_task_with_context(
        self,
        task: str,
        step: PlanStep,
        plan: ExecutionPlan,
        student_context: Optional[Dict[str, Any]],
    ) -> str:
        """Append summaries of dependency step results below the task string."""
        parts = [task]

        for dep_idx in step.depends_on:
            dep_step = plan.steps[dep_idx] if dep_idx < len(plan.steps) else None
            if dep_step and dep_step.result:
                response_text = dep_step.result.get("response", "")
                if response_text:
                    parts.append(
                        f"\n--- Context from {dep_step.agent.value} (step {dep_idx}) ---\n"
                        f"{response_text}"
                    )

        if student_context and student_context.get("name"):
            profile = student_context.get("profile", {})
            if profile:
                summary_parts = []
                if profile.get("disability_type"):
                    summary_parts.append(f"Disability: {profile['disability_type']}")
                if profile.get("learning_style"):
                    summary_parts.append(f"Learning style: {profile['learning_style']}")
                if profile.get("triggers"):
                    summary_parts.append(f"Triggers: {', '.join(profile['triggers'][:3])}")
                if profile.get("successful_methods"):
                    summary_parts.append(f"What works: {', '.join(profile['successful_methods'][:3])}")
                if profile.get("failed_methods"):
                    summary_parts.append(f"Avoid: {', '.join(profile['failed_methods'][:3])}")
                if summary_parts:
                    parts.append(
                        f"\n--- Student profile ({student_context['name']}) ---\n"
                        + "\n".join(summary_parts)
                    )

        return "\n".join(parts)

    async def _synthesize(self, plan: ExecutionPlan) -> str:
        """Synthesize results from multiple steps into one response."""
        step_results_parts = []
        for step in plan.steps:
            if step.result:
                response_text = step.result.get("response", "(no response)")
                step_results_parts.append(
                    f"[{step.agent.value} — step {step.step_index}]\n{response_text}"
                )

        step_results_text = "\n\n".join(step_results_parts)

        prompt = PLAN_SYNTHESIS_PROMPT.format(
            query=plan.original_query,
            step_results=step_results_text,
        )

        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )

        content = response.get("content", "")

        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt={
                "action": "synthesize_plan_results",
                "query_snippet": plan.original_query[:100],
                "num_steps": len(plan.steps),
            },
            response={
                "content": content[:200],
                "tokens_used": response.get("tokens_used"),
            },
        )

        return content

    @staticmethod
    def _is_asking_question(query: str) -> bool:
        """Check if query is asking a question vs just sharing information."""
        question_starters = ["how", "what", "can you", "could you", "help me"]
        return "?" in query or any(
            query.lower().startswith(w) for w in question_starters
        )
