"""
RAG Agent.
Retrieves and recommends teaching strategies using vector search.
"""
from typing import Dict, Any, Optional, List

from app.agents.base_agent import BaseAgent
from app.core.cache import get_cache
from app.utils.prompts import (
    RAG_AGENT_SYSTEM,
    RAG_AGENT_SEARCH_PROMPT,
    RAG_AGENT_NO_CONTEXT_PROMPT,
    RAG_AGENT_CLASS_WIDE_PROMPT,
    format_teaching_methods,
    format_all_student_profiles,
)


class RAGAgent(BaseAgent):
    """
    Agent for teaching method recommendations using RAG.

    Responsibilities:
    - Search teaching methods knowledge base
    - Provide evidence-based strategy recommendations
    - Consider student context when available
    - Cache responses for efficiency
    """

    MODULE_NAME = "RAG_AGENT"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = get_cache()

    async def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a teaching strategy query.

        Args:
            input_data: Contains 'query' and optionally student context
            context: Optional context with student_profile, teacher_id

        Returns:
            Dict with 'response', 'methods_retrieved', 'from_cache'
        """
        query = input_data.get("prompt", "")
        student_context = input_data.get("student_context") or {}

        # Extract student-specific constraints
        disability_type = student_context.get("disability_type")
        learning_style = student_context.get("learning_style")
        failed_methods = student_context.get("failed_methods", [])

        # Check cache first (only for non-student-specific queries)
        cache_key = None
        if not student_context:
            cached = await self.cache.get(query, self.MODULE_NAME)
            if cached:
                self.add_step(
                    prompt={"action": "cache_hit", "query": query[:100]},
                    response={"from_cache": True}
                )
                return {
                    "response": cached,
                    "methods_retrieved": [],
                    "from_cache": True
                }

        # Search for relevant teaching methods
        methods = await self.memory.search_teaching_methods(
            query=query,
            top_k=7,
            exclude_methods=failed_methods,
            disability_type=disability_type
        )

        # Generate response
        all_students_context = input_data.get("all_students_context")
        if all_students_context:
            response = await self._generate_class_wide_response(
                query, methods, all_students_context
            )
        elif student_context:
            response = await self._generate_contextual_response(
                query, methods, student_context
            )
        else:
            response = await self._generate_general_response(query, methods)

        # Cache the response if no student context and not class-wide
        if not student_context and not all_students_context:
            await self.cache.set(query, response, self.MODULE_NAME)

        return {
            "response": response,
            "methods_retrieved": [
                {
                    "method_name": m.get("method_name") or m.get("title", "Unknown"),
                    "category": m.get("category") or m.get("source_type", "Unknown"),
                    "score": m.get("score")
                }
                for m in methods
            ],
            "from_cache": False,
            "student_context_used": bool(student_context)
        }

    async def _generate_contextual_response(
        self,
        query: str,
        methods: List[Dict[str, Any]],
        student_context: Dict[str, Any]
    ) -> str:
        """Generate response with student context."""
        student_name = student_context.get("name", "the student")
        successful = student_context.get("successful_methods", [])

        prompt = RAG_AGENT_SEARCH_PROMPT.format(
            query=query,
            student_name=student_name,
            disability_type=student_context.get("disability_type", "Not specified"),
            learning_style=student_context.get("learning_style", "Not specified"),
            successful_methods=", ".join(successful[:3]) if successful else "Not specified",
            failed_methods=", ".join(student_context.get("failed_methods", [])) or "None specified",
            retrieved_methods=format_teaching_methods(methods)
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": RAG_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "contextual_search",
                "student": student_name,
                "query_snippet": query[:100],
                "disability_type": student_context.get("disability_type"),
                "methods_found": len(methods)
            },
            temperature=0.7,
            max_tokens=1000
        )

        return response

    async def _generate_general_response(
        self,
        query: str,
        methods: List[Dict[str, Any]]
    ) -> str:
        """Generate response without student context."""
        prompt = RAG_AGENT_NO_CONTEXT_PROMPT.format(
            query=query,
            retrieved_methods=format_teaching_methods(methods)
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": RAG_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "general_search",
                "query_snippet": query[:100],
                "methods_found": len(methods)
            },
            temperature=0.7,
            max_tokens=1000
        )

        return response

    async def _generate_class_wide_response(
        self,
        query: str,
        methods: List[Dict[str, Any]],
        all_students_context: List[Dict[str, Any]],
    ) -> str:
        """Generate response personalized to all students in the class."""
        prompt = RAG_AGENT_CLASS_WIDE_PROMPT.format(
            query=query,
            all_student_profiles=format_all_student_profiles(all_students_context),
            retrieved_methods=format_teaching_methods(methods),
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": RAG_AGENT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            prompt_summary={
                "action": "class_wide_search",
                "query_snippet": query[:100],
                "num_students": len(all_students_context),
                "methods_found": len(methods),
            },
            temperature=0.7,
            max_tokens=1500,
        )

        return response

    async def get_methods_for_student(
        self,
        query: str,
        student_profile: Dict[str, Any],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get teaching methods suitable for a specific student.
        Utility method for use by other agents.
        """
        methods = await self.memory.search_teaching_methods(
            query=query,
            top_k=top_k,
            exclude_methods=student_profile.get("failed_methods", []),
            disability_type=student_profile.get("disability_type")
        )

        self.add_step(
            prompt={
                "action": "get_methods_for_student",
                "student": student_profile.get("name"),
                "query": query[:50]
            },
            response={
                "methods_found": len(methods),
                "top_method": (
                    methods[0].get("method_name") or methods[0].get("title")
                ) if methods else None
            }
        )

        return methods

    async def get_relevant_methods(
        self,
        query: str,
        student_context: Optional[Dict[str, Any]] = None,
        top_k: int = 7
    ) -> Dict[str, Any]:
        """
        Get relevant teaching methods and return a formatted summary.
        Used by orchestrator for multi-agent synthesis.

        Args:
            query: The teacher's query
            student_context: Student profile context (optional)
            top_k: Number of methods to retrieve

        Returns:
            Dict with 'methods' list and 'methods_summary' string
        """
        profile = student_context.get("profile", {}) if student_context else {}

        methods = await self.memory.search_teaching_methods(
            query=query,
            top_k=top_k,
            exclude_methods=profile.get("failed_methods", []),
            disability_type=profile.get("disability_type")
        )

        self.add_step(
            prompt={
                "action": "get_relevant_methods",
                "query": query[:100],
                "has_student_context": bool(student_context)
            },
            response={
                "methods_found": len(methods),
                "method_names": [
                    m.get("method_name") or m.get("title", "Unknown")
                    for m in methods[:3]
                ]
            }
        )

        # Format methods into a concise summary
        if not methods:
            summary = "No specific teaching methods found for this query."
        else:
            lines = []
            for m in methods:
                name = m.get("method_name") or m.get("title", "Unknown")
                # Get description from various possible fields
                desc = m.get("description") or m.get("abstract") or m.get("text", "")
                # Truncate description if too long
                if len(desc) > 150:
                    desc = desc[:150] + "..."
                # Get applicable disabilities from various possible fields
                applicable = m.get("applicable_disabilities") or m.get("disability_categories", [])
                applicable_str = f" (good for: {', '.join(applicable[:2])})" if applicable else ""
                lines.append(f"- {name}: {desc}{applicable_str}")
            summary = "\n".join(lines)

        return {
            "methods": methods,
            "methods_summary": summary
        }

    async def explain_method(
        self,
        method_name: str,
        context: Optional[str] = None
    ) -> str:
        """
        Provide detailed explanation of a specific teaching method.
        """
        # Search for the specific method
        methods = await self.memory.search_teaching_methods(
            query=method_name,
            top_k=1
        )

        if not methods:
            return f"I couldn't find detailed information about '{method_name}'."

        method = methods[0]
        prompt = f"""Explain this teaching method in detail:

Method: {method.get('method_name')}
Category: {method.get('category', 'General')}
Description: {method.get('description', 'No description available')}

Context for use: {context or 'General application'}

Provide:
1. What the method involves
2. Why it works (the underlying principle)
3. Step-by-step implementation
4. Common pitfalls to avoid
5. Signs it's working"""

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": RAG_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "explain_method",
                "method": method_name
            },
            temperature=0.7,
            max_tokens=800
        )

        return response
