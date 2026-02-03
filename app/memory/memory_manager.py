"""
Unified Memory Manager.
Provides a single interface for both short-term (Supabase) and long-term (Pinecone) memory.

Data sources:
- Students: Supabase only (single source of truth)
- Teaching methods: Pinecone (for RAG/semantic search)
- Conversations/messages: Supabase
"""
from typing import Optional, List, Dict, Any
from datetime import date

from app.memory.supabase_client import SupabaseClient, get_supabase_client
from app.memory.pinecone_client import PineconeClient, get_pinecone_client
from app.core.llm_client import LLMClient, get_llm_client


class MemoryManager:
    """
    Unified interface for all memory operations.
    Coordinates between Supabase (short-term) and Pinecone (long-term).
    """

    def __init__(
        self,
        supabase: Optional[SupabaseClient] = None,
        pinecone: Optional[PineconeClient] = None,
        llm: Optional[LLMClient] = None
    ):
        self.supabase = supabase or get_supabase_client()
        self.pinecone = pinecone or get_pinecone_client()
        self.llm = llm or get_llm_client()

    # ==================== Student Operations (Hybrid: Supabase + Pinecone) ====================
    #
    # Architecture:
    # - Supabase: Canonical student data (CRUD operations, structured queries)
    # - Pinecone: Student embeddings for semantic search (find similar students)
    #

    async def get_student_profile(
        self,
        student_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a student's full profile from Supabase (canonical source)."""
        return await self.supabase.get_student(student_id)

    async def search_student_by_name(
        self,
        name: str
    ) -> List[Dict[str, Any]]:
        """
        Search for students by name.

        Uses Supabase as the single source of truth.
        """
        student = await self.supabase.get_student_by_name(name)
        if student:
            return [student]
        return []

    async def find_similar_students(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find students similar to a description/query using semantic search.

        Uses Pinecone embeddings for similarity, enriches with Supabase data.
        """
        embedding = await self.llm.embed(query)
        pinecone_results = await self.pinecone.search_students(embedding, top_k=top_k)

        # Enrich with Supabase data
        enriched = []
        for result in pinecone_results:
            student_id = result.get("id") or result.get("student_id")
            if student_id:
                full_profile = await self.supabase.get_student(student_id)
                if full_profile:
                    # Add similarity score from Pinecone
                    full_profile["similarity_score"] = result.get("score")
                    enriched.append(full_profile)
                else:
                    enriched.append(result)
        return enriched

    async def create_student(
        self,
        student_id: str,
        profile_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new student profile.

        Stores in both Supabase (canonical) and Pinecone (for search).
        """
        # Ensure ID is set
        profile_data["id"] = student_id

        # Create in Supabase
        student = await self.supabase.create_student(profile_data)
        if not student:
            return None

        # Create embedding for Pinecone
        profile_text = self._profile_to_text(profile_data)
        embedding = await self.llm.embed(profile_text)
        await self.pinecone.upsert_student_profile(student_id, embedding, profile_data)

        return student

    async def update_student_profile(
        self,
        student_id: str,
        profile_data: Dict[str, Any]
    ) -> bool:
        """
        Update a student's profile.

        Updates Supabase only (single source of truth for students).
        """
        updated = await self.supabase.update_student(student_id, profile_data)
        return updated is not None

    async def delete_student(self, student_id: str) -> bool:
        """
        Delete a student from both Supabase and Pinecone.
        """
        # Delete from Supabase
        deleted = await self.supabase.delete_student(student_id)

        # Delete from Pinecone
        try:
            self.pinecone.index.delete(ids=[student_id], namespace="student-profiles")
        except Exception:
            pass  # Pinecone deletion is best-effort

        return deleted

    async def list_students(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all students from Supabase."""
        return await self.supabase.list_students(limit)

    async def search_students_by_disability(
        self,
        disability_type: str
    ) -> List[Dict[str, Any]]:
        """Search students by disability type (exact match in Supabase)."""
        return await self.supabase.search_students_by_disability(disability_type)

    async def search_students_by_grade(self, grade: str) -> List[Dict[str, Any]]:
        """Search students by grade (exact match in Supabase)."""
        return await self.supabase.search_students_by_grade(grade)

    def _profile_to_text(self, profile: Dict[str, Any]) -> str:
        """Convert profile data to text for embedding."""
        parts = [
            f"Student: {profile.get('name', 'Unknown')}",
            f"Grade: {profile.get('grade', 'Unknown')}",
            f"Disability: {profile.get('disability_type', 'Unknown')}",
            f"Learning style: {profile.get('learning_style', 'Unknown')}",
        ]
        triggers = profile.get("triggers")
        if triggers:
            if isinstance(triggers, list):
                parts.append(f"Triggers: {', '.join(triggers)}")
            else:
                parts.append(f"Triggers: {triggers}")

        successful = profile.get("successful_methods")
        if successful:
            if isinstance(successful, list):
                parts.append(f"Successful methods: {', '.join(successful)}")
            else:
                parts.append(f"Successful methods: {successful}")

        failed = profile.get("failed_methods")
        if failed:
            if isinstance(failed, list):
                parts.append(f"Failed methods: {', '.join(failed)}")
            else:
                parts.append(f"Failed methods: {failed}")

        notes = profile.get("notes")
        if notes:
            parts.append(f"Notes: {notes}")

        return ". ".join(parts)

    # ==================== Teaching Methods Operations ====================

    async def search_teaching_methods(
        self,
        query: str,
        top_k: int = 7,
        exclude_methods: Optional[List[str]] = None,
        disability_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant teaching methods.

        Args:
            query: Natural language query
            top_k: Number of results
            exclude_methods: Methods to exclude (e.g., failed methods for a student)
            disability_type: Filter by applicable disability
        """
        embedding = await self.llm.embed(query)

        # Build filter
        # Note: scraped data uses 'disability_categories', normalize the type
        filter_dict = None
        if disability_type:
            # Normalize disability type to lowercase for matching
            disability_normalized = disability_type.lower().replace(" ", "_")
            filter_dict = {
                "disability_categories": {"$in": [disability_normalized, disability_type]}
            }

        results = await self.pinecone.search_teaching_methods(
            embedding, top_k=top_k * 2, filter_dict=filter_dict
        )

        # Filter out excluded methods
        if exclude_methods:
            exclude_set = set(m.lower() for m in exclude_methods)
            results = [
                r for r in results
                if (r.get("method_name") or r.get("title", "")).lower() not in exclude_set
            ]

        return results[:top_k]

    async def add_teaching_method(
        self,
        method_id: str,
        method_data: Dict[str, Any]
    ) -> bool:
        """Add a teaching method to the knowledge base."""
        method_text = self._method_to_text(method_data)
        embedding = await self.llm.embed(method_text)
        return await self.pinecone.upsert_teaching_method(
            method_id, embedding, method_data
        )

    def _method_to_text(self, method: Dict[str, Any]) -> str:
        """Convert method data to text for embedding."""
        parts = [
            f"Teaching method: {method.get('method_name', 'Unknown')}",
            f"Category: {method.get('category', 'Unknown')}",
            f"Description: {method.get('description', '')}",
        ]
        if method.get("applicable_disabilities"):
            parts.append(
                f"Applicable for: {', '.join(method['applicable_disabilities'])}"
            )
        return ". ".join(parts)

    # ==================== Conversation Operations ====================

    async def get_or_create_conversation(
        self,
        session_id: str,
        teacher_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get existing conversation or create a new one."""
        conversation = await self.supabase.get_conversation_by_session(session_id)
        if not conversation:
            conversation = await self.supabase.create_conversation(
                session_id, teacher_id
            )
        return conversation

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        agent_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a message to a conversation."""
        return await self.supabase.add_message(
            conversation_id, role, content, agent_used
        )

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        return await self.supabase.get_messages(conversation_id, limit)

    # ==================== Daily Context Operations ====================

    async def get_daily_context(
        self,
        teacher_id: str,
        student_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get today's context for a teacher."""
        return await self.supabase.get_daily_context(
            teacher_id,
            context_date=date.today(),
            student_id=student_id
        )

    async def add_alert(
        self,
        teacher_id: str,
        content: str,
        student_id: Optional[str] = None,
        priority: int = 1
    ) -> Dict[str, Any]:
        """Add an alert to daily context."""
        return await self.supabase.add_daily_context(
            teacher_id=teacher_id,
            context_type="alert",
            content=content,
            student_id=student_id,
            priority=priority
        )

    # ==================== Intervention Recording ====================

    async def record_intervention(
        self,
        student_id: str,
        method_used: str,
        context: str,
        outcome: str,
        teacher_notes: Optional[str] = None
    ) -> bool:
        """Record an intervention outcome for learning."""
        import uuid
        from datetime import datetime

        intervention_id = f"INT_{uuid.uuid4().hex[:8]}"
        intervention_text = f"{context}. Used {method_used}. Outcome: {outcome}"
        embedding = await self.llm.embed(intervention_text)

        metadata = {
            "student_id": student_id,
            "method_used": method_used,
            "context": context,
            "outcome": outcome,
            "teacher_notes": teacher_notes or "",
            "date": datetime.now().date().isoformat()
        }

        return await self.pinecone.upsert_intervention(
            intervention_id, embedding, metadata
        )

    async def get_past_interventions(
        self,
        context: str,
        student_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar past interventions."""
        embedding = await self.llm.embed(context)
        return await self.pinecone.search_interventions(
            embedding, top_k=top_k, student_id=student_id
        )

    # ==================== Events Operations ====================

    async def get_todays_events(self, teacher_id: str) -> List[Dict[str, Any]]:
        """
        Get today's events for a teacher.
        Combines one-off events from events table with recurring events from schedule_templates.
        """
        today = date.today()

        # Get one-off events from events table
        one_off_events = await self.supabase.get_events_by_date(teacher_id, today)

        # Get schedule templates for today's day of week
        # Python weekday(): 0=Monday, 1=Tuesday, ..., 6=Sunday
        # Our schema: 1=Monday, 2=Tuesday, ..., 5=Friday, 6=Saturday, 0=Sunday
        python_weekday = today.weekday()  # 0=Mon, 6=Sun
        db_weekday = python_weekday + 1 if python_weekday < 6 else 0  # Convert to 1=Mon, 0=Sun

        templates = await self.supabase.get_schedule_templates_for_day(teacher_id, db_weekday)

        # Convert templates to event format
        template_events = []
        for template in templates:
            event = {
                "id": f"template-{template.get('id', '')}",
                "teacher_id": teacher_id,
                "title": template.get("title", ""),
                "description": template.get("description", ""),
                "event_type": self._map_template_type_to_event_type(template.get("event_type", "")),
                "event_date": today.isoformat(),
                "start_time": template.get("start_time"),
                "end_time": template.get("end_time"),
                "is_recurring": True,
                "recurrence_pattern": template.get("recurrence_type"),
                "sensory_factors": template.get("sensory_factors") or {},
                "affected_students": [],
                "notes": None,
                "from_template": True,
                "template_id": template.get("id"),
                "metadata": template.get("metadata") or {}
            }
            template_events.append(event)

        # Combine and sort by start_time
        all_events = one_off_events + template_events
        all_events.sort(key=lambda e: e.get("start_time") or "00:00")

        return all_events

    def _map_template_type_to_event_type(self, template_type: str) -> str:
        """Map schedule template event_type to events table event_type."""
        mapping = {
            "class": "class_schedule",
            "one_on_one": "class_schedule",
            "meeting": "special_event",
            "communication": "special_event",
            "planning": "class_schedule",
            "reporting": "special_event"
        }
        return mapping.get(template_type, "class_schedule")

    async def get_upcoming_events(
        self,
        teacher_id: str,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get upcoming events for the next N days."""
        return await self.supabase.get_upcoming_events(teacher_id, days_ahead)

    async def get_events_affecting_student(
        self,
        teacher_id: str,
        student_id: str,
        days_ahead: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get events that might affect a specific student.

        Returns events where:
        1. The student is in the affected_students list, OR
        2. The event has sensory factors that match the student's triggers
        """
        events = await self.supabase.get_upcoming_events(teacher_id, days_ahead)

        # Get student profile to check triggers
        student = await self.get_student_profile(student_id)
        if not student:
            # If no student profile, just return events where they're explicitly listed
            return [e for e in events if student_id in (e.get("affected_students") or [])]

        student_triggers = student.get("triggers", [])
        trigger_keywords = self._extract_trigger_keywords(student_triggers)

        affected_events = []
        for event in events:
            # Check if student is explicitly listed
            if student_id in (event.get("affected_students") or []):
                affected_events.append(event)
                continue

            # Check if event sensory factors match student triggers
            sensory_factors = event.get("sensory_factors") or {}
            for factor, is_present in sensory_factors.items():
                if is_present and self._trigger_matches_factor(trigger_keywords, factor):
                    affected_events.append(event)
                    break

        return affected_events

    def _extract_trigger_keywords(self, triggers: List[str]) -> List[str]:
        """Extract keywords from trigger descriptions for matching."""
        keywords = []
        for trigger in triggers:
            # Extract individual words, lowercase
            words = trigger.lower().replace(",", " ").split()
            keywords.extend(words)
        return list(set(keywords))

    def _trigger_matches_factor(self, trigger_keywords: List[str], factor: str) -> bool:
        """Check if any trigger keyword matches a sensory factor."""
        factor_lower = factor.lower().replace("_", " ")
        factor_words = factor_lower.split()

        # Check for direct matches or partial matches
        for keyword in trigger_keywords:
            if keyword in factor_words or any(keyword in fw for fw in factor_words):
                return True
            # Also check if factor word appears in keyword
            for fw in factor_words:
                if fw in keyword:
                    return True
        return False

    async def create_event(
        self,
        teacher_id: str,
        title: str,
        event_type: str,
        event_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new event."""
        return await self.supabase.create_event(
            teacher_id=teacher_id,
            title=title,
            event_type=event_type,
            event_date=event_date,
            **kwargs
        )


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create the memory manager singleton."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
