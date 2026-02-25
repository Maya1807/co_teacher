"""
Presenter Service.
Transforms agent responses into user-facing messages with consistent voice.
For multi-step plans, also merges multiple agent results into one response.
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING

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

    MODULE_NAME = "PRESENTER"

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

    @staticmethod
    def format_multi_step_content(
        step_results: List[Dict[str, Any]],
    ) -> str:
        """
        Format multiple agent results into a single content block
        for the presentation prompt.

        Args:
            step_results: List of dicts with 'agent' and 'response' keys

        Returns:
            Formatted content string
        """
        parts = []
        for sr in step_results:
            agent = sr.get("agent", "AGENT")
            response_text = sr.get("response", "")
            if response_text:
                parts.append(f"[{agent}]\n{response_text}")
        return "\n\n".join(parts)

    async def present(
        self,
        query: str,
        agent_response: str,
        skip_for_updates: bool = False
    ) -> str:
        """
        Transform agent response to friendly user-facing message.
        For multi-step plans, merges and transforms in a single LLM call.

        Args:
            query: Original user query
            agent_response: Raw response from agent(s), or pre-formatted
                multi-step content from format_multi_step_content()
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

        messages_sent = [{"role": "user", "content": prompt}]

        response = await self.llm.complete(
            messages=messages_sent,
            temperature=0.7,
        )

        content = response.get("content", agent_response)

        # Track step (include full messages for traceability)
        self.tracker.add_step(
            module=self.MODULE_NAME,
            prompt={
                "action": "present_response",
                "query_snippet": query,
                "original_length": len(agent_response),
                "messages": messages_sent,
            },
            response={
                "content": content,
                "tokens": response.get("tokens_used"),
                "cost": response.get("cost", 0)
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
