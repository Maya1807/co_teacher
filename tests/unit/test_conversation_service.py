"""
Unit tests for ConversationService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.conversation_service import ConversationService


class TestConversationService:
    """Tests for ConversationService."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create a mock memory manager."""
        manager = MagicMock()
        manager.get_or_create_conversation = AsyncMock(return_value={
            "id": "conv-123",
            "session_id": "test-session",
            "teacher_id": "T001"
        })
        manager.add_message = AsyncMock(return_value={
            "id": "msg-123",
            "conversation_id": "conv-123",
            "role": "user",
            "content": "test message"
        })
        manager.get_conversation_history = AsyncMock(return_value=[
            {"id": "msg-1", "role": "user", "content": "Hello"},
            {"id": "msg-2", "role": "assistant", "content": "Hi there"}
        ])
        return manager

    @pytest.fixture
    def service(self, mock_memory_manager):
        """Create ConversationService with mocked dependencies."""
        return ConversationService(memory_manager=mock_memory_manager)

    @pytest.mark.asyncio
    async def test_get_or_create_conversation(self, service, mock_memory_manager):
        """Test getting or creating a conversation."""
        result = await service.get_or_create_conversation(
            session_id="test-session",
            teacher_id="T001"
        )

        assert result["id"] == "conv-123"
        assert result["session_id"] == "test-session"
        mock_memory_manager.get_or_create_conversation.assert_called_once_with(
            session_id="test-session",
            teacher_id="T001"
        )

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_without_teacher(self, service, mock_memory_manager):
        """Test creating conversation without teacher_id."""
        await service.get_or_create_conversation(session_id="test-session")

        mock_memory_manager.get_or_create_conversation.assert_called_once_with(
            session_id="test-session",
            teacher_id=None
        )

    @pytest.mark.asyncio
    async def test_add_user_message(self, service, mock_memory_manager):
        """Test adding a user message."""
        result = await service.add_user_message(
            conversation_id="conv-123",
            content="What works for Alex?"
        )

        assert result["id"] == "msg-123"
        mock_memory_manager.add_message.assert_called_once_with(
            conversation_id="conv-123",
            role="user",
            content="What works for Alex?"
        )

    @pytest.mark.asyncio
    async def test_add_assistant_message(self, service, mock_memory_manager):
        """Test adding an assistant message."""
        await service.add_assistant_message(
            conversation_id="conv-123",
            content="Here are some strategies...",
            agent_used="RAG_AGENT"
        )

        mock_memory_manager.add_message.assert_called_once_with(
            conversation_id="conv-123",
            role="assistant",
            content="Here are some strategies...",
            agent_used="RAG_AGENT"
        )

    @pytest.mark.asyncio
    async def test_add_assistant_message_without_agent(self, service, mock_memory_manager):
        """Test adding assistant message without specifying agent."""
        await service.add_assistant_message(
            conversation_id="conv-123",
            content="Response text"
        )

        mock_memory_manager.add_message.assert_called_once_with(
            conversation_id="conv-123",
            role="assistant",
            content="Response text",
            agent_used=None
        )

    @pytest.mark.asyncio
    async def test_get_history(self, service, mock_memory_manager):
        """Test getting conversation history."""
        result = await service.get_history(
            conversation_id="conv-123",
            limit=6
        )

        assert len(result) == 2
        assert result[0]["role"] == "user"
        mock_memory_manager.get_conversation_history.assert_called_once_with(
            conversation_id="conv-123",
            limit=6
        )

    @pytest.mark.asyncio
    async def test_get_history_default_limit(self, service, mock_memory_manager):
        """Test that default limit is 6."""
        await service.get_history(conversation_id="conv-123")

        mock_memory_manager.get_conversation_history.assert_called_once_with(
            conversation_id="conv-123",
            limit=6
        )
