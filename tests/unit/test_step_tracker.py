"""
Unit tests for StepTracker.
Tests step tracking for /api/execute response compliance.
"""
import pytest
from app.core.step_tracker import (
    StepTracker,
    Step,
    VALID_MODULES,
    get_step_tracker,
    reset_step_tracker
)


class TestStep:
    """Tests for the Step dataclass."""

    def test_valid_step_creation(self):
        """Can create a step with valid module name."""
        step = Step(
            module="ORCHESTRATOR",
            prompt={"text": "Test prompt"},
            response={"result": "Test response"}
        )
        assert step.module == "ORCHESTRATOR"
        assert step.prompt == {"text": "Test prompt"}
        assert step.response == {"result": "Test response"}

    def test_invalid_module_raises_error(self):
        """Invalid module name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Step(
                module="INVALID_AGENT",
                prompt={},
                response={}
            )
        assert "Invalid module" in str(exc_info.value)

    def test_all_valid_modules(self):
        """All valid modules can be used."""
        for module in VALID_MODULES:
            step = Step(module=module, prompt={}, response={})
            assert step.module == module

    def test_to_dict(self):
        """Step converts to dictionary correctly."""
        step = Step(
            module="RAG_AGENT",
            prompt={"query": "test"},
            response={"methods": ["method1"]}
        )
        result = step.to_dict()

        assert result["module"] == "RAG_AGENT"
        assert result["prompt"] == {"query": "test"}
        assert result["response"] == {"methods": ["method1"]}


class TestStepTracker:
    """Tests for the StepTracker class."""

    def test_add_step_with_required_fields(self):
        """Each step has module, prompt, response."""
        tracker = StepTracker()
        tracker.add_step(
            module="ORCHESTRATOR",
            prompt={"text": "Route this request"},
            response={"agent": "STUDENT_AGENT"}
        )
        steps = tracker.get_steps()

        assert len(steps) == 1
        assert "module" in steps[0]
        assert "prompt" in steps[0]
        assert "response" in steps[0]

    def test_module_names_match_architecture(self):
        """Module names must match architecture diagram exactly."""
        tracker = StepTracker()

        for module in VALID_MODULES:
            tracker.add_step(module=module, prompt={}, response={})

        steps = tracker.get_steps()
        for step in steps:
            assert step["module"] in VALID_MODULES

    def test_preserves_step_order(self):
        """Steps returned in order they were added."""
        tracker = StepTracker()
        tracker.add_step(module="ORCHESTRATOR", prompt={"step": 1}, response={})
        tracker.add_step(module="STUDENT_AGENT", prompt={"step": 2}, response={})
        tracker.add_step(module="ORCHESTRATOR", prompt={"step": 3}, response={})

        steps = tracker.get_steps()
        assert steps[0]["prompt"]["step"] == 1
        assert steps[1]["prompt"]["step"] == 2
        assert steps[2]["prompt"]["step"] == 3

    def test_clear_steps(self):
        """Can clear steps for new request."""
        tracker = StepTracker()
        tracker.add_step(module="ORCHESTRATOR", prompt={}, response={})
        tracker.add_step(module="STUDENT_AGENT", prompt={}, response={})

        assert len(tracker) == 2

        tracker.clear()

        assert len(tracker) == 0
        assert tracker.get_steps() == []

    def test_len_returns_step_count(self):
        """__len__ returns correct count."""
        tracker = StepTracker()
        assert len(tracker) == 0

        tracker.add_step(module="ORCHESTRATOR", prompt={}, response={})
        assert len(tracker) == 1

        tracker.add_step(module="RAG_AGENT", prompt={}, response={})
        assert len(tracker) == 2

    def test_get_modules_used(self):
        """Get unique modules in order of first appearance."""
        tracker = StepTracker()
        tracker.add_step(module="ORCHESTRATOR", prompt={}, response={})
        tracker.add_step(module="STUDENT_AGENT", prompt={}, response={})
        tracker.add_step(module="ORCHESTRATOR", prompt={}, response={})
        tracker.add_step(module="RAG_AGENT", prompt={}, response={})

        modules = tracker.get_modules_used()

        assert modules == ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT"]

    def test_get_steps_by_module(self):
        """Can filter steps by module."""
        tracker = StepTracker()
        tracker.add_step(module="ORCHESTRATOR", prompt={"id": 1}, response={})
        tracker.add_step(module="STUDENT_AGENT", prompt={"id": 2}, response={})
        tracker.add_step(module="ORCHESTRATOR", prompt={"id": 3}, response={})

        orchestrator_steps = tracker.get_steps_by_module("ORCHESTRATOR")

        assert len(orchestrator_steps) == 2
        assert orchestrator_steps[0]["prompt"]["id"] == 1
        assert orchestrator_steps[1]["prompt"]["id"] == 3

    def test_to_json(self):
        """Can serialize steps to JSON."""
        tracker = StepTracker()
        tracker.add_step(
            module="ORCHESTRATOR",
            prompt={"text": "test"},
            response={"result": "ok"}
        )

        json_str = tracker.to_json()

        assert '"module": "ORCHESTRATOR"' in json_str
        assert '"prompt"' in json_str
        assert '"response"' in json_str

    def test_complex_prompt_and_response(self):
        """Handles complex nested prompt and response data."""
        tracker = StepTracker()
        tracker.add_step(
            module="RAG_AGENT",
            prompt={
                "query": "teaching methods for ADHD",
                "constraints": {
                    "exclude": ["method1", "method2"],
                    "learning_style": "visual"
                }
            },
            response={
                "methods": [
                    {"name": "Method A", "score": 0.95},
                    {"name": "Method B", "score": 0.87}
                ],
                "total_found": 10
            }
        )

        steps = tracker.get_steps()
        assert steps[0]["prompt"]["constraints"]["learning_style"] == "visual"
        assert len(steps[0]["response"]["methods"]) == 2


class TestStepTrackerSingleton:
    """Tests for singleton pattern functions."""

    def test_get_step_tracker_returns_instance(self):
        """get_step_tracker returns a StepTracker instance."""
        tracker = get_step_tracker()
        assert isinstance(tracker, StepTracker)

    def test_reset_step_tracker_creates_new_instance(self):
        """reset_step_tracker creates fresh tracker."""
        tracker1 = get_step_tracker()
        tracker1.add_step(module="ORCHESTRATOR", prompt={}, response={})

        tracker2 = reset_step_tracker()

        assert len(tracker2) == 0
        assert tracker1 is not tracker2
