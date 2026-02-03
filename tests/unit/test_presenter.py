"""
Unit tests for Presenter.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.presenter import Presenter


class TestPresenter:
    """Tests for Presenter."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.complete = AsyncMock(return_value={
            "content": "Transformed response with friendly tone",
            "tokens_used": {"input": 100, "output": 50}
        })
        return client

    @pytest.fixture
    def mock_tracker(self):
        """Create mock step tracker."""
        tracker = MagicMock()
        tracker.add_step = MagicMock()
        return tracker

    @pytest.fixture
    def presenter(self, mock_llm_client, mock_tracker):
        """Create Presenter with mocked dependencies."""
        return Presenter(
            llm_client=mock_llm_client,
            step_tracker=mock_tracker,
            enabled=True
        )

    @pytest.fixture
    def disabled_presenter(self, mock_llm_client, mock_tracker):
        """Create disabled Presenter."""
        return Presenter(
            llm_client=mock_llm_client,
            step_tracker=mock_tracker,
            enabled=False
        )

    @pytest.mark.asyncio
    async def test_present_transforms_response(self, presenter, mock_llm_client):
        """Test that present transforms the response."""
        result = await presenter.present(
            query="What works for Alex?",
            agent_response="Raw agent response here"
        )

        assert result == "Transformed response with friendly tone"
        mock_llm_client.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_present_uses_prompt_template(self, presenter, mock_llm_client):
        """Test that present uses the correct prompt format."""
        await presenter.present(
            query="Test query",
            agent_response="Test response"
        )

        call_args = mock_llm_client.complete.call_args
        messages = call_args.kwargs["messages"]
        prompt = messages[0]["content"]

        # Verify prompt contains both query and response
        assert "Test query" in prompt
        assert "Test response" in prompt

    @pytest.mark.asyncio
    async def test_present_tracks_step(self, presenter, mock_tracker):
        """Test that present tracks a step."""
        await presenter.present(
            query="Test query",
            agent_response="Test response"
        )

        mock_tracker.add_step.assert_called_once()
        call_args = mock_tracker.add_step.call_args
        assert call_args.kwargs["module"] == "ORCHESTRATOR"
        assert call_args.kwargs["prompt"]["action"] == "present_response"

    @pytest.mark.asyncio
    async def test_present_disabled_returns_original(self, disabled_presenter, mock_llm_client):
        """Test that disabled presenter returns original response."""
        result = await disabled_presenter.present(
            query="Test query",
            agent_response="Original response"
        )

        assert result == "Original response"
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_present_skip_for_updates(self, presenter, mock_llm_client):
        """Test that skip_for_updates returns original response."""
        result = await presenter.present(
            query="Test query",
            agent_response="Update confirmation response",
            skip_for_updates=True
        )

        assert result == "Update confirmation response"
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_present_uses_correct_temperature(self, presenter, mock_llm_client):
        """Test that present uses temperature 0.7."""
        await presenter.present(
            query="Test",
            agent_response="Test"
        )

        call_args = mock_llm_client.complete.call_args
        assert call_args.kwargs["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_present_uses_correct_max_tokens(self, presenter, mock_llm_client):
        """Test that present uses max_tokens 400."""
        await presenter.present(
            query="Test",
            agent_response="Test"
        )

        call_args = mock_llm_client.complete.call_args
        assert call_args.kwargs["max_tokens"] == 400

    def test_set_enabled(self, presenter):
        """Test set_enabled method."""
        assert presenter.enabled is True

        presenter.set_enabled(False)
        assert presenter.enabled is False

        presenter.set_enabled(True)
        assert presenter.enabled is True

    @pytest.mark.asyncio
    async def test_present_handles_empty_response(self, presenter, mock_llm_client):
        """Test handling when LLM returns empty content."""
        mock_llm_client.complete.return_value = {
            "content": "",
            "tokens_used": {}
        }

        result = await presenter.present(
            query="Test",
            agent_response="Original"
        )

        # Should return empty string (or original based on implementation)
        # Current implementation returns empty string from LLM
        assert result == ""

    @pytest.mark.asyncio
    async def test_present_step_includes_lengths(self, presenter, mock_tracker):
        """Test that step tracking includes content lengths."""
        await presenter.present(
            query="Short query",
            agent_response="A" * 500  # Long response
        )

        call_args = mock_tracker.add_step.call_args
        prompt_data = call_args.kwargs["prompt"]
        assert prompt_data["original_length"] == 500
        assert len(prompt_data["query_snippet"]) <= 50
