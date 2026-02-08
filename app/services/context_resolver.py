"""
Context Resolver.
Extracts context from conversation history and resolves student identity.
"""
import re
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from app.agents.student_agent import StudentAgent
    from app.core.router import RoutingResult


# Common student name patterns for extraction
# These are sample names used in the system - could be made configurable
STUDENT_NAME_PATTERN = re.compile(
    r"\b(Alex|Jordan|Maya|Sam|Emma|Carlos|Taylor|Jamie|Morgan|Casey|Riley|"
    r"Alex M\.|Jordan K\.|Maya R\.|Sam T\.|Emma L\.|Carlos D\.|Taylor B\.|Jamie W\.|"
    r"Morgan S\.|Casey P\.|Riley N\.)\b",
    re.IGNORECASE
)


@dataclass
class ResolvedContext:
    """Result of context resolution."""
    conversation_context: Dict[str, Any]  # recent_student, previous_agents, history_summary
    student_context: Optional[Dict[str, Any]]  # Full student profile if found
    student_name: Optional[str]  # Resolved student name


class ContextResolver:
    """
    Extracts context from conversation history and resolves student identity.

    Extracted from orchestrator to separate context management concerns.
    """

    def __init__(self, student_agent: "StudentAgent"):
        """
        Initialize with StudentAgent dependency.

        Args:
            student_agent: StudentAgent instance for resolving student profiles
        """
        self.student_agent = student_agent

    def extract_conversation_context(
        self,
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract useful context from conversation history.

        Analyzes recent messages to identify:
        - Recent student being discussed
        - Recent topic/intent
        - Previous agents used

        Args:
            history: List of recent messages

        Returns:
            Dict with extracted context:
            - recent_student: Last mentioned student name
            - recent_topic: Topic being discussed (currently unused)
            - previous_agents: List of agents used in conversation
            - history_summary: Brief summary of recent messages
        """
        context = {
            "recent_student": None,
            "recent_topic": None,
            "previous_agents": [],
            "history_summary": "",
            "was_class_wide": False,
            "mentioned_students": [],
        }

        if not history or len(history) <= 1:
            return context

        # Scan messages from most recent to oldest (excluding the just-added user message)
        for msg in reversed(history[:-1]):
            content = msg.get("content", "")

            # Look for student names
            if not context["recent_student"]:
                match = STUDENT_NAME_PATTERN.search(content)
                if match:
                    context["recent_student"] = match.group(1)

            # Track agents used
            agent = msg.get("agent_used")
            if agent and agent not in context["previous_agents"]:
                context["previous_agents"].append(agent)

        # Second pass: detect class-wide responses from the most recent assistant message
        for msg in reversed(history[:-1]):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                all_names = STUDENT_NAME_PATTERN.findall(content)
                # Deduplicate (case-insensitive) while preserving order
                seen = set()
                unique_names = []
                for name in all_names:
                    key = name.lower()
                    if key not in seen:
                        seen.add(key)
                        unique_names.append(name)
                if len(unique_names) >= 3:
                    context["was_class_wide"] = True
                    context["mentioned_students"] = unique_names
                break  # Only check the most recent assistant message

        # Create a brief summary of recent conversation
        recent_msgs = history[-4:-1] if len(history) > 4 else history[:-1]
        if recent_msgs:
            summaries = []
            for msg in recent_msgs:
                role = msg.get("role", "unknown")
                limit = 300 if role == "assistant" else 100
                content = msg.get("content", "")[:limit]
                summaries.append(f"{role}: {content}...")
            context["history_summary"] = "\n".join(summaries)

        return context

    async def resolve_student(
        self,
        student_name_from_routing: Optional[str],
        conversation_context: Dict[str, Any],
        should_resolve: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve student context from routing entities or conversation context.

        Args:
            student_name_from_routing: Name extracted during routing
            conversation_context: Context from conversation history
            should_resolve: Whether to attempt resolution if no name provided

        Returns:
            Full student context dict or None if not found
        """
        # Determine the student name to look up
        student_name = student_name_from_routing
        if not student_name and conversation_context.get("recent_student"):
            student_name = conversation_context["recent_student"]

        if not student_name and not should_resolve:
            return None

        # Delegate to student agent
        return await self.student_agent.get_student_context(
            student_name=student_name
        )

    async def resolve(
        self,
        history: List[Dict[str, Any]],
        routing_result: "RoutingResult",
        should_get_student: bool
    ) -> ResolvedContext:
        """
        Complete context resolution: conversation context + student context.

        This is the main entry point that combines both extraction steps.

        Args:
            history: Conversation history
            routing_result: Result from router with extracted entities
            should_get_student: Whether to fetch student context

        Returns:
            ResolvedContext with all resolved information
        """
        # Extract conversation context
        conv_context = self.extract_conversation_context(history)

        # Get student name from routing or context
        student_name_from_routing = routing_result.extracted_entities.get("name")
        student_name = student_name_from_routing or conv_context.get("recent_student")

        # Resolve student context if needed
        student_context = None
        if should_get_student or student_name:
            student_context = await self.resolve_student(
                student_name_from_routing=student_name_from_routing,
                conversation_context=conv_context,
                should_resolve=should_get_student
            )

        return ResolvedContext(
            conversation_context=conv_context,
            student_context=student_context,
            student_name=student_context.get("name") if student_context else student_name
        )
