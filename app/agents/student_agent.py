"""
Student Agent.
Handles student-specific queries: profiles, triggers, history, updates.
"""
from typing import Dict, Any, Optional, List

from app.agents.base_agent import BaseAgent
import json
from app.utils.prompts import (
    STUDENT_AGENT_SYSTEM,
    STUDENT_AGENT_PROFILE_PROMPT,
    STUDENT_AGENT_NOT_FOUND_PROMPT,
    STUDENT_AGENT_UPDATE_EXTRACT_PROMPT,
    STUDENT_AGENT_UPDATE_CONFIRM_PROMPT,
    format_student_profile,
    format_daily_context
)


class StudentAgent(BaseAgent):
    """
    Agent for student-specific operations.

    Responsibilities:
    - Retrieve and present student profiles
    - Explain triggers and successful methods
    - Handle profile updates
    - Provide student context for other agents
    """

    MODULE_NAME = "STUDENT_AGENT"

    async def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a student-related query.

        Args:
            input_data: Contains 'query' and optionally 'student_name' or 'student_id'
            context: Optional context with teacher_id, session_id

        Returns:
            Dict with 'response', 'student_profile' (if found), 'action_taken'
        """
        query = input_data.get("prompt", "")
        student_name = input_data.get("student_name")
        student_id = input_data.get("student_id")
        action = input_data.get("action", "query")  # query, update, list

        # Capture original_query for update detection (planner sends
        # a specific task as "prompt" but the raw user query as
        # "original_query" so update extraction sees the real intent).
        self._current_original_query = input_data.get("original_query")

        # Determine what action to take
        if action == "update":
            return await self._handle_update(query, student_id, context)
        elif action == "list":
            return await self._handle_list(query, context)
        else:
            return await self._handle_query(query, student_name, student_id, context)

    async def _handle_query(
        self,
        query: str,
        student_name: Optional[str],
        student_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle a query about a specific student."""
        profile = None

        # Try to find the student
        if student_id:
            profile = await self.memory.get_student_profile(student_id)
        elif student_name:
            # Search by name
            matches = await self.memory.search_student_by_name(student_name)
            if matches:
                profile = matches[0]  # Take best match

        if not profile:
            # Student not found - generate helpful response
            return await self._handle_not_found(query, student_name)

        # Get student_id for updates
        sid = profile.get("id") or profile.get("student_id")

        # Check if query contains implicit update information
        # (e.g., "Alex had a meltdown when the bell rang")
        # Use original_query when available so update extraction sees the
        # teacher's raw words rather than the planner's rewritten task.
        raw_query = getattr(self, "_current_original_query", None) or query
        update_result = await self._extract_and_apply_updates(raw_query, profile, sid)

        # Get daily context if teacher_id available
        daily_context = []
        if context and context.get("teacher_id"):
            daily_context = await self.memory.get_daily_context(
                teacher_id=context["teacher_id"],
                student_id=sid
            )

        # Use updated profile if updates were applied
        current_profile = update_result.get("updated_profile", profile)

        # If updates were applied, just return the confirmation without full profile dump
        # The orchestrator will handle any additional context needed
        if update_result.get("action_taken") == "update_applied":
            return {
                "response": update_result["response"],
                "student_profile": current_profile,
                "action_taken": "update_applied",
                "student_id": sid,
                "student_name": current_profile.get("name"),
                "updates_applied": update_result.get("updates_applied")
            }

        # If items already exist in profile, return the helpful message
        if update_result.get("action_taken") == "already_exists":
            return {
                "response": update_result["response"],
                "student_profile": current_profile,
                "action_taken": "already_exists",
                "student_id": sid,
                "student_name": current_profile.get("name"),
                "updates_applied": None
            }

        # No updates - generate response about the student
        prompt = STUDENT_AGENT_PROFILE_PROMPT.format(
            profile=format_student_profile(current_profile),
            query=query,
            daily_context=format_daily_context(daily_context)
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": STUDENT_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "profile_query",
                "student": current_profile.get("name", "Unknown"),
                "query_snippet": query[:100]
            },
            temperature=0.7,
            max_tokens=800
        )

        return {
            "response": response,
            "student_profile": current_profile,
            "action_taken": "profile_retrieved",
            "student_id": sid,
            "student_name": current_profile.get("name"),
            "updates_applied": None
        }

    async def _handle_not_found(
        self,
        query: str,
        student_name: Optional[str]
    ) -> Dict[str, Any]:
        """Handle case when student is not found."""
        prompt = STUDENT_AGENT_NOT_FOUND_PROMPT.format(
            query=query,
            student_name=student_name or "Unknown"
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": STUDENT_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "student_not_found",
                "searched_name": student_name
            },
            temperature=0.7,
            max_tokens=300
        )

        return {
            "response": response,
            "student_profile": None,
            "action_taken": "not_found",
            "student_name": student_name
        }

    async def _handle_update(
        self,
        query: str,
        student_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle a student profile update request."""
        if not student_id:
            return {
                "response": "I need to know which student to update. Please specify the student name.",
                "action_taken": "update_failed",
                "error": "no_student_id"
            }

        profile = await self.memory.get_student_profile(student_id)
        if not profile:
            return {
                "response": f"I couldn't find a student with ID {student_id}.",
                "action_taken": "update_failed",
                "error": "student_not_found"
            }

        # Use LLM to extract structured update data
        update_result = await self._extract_and_apply_updates(query, profile, student_id)

        return {
            "response": update_result["response"],
            "student_profile": update_result.get("updated_profile", profile),
            "action_taken": update_result["action_taken"],
            "student_id": student_id,
            "updates_applied": update_result.get("updates_applied")
        }

    async def _extract_and_apply_updates(
        self,
        query: str,
        profile: Dict[str, Any],
        student_id: str
    ) -> Dict[str, Any]:
        """
        Use LLM to determine if query contains update info and apply updates.

        Returns dict with response, action_taken, and optionally updates_applied.
        """
        # Ask LLM to analyze if this is an update and extract structured data
        prompt = STUDENT_AGENT_UPDATE_EXTRACT_PROMPT.format(
            profile=format_student_profile(profile),
            query=query
        )

        extraction_response = await self.call_llm(
            messages=[
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "extract_update_info",
                "student": profile.get("name"),
                "query_snippet": query[:100]
            },
            temperature=0.1,  # Low temp for structured extraction
            max_tokens=500
        )

        # Parse the JSON response
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = extraction_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            print(f"[DEBUG] Update extraction response: {cleaned[:200]}...")
            extraction = json.loads(cleaned)
            print(f"[DEBUG] Parsed extraction: is_update={extraction.get('is_update')}, updates={extraction.get('updates')}")
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON parse error: {e}, response was: {extraction_response[:200]}")
            # If parsing fails, treat as not an update
            return {
                "response": "I had trouble understanding that request. Could you rephrase what you'd like to update?",
                "action_taken": "parse_error"
            }

        # Check if LLM detected items that already exist in the profile
        already_exists = extraction.get("already_exists")
        if already_exists and not extraction.get("is_update", False):
            student_name = profile.get("name", "the student")
            items_str = ", ".join(f'"{item}"' for item in already_exists)
            return {
                "response": f"{items_str} is already in {student_name}'s profile. Is there anything else you'd like me to update or help you with?",
                "action_taken": "already_exists",
                "updated_profile": profile
            }

        # Check if LLM determined this is an update
        if not extraction.get("is_update", False):
            return {
                "response": extraction.get("reason", "This doesn't appear to be an update request."),
                "action_taken": "not_an_update"
            }

        # Build the update payload
        updates = extraction.get("updates", {})
        profile_updates = {}
        updates_summary_parts = []
        already_exists_items = []  # Track duplicates

        # Handle list fields - support both adding and removing
        for field in ["triggers", "successful_methods", "failed_methods"]:
            existing = list(profile.get(field, []) or [])
            modified = False

            # Handle additions
            add_key = f"add_{field}"
            if updates.get(add_key):
                new_items = updates[add_key]
                # Avoid duplicates (case-insensitive check)
                existing_lower = [item.lower() for item in existing]
                added_items = []
                for item in new_items:
                    if item.lower() not in existing_lower:
                        existing.append(item)
                        added_items.append(item)
                        modified = True
                    else:
                        # Track items that already exist
                        already_exists_items.append((field, item))
                if added_items:
                    updates_summary_parts.append(f"- Added to {field.replace('_', ' ')}: {', '.join(added_items)}")

            # Handle removals
            remove_key = f"remove_{field}"
            if updates.get(remove_key):
                items_to_remove = updates[remove_key]
                original_count = len(existing)
                # Case-insensitive removal
                items_to_remove_lower = [item.lower() for item in items_to_remove]
                existing = [item for item in existing if item.lower() not in items_to_remove_lower]
                if len(existing) < original_count:
                    modified = True
                    updates_summary_parts.append(f"- Removed from {field.replace('_', ' ')}: {', '.join(items_to_remove)}")

            if modified:
                profile_updates[field] = existing

        # If nothing to update but we found duplicates, inform the user
        if not profile_updates and not updates.get("notes") and already_exists_items:
            student_name = profile.get("name", "the student")
            duplicate_msgs = []
            for field, item in already_exists_items:
                field_name = field.replace('_', ' ')
                duplicate_msgs.append(f'"{item}" is already in {student_name}\'s {field_name}')

            return {
                "response": f"{'. '.join(duplicate_msgs)}. Is there anything else you'd like me to update or help you with?",
                "action_taken": "duplicate_detected",
                "updated_profile": profile
            }

        # Handle notes - append with timestamp
        if updates.get("notes"):
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d")
            new_note = f"[{timestamp}] {updates['notes']}"
            existing_notes = profile.get("notes", "") or ""
            if existing_notes:
                profile_updates["notes"] = f"{existing_notes}\n{new_note}"
            else:
                profile_updates["notes"] = new_note
            updates_summary_parts.append(f"- Added note: {updates['notes']}")

        # Apply updates if we have any
        if profile_updates:
            success = await self.memory.update_student_profile(student_id, profile_updates)

            if not success:
                return {
                    "response": "I understood the update but had trouble saving it. Please try again.",
                    "action_taken": "update_save_failed"
                }

            # Generate confirmation response
            updates_summary = "\n".join(updates_summary_parts)
            confirm_prompt = STUDENT_AGENT_UPDATE_CONFIRM_PROMPT.format(
                student_name=profile.get("name", "the student"),
                updates_summary=updates_summary
            )

            confirmation = await self.call_llm(
                messages=[
                    {"role": "user", "content": confirm_prompt}
                ],
                prompt_summary={
                    "action": "confirm_update",
                    "student": profile.get("name"),
                    "fields_updated": list(profile_updates.keys())
                },
                temperature=0.7,
                max_tokens=200
            )

            # Fetch updated profile
            updated_profile = await self.memory.get_student_profile(student_id)

            return {
                "response": confirmation,
                "action_taken": "update_applied",
                "updates_applied": profile_updates,
                "updated_profile": updated_profile
            }
        else:
            return {
                "response": "I didn't find any specific updates to make. Could you be more specific about what you'd like to change?",
                "action_taken": "no_updates_found"
            }

    async def _handle_list(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle a request to list/search students."""
        # Search for students matching the query
        matches = await self.memory.find_similar_students(query, top_k=5)

        if not matches:
            return {
                "response": "I couldn't find any students matching your criteria.",
                "action_taken": "list_empty",
                "students": []
            }

        # Format the list
        student_list = []
        for match in matches:
            student_list.append({
                "name": match.get("name"),
                "grade": match.get("grade"),
                "disability_type": match.get("disability_type"),
                "student_id": match.get("student_id")
            })

        response_parts = ["Here are the students I found:\n"]
        for i, student in enumerate(student_list, 1):
            response_parts.append(
                f"{i}. {student['name']} (Grade {student['grade']}) - {student['disability_type']}"
            )

        return {
            "response": "\n".join(response_parts),
            "action_taken": "list_retrieved",
            "students": student_list
        }

    async def get_student_context(
        self,
        student_name: Optional[str] = None,
        student_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get student context for use by other agents.
        This is a utility method, not a full process() call.
        """
        profile = None

        if student_id:
            profile = await self.memory.get_student_profile(student_id)
        elif student_name:
            matches = await self.memory.search_student_by_name(student_name)
            if matches:
                profile = matches[0]

        if not profile:
            return None

        # Get student_id - Supabase uses 'id', Pinecone may use 'student_id'
        student_id_value = profile.get("id") or profile.get("student_id")

        # Add step for context retrieval (non-LLM operation)
        self.add_step(
            prompt={"action": "get_context", "student": student_name or student_id},
            response={"found": True, "student_id": student_id_value}
        )

        return {
            "student_id": student_id_value,
            "name": profile.get("name"),
            "disability_type": profile.get("disability_type"),
            "learning_style": profile.get("learning_style"),
            "triggers": profile.get("triggers", []),
            "successful_methods": profile.get("successful_methods", []),
            "failed_methods": profile.get("failed_methods", []),
            # Include full profile for agents that need more details
            "profile": profile
        }
