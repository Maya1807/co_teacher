"""
Presenter Service.
Transforms agent responses into user-facing messages with consistent voice.
"""
from typing import Optional, TYPE_CHECKING

from app.utils.prompts import FINAL_PRESENTATION_PROMPT

if TYPE_CHECKING:
    from app.core.llm_client import LLMClient
    from app.core.step_tracker import StepTracker


class Presenter:
    """
    Transforms agent responses into friendly, user-facing messages.

    This is the final presentation layer that applies consistent voice/tone.
    Can be disabled for simple responses or when voice transformation isn't needed.

    Extracted from orchestrator to separate presentation concerns.
    """

    MODULE_NAME = "ORCHESTRATOR"  # Steps tracked under orchestrator

    def __init__(
        self,
        llm_client: "LLMClient",
        step_tracker: "StepTracker",
        enabled: bool = True
    ):
        """
        Initialize presenter.

        Args:
            llm_client: LLM client for voice transformation
            step_tracker: Step tracker for logging
            enabled: Whether presentation is enabled (default True)
        """
        self.llm = llm_client
        self.tracker = step_tracker
        self.enabled = enabled

    async def present(
        self,
        query: str,
        agent_response: str,
        skip_for_updates: bool = False
    ) -> str:
        """
        Transform agent response to friendly user-facing message.

        Args:
            query: Original user query
            agent_response: Raw response from agent(s)
            skip_for_updates: If True, return response as-is (for update confirmations)

        Returns:
            Transformed response (or original if disabled/skipped)
        """
        if not self.enabled or skip_for_updates:
            return agent_response

        prompt = FINAL_PRESENTATION_PROMPT.format(
            query=query,
            agent_response=agent_response
        )

        response = await self.llm.complete(
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )

        content = response.get("content", agent_response)

        # Track step
        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt={
                "action": "present_response",
                "query_snippet": query[:50],
                "original_length": len(agent_response)
            },
            response={
                "content": content[:200],
                "tokens_used": response.get("tokens_used")
            }
        )

        return content

    def set_enabled(self, enabled: bool):
        """
        Enable or disable presentation.

        Args:
            enabled: Whether to enable presentation
        """
        self.enabled = enabled
