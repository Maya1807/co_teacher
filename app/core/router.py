"""
Rule-Based Router for Agent Selection.
Saves ~40% of LLM calls by routing requests based on keywords and patterns.
Only falls back to LLM-based routing when no clear match is found.
"""
import json
import re
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from app.core.llm_client import LLMClient
    from app.core.step_tracker import StepTracker


class AgentType(str, Enum):
    """Valid agent types in the system."""
    ORCHESTRATOR = "ORCHESTRATOR"
    STUDENT_AGENT = "STUDENT_AGENT"
    RAG_AGENT = "RAG_AGENT"
    ADMIN_AGENT = "ADMIN_AGENT"
    PREDICT_AGENT = "PREDICT_AGENT"


@dataclass
class RoutingResult:
    """Result of routing decision."""
    agents: List[AgentType]  # Can route to multiple agents
    confidence: float  # 0.0 to 1.0
    matched_pattern: Optional[str] = None
    requires_llm_confirmation: bool = False
    extracted_entities: Dict[str, Any] = None

    def __post_init__(self):
        if self.extracted_entities is None:
            self.extracted_entities = {}

    @property
    def agent(self) -> AgentType:
        """Primary agent (first in list). For backward compatibility."""
        return self.agents[0] if self.agents else AgentType.ORCHESTRATOR

    @property
    def is_multi_agent(self) -> bool:
        """Check if multiple agents are needed."""
        return len(self.agents) > 1


