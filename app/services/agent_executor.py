"""
Agent Executor.
Simple dispatch to appropriate agents based on routing result.
"""
from typing import Dict, Any, Optional, TYPE_CHECKING

from app.core.router import AgentType

if TYPE_CHECKING:
    from app.agents.student_agent import StudentAgent
    from app.agents.rag_agent import RAGAgent
    from app.agents.admin_agent import AdminAgent
    from app.agents.predict_agent import PredictAgent


class AgentExecutor:
    """
    Dispatches queries to appropriate agents based on routing result.

    Extracted from orchestrator to separate agent dispatch concerns.
    """

    def __init__(
        self,
        student_agent: "StudentAgent",
        rag_agent: "RAGAgent",
        admin_agent: "AdminAgent",
        predict_agent: "PredictAgent"
    ):
        """
        Initialize with agent instances.

        Args:
            student_agent: StudentAgent instance
            rag_agent: RAGAgent instance
            admin_agent: AdminAgent instance
            predict_agent: PredictAgent instance
        """
        self._agents = {
            AgentType.STUDENT_AGENT: student_agent,
            AgentType.RAG_AGENT: rag_agent,
            AgentType.ADMIN_AGENT: admin_agent,
            AgentType.PREDICT_AGENT: predict_agent,
        }

    async def execute(
        self,
        agent_type: AgentType,
        query: str,
        student_context: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the appropriate agent with given inputs.

        Args:
            agent_type: Which agent to execute
            query: The user's query
            student_context: Optional student context (profile, triggers, etc.)
            context: Optional additional context (session_id, teacher_id)

        Returns:
            Agent result dict with 'response' key and agent-specific data

        Raises:
            ValueError: If agent_type is not supported
        """
        input_data = {
            "prompt": query,
            "student_context": student_context
        }

        if student_context:
            input_data["student_name"] = student_context.get("name")
            input_data["student_id"] = student_context.get("student_id")

        agent = self._agents.get(agent_type)
        if not agent:
            raise ValueError(f"Unknown or unsupported agent type: {agent_type}")

        return await agent.process(input_data, context)

    def get_agent(self, agent_type: AgentType):
        """
        Get agent instance by type.

        Args:
            agent_type: The type of agent to retrieve

        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_type)

    @property
    def supported_agents(self):
        """List of supported agent types."""
        return list(self._agents.keys())
