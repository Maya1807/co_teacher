"""
LLM Planner for the Co-Teacher system.
Decomposes teacher queries into step-by-step execution plans.
"""
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, TYPE_CHECKING

from app.core.router import AgentType

if TYPE_CHECKING:
    from app.core.llm_client import LLMClient
    from app.core.step_tracker import StepTracker


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_index: int
    agent: AgentType
    task: str
    depends_on: List[int] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionPlan:
    """A full execution plan with one or more steps."""
    steps: List[PlanStep]
    student_name: Optional[str]
    original_query: str

    @property
    def is_multi_step(self) -> bool:
        return len(self.steps) > 1

    @property
    def agents_involved(self) -> List[AgentType]:
        seen: Set[AgentType] = set()
        result: List[AgentType] = []
        for step in self.steps:
            if step.agent not in seen:
                seen.add(step.agent)
                result.append(step.agent)
        return result

    @property
    def needs_student_context(self) -> bool:
        return any(
            step.agent == AgentType.STUDENT_AGENT for step in self.steps
        )


# Map from string agent names to AgentType enum
_AGENT_NAME_MAP = {
    "STUDENT_AGENT": AgentType.STUDENT_AGENT,
    "RAG_AGENT": AgentType.RAG_AGENT,
    "ADMIN_AGENT": AgentType.ADMIN_AGENT,
    "PREDICT_AGENT": AgentType.PREDICT_AGENT,
}


class LLMPlanner:
    """
    Uses an LLM to decompose teacher queries into execution plans.
    Each plan is a list of PlanSteps with dependency ordering.
    """

    MODULE_NAME = "PLANNER"

    def __init__(
        self,
        llm_client: "LLMClient",
        step_tracker: "StepTracker"
    ):
        self.llm = llm_client
        self.tracker = step_tracker

    async def create_plan(
        self,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        Create an execution plan for a teacher query.

        Args:
            query: The teacher's request
            conversation_context: Optional context from conversation history

        Returns:
            ExecutionPlan with steps, student_name, and original_query
        """
        from app.utils.prompts import (
            PLANNER_SYSTEM,
            PLANNER_USER_PROMPT,
            PLANNER_CONTEXT_ADDENDUM,
        )

        prompt = PLANNER_USER_PROMPT.format(query=query)

        conv = conversation_context or {}
        recent_student = conv.get("recent_student")
        previous_agents = conv.get("previous_agents", [])
        history_summary = conv.get("history_summary")
        was_class_wide = conv.get("was_class_wide", False)
        mentioned_students = conv.get("mentioned_students", [])

        has_context = recent_student or previous_agents or history_summary or was_class_wide
        if has_context:
            prompt += PLANNER_CONTEXT_ADDENDUM.format(
                recent_student=recent_student or "Unknown",
                history_summary=history_summary or "No prior messages",
                previous_agents=", ".join(previous_agents) or "None",
                was_class_wide=was_class_wide,
                mentioned_students=", ".join(mentioned_students) if mentioned_students else "None",
            )

        response = await self.llm.complete(
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )

        content = response.get("content", "")

        # Track step
        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt={
                "action": "create_plan",
                "query_snippet": query[:100],
            },
            response={
                "content": content[:300],
                "tokens_used": response.get("tokens_used"),
            },
        )

        # Parse and validate
        try:
            plan = self._parse_plan(content, query)
            return plan
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            return self._fallback_plan(query)

    def _parse_plan(self, content: str, query: str) -> ExecutionPlan:
        """Parse LLM JSON response into an ExecutionPlan. Raises on invalid data."""
        # Clean markdown code fences
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        raw_steps = data.get("steps", [])
        student_name = data.get("student_name")

        if not raw_steps:
            raise ValueError("Plan has no steps")

        steps: List[PlanStep] = []
        for raw in raw_steps:
            agent_str = raw["agent"]
            if agent_str not in _AGENT_NAME_MAP:
                raise ValueError(f"Unknown agent: {agent_str}")

            step_index = raw["step_index"]
            depends_on = raw.get("depends_on", [])

            # Validate depends_on: no self-refs, no forward refs
            for dep in depends_on:
                if dep >= step_index:
                    raise ValueError(
                        f"Step {step_index} has invalid dependency on step {dep}"
                    )

            steps.append(
                PlanStep(
                    step_index=step_index,
                    agent=_AGENT_NAME_MAP[agent_str],
                    task=raw["task"],
                    depends_on=depends_on,
                )
            )

        return ExecutionPlan(
            steps=steps,
            student_name=student_name,
            original_query=query,
        )

    def _fallback_plan(self, query: str) -> ExecutionPlan:
        """Return a single-step RAG_AGENT plan as fallback."""
        return ExecutionPlan(
            steps=[
                PlanStep(
                    step_index=0,
                    agent=AgentType.RAG_AGENT,
                    task=query,
                    depends_on=[],
                )
            ],
            student_name=None,
            original_query=query,
        )