class RuleBasedRouter:
    """
    Routes requests to appropriate agents using keyword and pattern matching.

    Routing Priority:
    1. Exact keyword matches (high confidence)
    2. Pattern matches with entity extraction (medium-high confidence)
    3. Fuzzy keyword matches (medium confidence)
    4. LLM fallback (when confidence < threshold)
    """

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.9
    MEDIUM_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.5
    LLM_FALLBACK_THRESHOLD = 0.5

    # ==================== STUDENT_AGENT Rules ====================
    # Queries about specific students, profiles, triggers, history
    # Note: Only include keywords that are student-specific, not general situations
    # Words like "meltdown", "crisis" are situations - they go to RAG unless a name is present
    STUDENT_KEYWORDS = [
        "profile", "triggers", "trigger", "history",
        "what works for", "learning style",
        "iep goal", "struggling with",
        "their profile", "his profile", "her profile",
        "their triggers", "his triggers", "her triggers"
    ]

    STUDENT_PATTERNS = [
        # "[Name]'s profile/triggers/parents/etc" - single word name before 's
        r"\b(?P<name>[A-Za-z]+)'s\s+(?:profile|triggers?|history|behavior|parents?)",
        r"[Pp]rofile\s+(?:for|of)\s+(?P<name>[A-Za-z]+)",
        # "about [Name]" or "check on [Name]" - name is single word
        r"(?:about|check\s+on|how\s+is|update\s+on)\s+(?P<name>[A-Za-z]+)\b",
        # "What works for [Name]"
        r"what\s+works\s+for\s+(?P<name>[A-Za-z]+)\b",
        # "[Name] is having/had/started" - name at word boundary
        r"\b(?P<name>[A-Za-z]+)\s+(?:is\s+having|had\s+a|has\s+been|was\s+having|started\s+having)",
        # "help [Name] with" - e.g., "How can I help Maya with reading?"
        r"help\s+(?P<name>[A-Za-z]+)\s+with",
        # "for [Name]" at end - e.g., "strategies for Alex"
        r"(?:strategies?|methods?|tips?|advice)\s+for\s+(?P<name>[A-Za-z]+)\s*[\?\.]?\s*$",
        # "help him/her" with name earlier - "[Name]'s parents...he/she"
        r"\b(?P<name>[A-Za-z]+)'s\s+parents?",
    ]

    # ==================== RAG_AGENT Rules ====================
    # Teaching methods, strategies, recommendations, and general situations
    RAG_KEYWORDS = [
        "strategy", "strategies", "method", "methods", "technique",
        "how to teach", "suggest", "recommend", "approach", "intervention",
        "accommodate", "adaptation", "modify", "differentiate",
        "best practice", "evidence-based", "research", "effective",
        # Behavioral situations (general, not student-specific)
        "meltdown", "crisis", "behavior", "de-escalation", "calm down",
        "sensory overload", "outburst", "tantrum", "dysregulation"
    ]

    RAG_PATTERNS = [
        # "How do I [teach/help/support]"
        r"how\s+(?:do\s+I|can\s+I|should\s+I)\s+(?:teach|help|support|engage|motivate|accommodate)",
        # "What's the best way to"
        r"what(?:'s|\s+is)\s+the\s+best\s+(?:way|approach|method)\s+to",
        # "Strategies for [condition/situation]"
        r"strateg(?:y|ies)\s+for\s+(?:teaching\s+)?(?P<topic>.+?)(?:\?|$)",
        # "What strategies/methods/techniques work/help"
        r"what\s+(?:strategies?|methods?|techniques?)\s+(?:work|help)",
        # "How to handle/manage"
        r"how\s+to\s+(?:handle|manage|deal\s+with|address)",
        # "Help with [situation]" - general situations like meltdowns, behaviors
        r"[Hh]elp\s+(?:me\s+)?with\s+(?:a\s+)?(?:meltdown|crisis|behavior|outburst|tantrum|situation)",
        # "Techniques for" or "Techniques that help"
        r"techniques?\s+(?:for|that\s+help\s+with)\s+(?P<topic>.+?)(?:\?|$)",
        # "Suggest methods for"
        r"(?:suggest|recommend)\s+(?:some\s+)?(?:methods?|strategies?|techniques?)",
    ]

    # ==================== ADMIN_AGENT Rules ====================
    # Reports, IEP, communication, summaries
    ADMIN_KEYWORDS = [
        "draft", "iep", "report", "parent", "email", "message",
        "summary", "documentation", "letter", "update", "meeting",
        "write", "prepare", "create", "send", "communicate",
        "progress report", "incident", "daily summary"
    ]

    ADMIN_PATTERNS = [
        # "Draft/Write a [document type]"
        r"(?:draft|write|prepare|create)\s+(?:a\s+)?(?P<doc_type>report|email|letter|message|summary|iep)",
        # "Send [something] to parent"
        r"(?:send|prepare)\s+.+?\s+(?:to|for)\s+(?:the\s+)?parent",
        # "Parent communication"
        r"parent\s+(?:communication|update|message|email)",
        # "IEP [action]"
        r"iep\s+(?:report|update|draft|summary|meeting|goal)",
        # "Summary of/for [time period]"
        r"summary\s+(?:of|for)\s+(?:the\s+)?(?:day|week|month|today|yesterday)",
        # "Daily/Weekly report"
        r"(?:daily|weekly|monthly)\s+(?:report|summary|update)",
    ]

    # ==================== PREDICT_AGENT Rules ====================
    # Predictions, daily briefings, event-based concerns
    PREDICT_KEYWORDS = [
        "predict", "forecast", "warning", "heads up", "watch for",
        "today's schedule", "upcoming", "any concerns", "prepare for",
        "morning briefing", "daily briefing", "what's happening today",
        "what should i watch", "what to expect", "any risks",
        "who might struggle", "potential issues", "fire drill",
        "field trip", "assembly"
    ]

    PREDICT_PATTERNS = [
        # "What should I watch/prepare/expect today"
        r"what.*(?:watch|prepare|expect).*today",
        # "Any concerns/issues/challenges today/this week"
        r"any.*(?:concerns?|issues?|challenges?|risks?).*(?:today|this week)",
        # "Daily/morning briefing/summary/heads up"
        r"(?:daily|morning)\s+(?:briefing|summary|heads\s+up)",
        # "Who might struggle with [event]"
        r"who\s+(?:might|may|could|will)\s+(?:struggle|have\s+trouble|be\s+affected)",
        # "Predictions for today/tomorrow"
        r"predictions?\s+for\s+(?:today|tomorrow|this\s+week)",
        # "What's happening today"
        r"what(?:'s|\s+is)\s+happening\s+today",
        # "Prepare me for today"
        r"prepare\s+(?:me\s+)?for\s+today",
    ]

    # ==================== Multi-Agent Indicators ====================
    # Keywords that suggest multiple agents needed
    MULTI_AGENT_KEYWORDS = [
        "and also", "as well as", "then", "after that",
        "based on their profile", "considering their history"
    ]

    # ==================== General Name Detection ====================
    # Patterns to detect student names in any context
    # Names are capitalized proper nouns, not common educational terms
    GENERAL_NAME_PATTERNS = [
        # "for [Name]" at end - but name must be followed by ? or end, not more words
        r"(?:for|with)\s+(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\??\s*$",
        # "[Name]'s" - single word possessive (not at sentence start)
        # Use word boundary to avoid matching "Check Alex's" as "Check Alex"
        r"(?<!\. )(?<!\? )(?<!^)\b(?P<name>[A-Z][a-z]+)'s\b",
    ]

    # Words that look like names but aren't (educational terms, question words, etc.)
    NAME_EXCLUSIONS = {
        # Pronouns
        "i", "me", "my", "he", "she", "they", "we", "you", "it", "him", "her", "them",
        # Question words
        "what", "who", "where", "when", "how", "why", "which",
        # Educational terms
        "students", "student", "adhd", "autism", "autistic", "dyslexia",
        "children", "kids", "learners", "teachers", "parents", "class",
        "iep", "goals", "reading", "math", "writing", "behavior",
        # Days and months
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday", "january", "february", "march", "april",
        "may", "june", "july", "august", "september", "october",
        "november", "december", "today", "yesterday", "tomorrow",
        # Common verbs that might be capitalized at sentence start
        "check", "update", "draft", "write", "prepare", "create", "send",
        "get", "show", "tell", "help", "suggest", "recommend",
        # Common words that aren't names
        "the", "a", "an", "this", "that", "meeting", "had", "have", "with"
    }

    def __init__(
        self,
        llm_client: Optional["LLMClient"] = None,
        step_tracker: Optional["StepTracker"] = None
    ):
        """
        Initialize the router with compiled regex patterns.

        Args:
            llm_client: Optional LLM client for fallback routing
            step_tracker: Optional step tracker for logging LLM calls
        """
        self.llm = llm_client
        self.tracker = step_tracker
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        # Student patterns: IGNORECASE for flexible name matching
        # Names will be title-cased when extracted
        self._student_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.STUDENT_PATTERNS
        ]
        self._rag_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.RAG_PATTERNS
        ]
        self._admin_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.ADMIN_PATTERNS
        ]
        self._predict_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.PREDICT_PATTERNS
        ]
        # General name detection (case-sensitive for proper nouns)
        self._general_name_patterns = [
            re.compile(p) for p in self.GENERAL_NAME_PATTERNS
        ]

    def route(
        self,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> RoutingResult:
        """
        Route a query to the appropriate agent(s).

        Args:
            query: The user's input query
            conversation_context: Optional context from conversation history

        Returns:
            RoutingResult with agent type(s), confidence, and extracted entities
        """
        query_lower = query.lower().strip()
        agents_needed: List[AgentType] = []
        entities: Dict[str, Any] = {}
        matched_patterns: List[str] = []
        confidence = 0.0
        conv_context = conversation_context or {}

        # 1. Check for student-specific patterns FIRST (most precise)
        student_match = self._check_agent_patterns(query, self._student_patterns)
        if student_match:
            agents_needed.append(AgentType.STUDENT_AGENT)
            entities.update(student_match.get("entities", {}))
            matched_patterns.append("student pattern")
            confidence = max(confidence, self.HIGH_CONFIDENCE)

        # 2. Check for general student name in query (if no specific pattern matched)
        if AgentType.STUDENT_AGENT not in agents_needed:
            student_name = self._extract_name_general(query)
            if student_name:
                agents_needed.append(AgentType.STUDENT_AGENT)
                entities["name"] = student_name
                matched_patterns.append(f"student name: {student_name}")
                confidence = max(confidence, self.HIGH_CONFIDENCE)

        # 2b. Check conversation context for recent student (follow-up queries)
        if AgentType.STUDENT_AGENT not in agents_needed and "name" not in entities:
            recent_student = conv_context.get("recent_student")
            if recent_student and self._is_followup_query(query_lower):
                # This looks like a follow-up about the previous student
                agents_needed.append(AgentType.STUDENT_AGENT)
                entities["name"] = recent_student
                matched_patterns.append(f"follow-up about {recent_student}")
                confidence = max(confidence, self.MEDIUM_CONFIDENCE)

        # 3. Check for PREDICT patterns/keywords (before RAG, as some queries overlap)
        predict_match = self._check_agent_patterns(query, self._predict_patterns)
        if predict_match:
            agents_needed.append(AgentType.PREDICT_AGENT)
            entities.update(predict_match.get("entities", {}))
            matched_patterns.append("predict pattern")
            confidence = max(confidence, self.HIGH_CONFIDENCE)
        elif self._has_keywords(query_lower, self.PREDICT_KEYWORDS):
            agents_needed.append(AgentType.PREDICT_AGENT)
            matched_patterns.append("predict keywords")
            confidence = max(confidence, self.MEDIUM_CONFIDENCE)

        # 4. Check for RAG patterns/keywords
        rag_match = self._check_agent_patterns(query, self._rag_patterns)
        if rag_match:
            agents_needed.append(AgentType.RAG_AGENT)
            entities.update(rag_match.get("entities", {}))
            matched_patterns.append("rag pattern")
            confidence = max(confidence, self.HIGH_CONFIDENCE)
        elif self._has_keywords(query_lower, self.RAG_KEYWORDS):
            agents_needed.append(AgentType.RAG_AGENT)
            matched_patterns.append("rag keywords")
            confidence = max(confidence, self.MEDIUM_CONFIDENCE)

        # 5. Check for ADMIN patterns/keywords
        admin_match = self._check_agent_patterns(query, self._admin_patterns)
        if admin_match:
            agents_needed.append(AgentType.ADMIN_AGENT)
            entities.update(admin_match.get("entities", {}))
            matched_patterns.append("admin pattern")
            confidence = max(confidence, self.HIGH_CONFIDENCE)
        elif self._has_keywords(query_lower, self.ADMIN_KEYWORDS):
            agents_needed.append(AgentType.ADMIN_AGENT)
            matched_patterns.append("admin keywords")
            confidence = max(confidence, self.MEDIUM_CONFIDENCE)

        # 6. Check for student keywords (if not already added by name/pattern)
        if AgentType.STUDENT_AGENT not in agents_needed:
            if self._has_keywords(query_lower, self.STUDENT_KEYWORDS):
                agents_needed.append(AgentType.STUDENT_AGENT)
                matched_patterns.append("student keywords")
                confidence = max(confidence, self.MEDIUM_CONFIDENCE)

        # 7. Handle results
        if not agents_needed:
            # No confident match - needs LLM routing
            return RoutingResult(
                agents=[AgentType.ORCHESTRATOR],
                confidence=0.3,
                requires_llm_confirmation=True,
                matched_pattern="no rule matched - LLM routing needed"
            )

        return RoutingResult(
            agents=agents_needed,
            confidence=confidence,
            matched_pattern=" + ".join(matched_patterns),
            extracted_entities=entities
        )

    def _extract_name_general(self, query: str) -> Optional[str]:
        """Extract a student name from query using general patterns."""
        for pattern in self._general_name_patterns:
            match = pattern.search(query)
            if match and "name" in match.groupdict():
                name = match.group("name")
                # Check if it's actually a name, not a common term
                if name.lower() not in self.NAME_EXCLUSIONS:
                    return name
        return None

    def _check_agent_patterns(self, query: str, patterns: List[re.Pattern]) -> Optional[Dict[str, Any]]:
        """Check if query matches any of the given patterns."""
        for pattern in patterns:
            match = pattern.search(query)
            if match:
                entities = match.groupdict()
                # Check if extracted name is actually a name (not a common word)
                if "name" in entities and entities["name"]:
                    name_lower = entities["name"].lower()
                    if name_lower in self.NAME_EXCLUSIONS:
                        # Skip this match, try next pattern
                        continue
                    # Title-case names for consistency (handles "taylor" -> "Taylor")
                    entities["name"] = entities["name"].title()
                return {
                    "pattern": pattern.pattern,
                    "entities": entities
                }
        return None

    def _has_keywords(self, query_lower: str, keywords: List[str]) -> bool:
        """Check if query contains any of the given keywords."""
        return any(kw in query_lower for kw in keywords)

    def _is_followup_query(self, query_lower: str) -> bool:
        """
        Check if the query looks like a follow-up to a previous conversation.

        Follow-up indicators:
        - Pronouns referring to a person (their, his, her, them)
        - Questions without explicit subject (what about, how about)
        - Continuation phrases (and what, also, another)
        """
        followup_indicators = [
            # Pronouns referring to previous subject
            "their ", "his ", "her ", "them ",
            "the student", "this student",
            # Questions without subject
            "what about ", "how about ", "what else",
            "any other", "anything else",
            # Continuation phrases
            "and what", "also ", "another ",
            # Trigger/method references without name
            "triggers", "what works", "what doesn't",
            "successful methods", "failed methods",
            "profile", "learning style"
        ]
        return any(indicator in query_lower for indicator in followup_indicators)

    def extract_student_name(self, query: str) -> Optional[str]:
        """Extract student name from query if present."""
        # Try general name patterns first
        name = self._extract_name_general(query)
        if name:
            return name
        # Fall back to student-specific patterns
        for pattern in self._student_patterns:
            match = pattern.search(query)
            if match and "name" in match.groupdict():
                return match.group("name")
        return None

    def get_routing_explanation(self, result: RoutingResult) -> str:
        """Get human-readable explanation of routing decision."""
        if result.requires_llm_confirmation:
            return (
                f"No confident rule match found (confidence: {result.confidence:.0%}). "
                "Using LLM for routing decision."
            )

        entities_str = ""
        if result.extracted_entities:
            entities_str = f" Extracted: {result.extracted_entities}"

        agents_str = ", ".join(a.value for a in result.agents)
        return (
            f"Routed to [{agents_str}] with {result.confidence:.0%} confidence. "
            f"Match: {result.matched_pattern}.{entities_str}"
        )

    # ==================== LLM Fallback Routing ====================

    async def route_with_fallback(
        self,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        use_llm_fallback: bool = True
    ) -> RoutingResult:
        """
        Route query with optional LLM fallback for low-confidence cases.

        This method first tries rule-based routing, then falls back to LLM
        if confidence is too low and LLM client is configured.

        Args:
            query: The user's input query
            conversation_context: Context from conversation history
            context: Additional context (session_id, previous_agents)
            use_llm_fallback: Whether to use LLM when confidence < 0.5

        Returns:
            RoutingResult with agents, confidence, and extracted entities
        """
        # First try rule-based routing
        result = self.route(query, conversation_context)

        # Fall back to LLM if needed and configured
        if result.requires_llm_confirmation and use_llm_fallback and self.llm:
            result = await self._llm_route(query, context)

        return result

    async def _llm_route(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> RoutingResult:
        """
        Use LLM for routing when rule-based router is not confident.

        Args:
            query: The user's input query
            context: Additional context (session_id, previous_agents)

        Returns:
            RoutingResult from LLM analysis
        """
        from app.utils.prompts import ORCHESTRATOR_ROUTE_PROMPT, ORCHESTRATOR_SYSTEM

        previous_agents = context.get("previous_agents", []) if context else []

        prompt = ORCHESTRATOR_ROUTE_PROMPT.format(
            query=query,
            session_id=context.get("session_id", "default") if context else "default",
            previous_agents=", ".join(previous_agents) or "None"
        )

        # Call LLM
        response = await self.llm.complete(
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )

        content = response.get("content", "")

        # Track step if tracker is configured
        if self.tracker:
            self.tracker.add_step(
                module="ORCHESTRATOR",
                prompt={
                    "action": "llm_routing",
                    "query_snippet": query[:100]
                },
                response={
                    "content": content[:200],
                    "tokens_used": response.get("tokens_used")
                }
            )

        # Parse LLM response
        try:
            routing_json = json.loads(content)
            agent_name = routing_json.get("primary_agent", "RAG_AGENT")
            agent_type = AgentType(agent_name)
            student_name = routing_json.get("student_name")
            follow_up = routing_json.get("follow_up_agent")

            # Build agents list
            agents = [agent_type]
            if follow_up and follow_up != agent_name:
                try:
                    agents.append(AgentType(follow_up))
                except ValueError:
                    pass

            return RoutingResult(
                agents=agents,
                confidence=0.8,
                matched_pattern="llm_routing",
                extracted_entities={"name": student_name} if student_name else {}
            )
        except (json.JSONDecodeError, ValueError):
            # Default to RAG for general queries
            return RoutingResult(
                agents=[AgentType.RAG_AGENT],
                confidence=0.5,
                matched_pattern="llm_routing_fallback"
            )


# Singleton instance
_router: Optional[RuleBasedRouter] = None


def get_router() -> RuleBasedRouter:
    """Get or create the router singleton."""
    global _router
    if _router is None:
        _router = RuleBasedRouter()
    return _router


def route_query(query: str) -> RoutingResult:
    """Convenience function to route a query."""
    return get_router().route(query)
