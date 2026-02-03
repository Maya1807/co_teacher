"""
Step Tracker for tracking LLM calls.
Required for the steps[] array in /api/execute response.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from contextvars import ContextVar
import json


# Valid module names - must match architecture diagram
VALID_MODULES = ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT", "ADMIN_AGENT", "PREDICT_AGENT"]


@dataclass
class Step:
    """Represents a single execution step."""
    module: str
    prompt: Dict[str, Any]
    response: Dict[str, Any]

    def __post_init__(self):
        """Validate module name."""
        if self.module not in VALID_MODULES:
            raise ValueError(
                f"Invalid module '{self.module}'. Must be one of: {VALID_MODULES}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "module": self.module,
            "prompt": self.prompt,
            "response": self.response
        }


class StepTracker:
    """
    Tracks all LLM calls during agent execution.
    Thread-safe for single request (not shared across requests).
    """

    def __init__(self):
        self._steps: List[Step] = []

    def add_step(
        self,
        module: str,
        prompt: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """
        Add a new execution step.

        Args:
            module: Module name (must be in VALID_MODULES)
            prompt: The prompt/input sent to the module
            response: The response received from the module
        """
        step = Step(module=module, prompt=prompt, response=response)
        self._steps.append(step)

    def get_steps(self) -> List[Dict[str, Any]]:
        """Get all steps as a list of dictionaries."""
        return [step.to_dict() for step in self._steps]

    def clear(self) -> None:
        """Clear all recorded steps."""
        self._steps = []

    def __len__(self) -> int:
        """Return number of steps recorded."""
        return len(self._steps)

    def get_modules_used(self) -> List[str]:
        """Get list of unique modules used in order of first appearance."""
        seen = set()
        modules = []
        for step in self._steps:
            if step.module not in seen:
                seen.add(step.module)
                modules.append(step.module)
        return modules

    def get_steps_by_module(self, module: str) -> List[Dict[str, Any]]:
        """Get all steps for a specific module."""
        return [
            step.to_dict()
            for step in self._steps
            if step.module == module
        ]

    def to_json(self) -> str:
        """Serialize steps to JSON string."""
        return json.dumps(self.get_steps(), indent=2)


# Context variable for request-scoped step tracking (async-safe)
_current_tracker: ContextVar[Optional[StepTracker]] = ContextVar('step_tracker', default=None)


def get_step_tracker() -> StepTracker:
    """Get or create the current step tracker (request-scoped via ContextVar)."""
    tracker = _current_tracker.get()
    if tracker is None:
        tracker = StepTracker()
        _current_tracker.set(tracker)
    return tracker


def reset_step_tracker() -> StepTracker:
    """Reset and return a new step tracker (call at start of each request)."""
    tracker = StepTracker()
    _current_tracker.set(tracker)
    return tracker
