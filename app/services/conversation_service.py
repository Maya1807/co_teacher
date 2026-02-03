"""
Conversation Service.
Handles conversation lifecycle and message storage.
"""
from typing import Dict, Any, Optional, List

from app.memory.memory_manager import MemoryManager, get_memory_manager


class ConversationService:
    """
    Handles conversation lifecycle and message storage.

    Extracted from orchestrator to separate conversation persistence concerns.
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.memory = memory_manager or get_memory_manager()

    async def get_or_create_conversation(
        self,
        session_id: str,
        teacher_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing conversation or create new one.

        Args:
            session_id: Unique session identifier
            teacher_id: Optional teacher identifier

        Returns:
            Conversation dict with 'id' key
        """
        return await self.memory.get_or_create_conversation(
            session_id=session_id,
            teacher_id=teacher_id
        )

    async def add_user_message(
        self,
        conversation_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Store a user message in the conversation.

        Args:
            conversation_id: Conversation ID
            content: Message content

        Returns:
            Message record
        """
        return await self.memory.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content
        )

    async def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        agent_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store an assistant response in the conversation.

        Args:
            conversation_id: Conversation ID
            content: Response content
            agent_used: Which agent generated the response

        Returns:
            Message record
        """
        return await self.memory.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            agent_used=agent_used
        )

    async def get_history(
        self,
        conversation_id: str,
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dicts ordered chronologically
        """
        return await self.memory.get_conversation_history(
            conversation_id=conversation_id,
            limit=limit
        )


# Singleton for easy access
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get or create the conversation service singleton."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
