"""
Base Agent class.
Abstract base class for all agents in the system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.core.llm_client import LLMClient, get_llm_client
from app.core.step_tracker import StepTracker, get_step_tracker
from app.memory.memory_manager import MemoryManager, get_memory_manager


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Provides common functionality for LLM calls, step tracking, and memory access.
    """

    # Must be overridden by subclasses
    MODULE_NAME: str = "BASE_AGENT"

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        step_tracker: Optional[StepTracker] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        self.llm = llm_client or get_llm_client()
        self.tracker = step_tracker or get_step_tracker()
        self.memory = memory_manager or get_memory_manager()

    @abstractmethod
    async def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process input and return result.
        Must be implemented by subclasses.

        Args:
            input_data: The input to process
            context: Optional context from orchestrator

        Returns:
            Dict containing the agent's response
        """
        pass

    async def call_llm(
        self,
        messages: list,
        prompt_summary: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Call the LLM and automatically track the step.

        Args:
            messages: List of message dicts for the LLM
            prompt_summary: Summary of the prompt for step tracking
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            The LLM response content
        """
        # Make the LLM call
        result = await self.llm.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Handle None content
        content = result.get("content") or ""

        # Track the step
        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt=prompt_summary,
            response={
                "content": content[:500] if content else "(empty response)",
                "tokens": result.get("tokens_used", 0),
                "cost": result.get("cost", 0)
            }
        )

        return content

    async def call_llm_with_response_tracking(
        self,
        messages: list,
        prompt_summary: Dict[str, Any],
        response_summary: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Call the LLM with custom response summary for step tracking.
        Use this when you want to control what appears in the steps log.
        """
        result = await self.llm.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Track the step with custom response summary
        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt=prompt_summary,
            response=response_summary
        )

        return result.get("content") or ""

    def add_step(
        self,
        prompt: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """Manually add a step (for non-LLM operations)."""
        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt=prompt,
            response=response
        )

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Should be overridden by subclasses.
        """
        return f"You are the {self.MODULE_NAME} in the Co-Teacher system."

    def format_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Format context for inclusion in prompts."""
        if not context:
            return ""

        parts = []
        if "student_profile" in context:
            profile = context["student_profile"]
            parts.append(f"Student: {profile.get('name', 'Unknown')}")
            if profile.get("triggers"):
                parts.append(f"Triggers: {', '.join(profile['triggers'])}")
            if profile.get("successful_methods"):
                parts.append(f"Works: {', '.join(profile['successful_methods'])}")
            if profile.get("failed_methods"):
                parts.append(f"Avoid: {', '.join(profile['failed_methods'])}")

        if "daily_context" in context:
            for item in context["daily_context"][:3]:
                parts.append(f"Note: {item.get('content', '')}")

        return "\n".join(parts)
