"""
Admin Agent.
Handles administrative tasks: IEP reports, parent communication, summaries.
"""
from typing import Dict, Any, Optional, List
from datetime import date

from app.agents.base_agent import BaseAgent
from app.core.cache import get_cache
from app.utils.prompts import (
    ADMIN_AGENT_SYSTEM,
    ADMIN_AGENT_IEP_PROMPT,
    ADMIN_AGENT_PARENT_EMAIL_PROMPT,
    ADMIN_AGENT_SUMMARY_PROMPT,
    ADMIN_AGENT_INCIDENT_PROMPT,
    format_student_profile
)


class AdminAgent(BaseAgent):
    """
    Agent for administrative tasks.

    Responsibilities:
    - Draft IEP reports and progress updates
    - Compose parent communication
    - Create daily/weekly summaries
    - Prepare meeting materials
    - Generate incident reports
    """

    MODULE_NAME = "ADMIN_AGENT"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = get_cache()

    async def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an administrative request.

        Args:
            input_data: Contains 'query' and 'doc_type'
            context: Optional context with student_profile, teacher_id

        Returns:
            Dict with 'response', 'document_type', 'metadata'
        """
        query = input_data.get("prompt", "")
        doc_type = input_data.get("doc_type", self._detect_doc_type(query))
        student_context = input_data.get("student_context") or {}

        # Route to appropriate handler
        if doc_type == "iep":
            return await self._handle_iep(query, student_context, context)
        elif doc_type == "email":
            return await self._handle_parent_email(query, student_context, context)
        elif doc_type == "summary":
            return await self._handle_summary(query, context)
        elif doc_type == "incident":
            return await self._handle_incident(query, student_context, context)
        else:
            return await self._handle_general(query, student_context, context)

    def _detect_doc_type(self, query: str) -> str:
        """Detect document type from query."""
        query_lower = query.lower()

        if any(word in query_lower for word in ["iep", "goal", "objective", "progress report"]):
            return "iep"
        elif any(word in query_lower for word in ["email", "parent", "message", "letter"]):
            return "email"
        elif any(word in query_lower for word in ["summary", "daily", "weekly", "overview"]):
            return "summary"
        elif any(word in query_lower for word in ["incident", "behavior", "occurred"]):
            return "incident"
        else:
            return "general"

    async def _handle_iep(
        self,
        query: str,
        student_context: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate IEP-related document."""
        # Get observations if available
        observations = ""
        if context and context.get("teacher_id") and student_context.get("student_id"):
            daily_contexts = await self.memory.get_daily_context(
                teacher_id=context["teacher_id"],
                student_id=student_context.get("student_id")
            )
            observations = "\n".join([
                f"- {ctx.get('content', '')}" for ctx in daily_contexts[:5]
            ]) or "No recent observations recorded."

        prompt = ADMIN_AGENT_IEP_PROMPT.format(
            query=query,
            student_info=format_student_profile(student_context) if student_context else "No student specified",
            observations=observations
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": ADMIN_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "iep_document",
                "student": student_context.get("name", "Unknown"),
                "query_type": "IEP"
            },
            temperature=0.6,
            max_tokens=1200
        )

        return {
            "response": response,
            "document_type": "iep",
            "student_name": student_context.get("name"),
            "metadata": {
                "generated_date": date.today().isoformat(),
                "observations_included": bool(observations)
            }
        }

    async def _handle_parent_email(
        self,
        query: str,
        student_context: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Draft parent communication."""
        # Build context for the email
        email_context = query
        if student_context:
            email_context += f"\nStudent: {student_context.get('name', 'Unknown')}"
            if student_context.get("triggers"):
                email_context += f"\n(Note: Be sensitive about: {', '.join(student_context['triggers'][:2])})"

        prompt = ADMIN_AGENT_PARENT_EMAIL_PROMPT.format(
            query=query,
            student_name=student_context.get("name", "the student"),
            context=email_context
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": ADMIN_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "parent_email",
                "student": student_context.get("name", "Unknown")
            },
            temperature=0.7,
            max_tokens=800
        )

        return {
            "response": response,
            "document_type": "email",
            "student_name": student_context.get("name"),
            "metadata": {
                "generated_date": date.today().isoformat(),
                "recipient": "parent"
            }
        }

    async def _handle_summary(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a summary report."""
        # Determine time period
        query_lower = query.lower()
        if "week" in query_lower:
            time_period = "weekly"
        elif "month" in query_lower:
            time_period = "monthly"
        else:
            time_period = "daily"

        # Get data to summarize
        data = "No data available for the specified period."
        if context and context.get("teacher_id"):
            daily_contexts = await self.memory.get_daily_context(
                teacher_id=context["teacher_id"]
            )
            if daily_contexts:
                data = "\n".join([
                    f"- [{ctx.get('context_type', 'note')}] {ctx.get('content', '')}"
                    for ctx in daily_contexts[:10]
                ])

        # Check cache for summaries
        cache_key = f"summary_{time_period}_{date.today().isoformat()}"
        cached = await self.cache.get(cache_key, self.MODULE_NAME)
        if cached:
            self.add_step(
                prompt={"action": "summary_cache_hit", "period": time_period},
                response={"from_cache": True}
            )
            return {
                "response": cached,
                "document_type": "summary",
                "time_period": time_period,
                "from_cache": True
            }

        prompt = ADMIN_AGENT_SUMMARY_PROMPT.format(
            query=query,
            time_period=time_period,
            data=data
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": ADMIN_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "summary",
                "period": time_period
            },
            temperature=0.6,
            max_tokens=1000
        )

        # Cache the summary
        await self.cache.set(cache_key, response, self.MODULE_NAME)

        return {
            "response": response,
            "document_type": "summary",
            "time_period": time_period,
            "from_cache": False,
            "metadata": {
                "generated_date": date.today().isoformat()
            }
        }

    async def _handle_incident(
        self,
        query: str,
        student_context: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate an incident report."""
        prompt = ADMIN_AGENT_INCIDENT_PROMPT.format(
            query=query,
            student_name=student_context.get("name", "the student"),
            incident_details=query,
            actions_taken="As described in the request"
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": ADMIN_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "incident_report",
                "student": student_context.get("name", "Unknown")
            },
            temperature=0.5,
            max_tokens=800
        )

        return {
            "response": response,
            "document_type": "incident",
            "student_name": student_context.get("name"),
            "metadata": {
                "generated_date": date.today().isoformat(),
                "requires_review": True
            }
        }

    async def _handle_general(
        self,
        query: str,
        student_context: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle general administrative requests."""
        prompt = f"""Administrative request: {query}

Student context: {format_student_profile(student_context) if student_context else 'None provided'}

Please draft an appropriate response or document based on the request."""

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": ADMIN_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "general_admin",
                "query_snippet": query[:100]
            },
            temperature=0.7,
            max_tokens=800
        )

        return {
            "response": response,
            "document_type": "general",
            "metadata": {
                "generated_date": date.today().isoformat()
            }
        }

    async def draft_document(
        self,
        doc_type: str,
        student_profile: Optional[Dict[str, Any]] = None,
        additional_info: Optional[str] = None
    ) -> str:
        """
        Utility method to draft a specific document type.
        Used by orchestrator for multi-agent workflows.
        """
        query = f"Draft a {doc_type}"
        if additional_info:
            query += f": {additional_info}"

        result = await self.process(
            input_data={
                "query": query,
                "doc_type": doc_type,
                "student_context": student_profile
            }
        )

        return result.get("response", "")
