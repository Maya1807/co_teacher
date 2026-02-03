"""
Supabase client for short-term memory operations.
Handles conversations, daily context, alerts, and caching.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uuid

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

from app.config import get_settings


class MockSupabaseClient:
    """
    Mock Supabase client for local testing without Supabase connection.
    Stores data in memory (not persisted).
    """

    def __init__(self):
        self._conversations = {}
        self._messages = {}
        self._daily_context = {}
        self._cache = {}
        self._students = {}
        self._events = {}
        self._schedule_templates = {}
        self._seed_mock_schedule_templates()
        print("INFO: Using MockSupabaseClient (no persistence)")

    def _seed_mock_schedule_templates(self):
        """Seed mock schedule templates for local testing."""
        # Daily classes (Mon-Fri = days 1-5)
        templates = [
            {
                "id": "mock-math",
                "teacher_id": "default",
                "title": "Math Class",
                "event_type": "class",
                "recurrence_type": "weekly",
                "days_of_week": [1, 2, 3, 4, 5],
                "start_time": "09:00",
                "end_time": "10:00",
                "sensory_factors": {"requires_focus": True, "seated_work": True},
                "metadata": {"subject": "math"},
                "is_active": True
            },
            {
                "id": "mock-science",
                "teacher_id": "default",
                "title": "Science Class",
                "event_type": "class",
                "recurrence_type": "weekly",
                "days_of_week": [1, 2, 3, 4, 5],
                "start_time": "10:15",
                "end_time": "11:15",
                "sensory_factors": {"hands_on_activity": True, "group_work": True},
                "metadata": {"subject": "science"},
                "is_active": True
            },
            {
                "id": "mock-reading",
                "teacher_id": "default",
                "title": "Reading Class",
                "event_type": "class",
                "recurrence_type": "weekly",
                "days_of_week": [1, 2, 3, 4, 5],
                "start_time": "11:30",
                "end_time": "12:15",
                "sensory_factors": {"quiet_environment": True, "seated_work": True},
                "metadata": {"subject": "reading"},
                "is_active": True
            },
            {
                "id": "mock-art",
                "teacher_id": "default",
                "title": "Art Class",
                "event_type": "class",
                "recurrence_type": "weekly",
                "days_of_week": [1, 2, 3, 4, 5],
                "start_time": "13:00",
                "end_time": "14:00",
                "sensory_factors": {"hands_on_activity": True, "sensory_materials": True},
                "metadata": {"subject": "art"},
                "is_active": True
            },
            {
                "id": "mock-pe",
                "teacher_id": "default",
                "title": "PE Class",
                "event_type": "class",
                "recurrence_type": "weekly",
                "days_of_week": [1, 2, 3, 4, 5],
                "start_time": "14:15",
                "end_time": "15:00",
                "sensory_factors": {"physical_activity": True, "loud_environment": True, "competitive": True},
                "metadata": {"subject": "pe"},
                "is_active": True
            },
            # One-on-one sessions
            {
                "id": "mock-1on1-mon",
                "teacher_id": "default",
                "title": "One-on-One: Alex",
                "event_type": "one_on_one",
                "recurrence_type": "weekly",
                "days_of_week": [1],
                "start_time": "15:15",
                "end_time": "15:45",
                "sensory_factors": {"quiet_environment": True, "individual_attention": True},
                "metadata": {"student": "Alex"},
                "is_active": True
            },
            {
                "id": "mock-1on1-tue",
                "teacher_id": "default",
                "title": "One-on-One: Jordan",
                "event_type": "one_on_one",
                "recurrence_type": "weekly",
                "days_of_week": [2],
                "start_time": "15:15",
                "end_time": "15:45",
                "sensory_factors": {"quiet_environment": True, "individual_attention": True},
                "metadata": {"student": "Jordan"},
                "is_active": True
            },
            {
                "id": "mock-1on1-wed",
                "teacher_id": "default",
                "title": "One-on-One: Sam",
                "event_type": "one_on_one",
                "recurrence_type": "weekly",
                "days_of_week": [3],
                "start_time": "15:15",
                "end_time": "15:45",
                "sensory_factors": {"quiet_environment": True, "individual_attention": True},
                "metadata": {"student": "Sam"},
                "is_active": True
            },
            {
                "id": "mock-1on1-thu",
                "teacher_id": "default",
                "title": "One-on-One: Maya",
                "event_type": "one_on_one",
                "recurrence_type": "weekly",
                "days_of_week": [4],
                "start_time": "15:15",
                "end_time": "15:45",
                "sensory_factors": {"quiet_environment": True, "individual_attention": True},
                "metadata": {"student": "Maya"},
                "is_active": True
            },
            {
                "id": "mock-1on1-fri",
                "teacher_id": "default",
                "title": "One-on-One: Ethan",
                "event_type": "one_on_one",
                "recurrence_type": "weekly",
                "days_of_week": [5],
                "start_time": "15:15",
                "end_time": "15:45",
                "sensory_factors": {"quiet_environment": True, "individual_attention": True},
                "metadata": {"student": "Ethan"},
                "is_active": True
            },
            # Weekly meetings
            {
                "id": "mock-staff-meeting",
                "teacher_id": "default",
                "title": "Weekly Staff Meeting",
                "event_type": "meeting",
                "recurrence_type": "weekly",
                "days_of_week": [1],
                "start_time": "16:00",
                "end_time": "17:00",
                "sensory_factors": None,
                "metadata": {"notes": "Team coordination"},
                "is_active": True
            },
            {
                "id": "mock-parent-emails",
                "teacher_id": "default",
                "title": "Weekly Parent Update Emails",
                "event_type": "communication",
                "recurrence_type": "weekly",
                "days_of_week": [4],
                "start_time": "16:00",
                "end_time": "17:00",
                "sensory_factors": None,
                "metadata": {"tasks": ["weekly_updates", "behavior_notes"]},
                "is_active": True
            }
        ]
        for t in templates:
            self._schedule_templates[t["id"]] = t
    
    async def create_conversation(self, session_id: str, teacher_id: Optional[str] = None) -> Dict[str, Any]:
        conv_id = str(uuid.uuid4())
        conv = {"id": conv_id, "session_id": session_id, "teacher_id": teacher_id}
        self._conversations[conv_id] = conv
        return conv
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return self._conversations.get(conversation_id)
    
    async def get_conversation_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        for conv in self._conversations.values():
            if conv.get("session_id") == session_id:
                return conv
        return None
    
    async def add_message(self, conversation_id: str, role: str, content: str, agent_used: Optional[str] = None) -> Dict[str, Any]:
        msg = {"id": str(uuid.uuid4()), "conversation_id": conversation_id, "role": role, "content": content, "agent_used": agent_used}
        if conversation_id not in self._messages:
            self._messages[conversation_id] = []
        self._messages[conversation_id].append(msg)
        return msg
    
    async def get_messages(self, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._messages.get(conversation_id, [])[:limit]
    
    async def add_daily_context(self, teacher_id: str, context_type: str, content: str, student_id: Optional[str] = None, priority: int = 0) -> Dict[str, Any]:
        ctx = {"id": str(uuid.uuid4()), "teacher_id": teacher_id, "context_type": context_type, "content": content}
        return ctx
    
    async def get_daily_context(self, teacher_id: str, context_date: Optional[date] = None, student_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []
    
    async def resolve_context(self, context_id: str) -> bool:
        return True
    
    async def record_alert(self, teacher_id: str, alert_type: str, alert_content: str, student_id: Optional[str] = None) -> Dict[str, Any]:
        return {"id": str(uuid.uuid4())}
    
    async def was_alert_sent(self, teacher_id: str, alert_type: str, student_id: Optional[str] = None, hours_ago: int = 24) -> bool:
        return False
    
    async def add_pending_feedback(self, teacher_id: str, action_type: str, original_suggestion: str, student_id: Optional[str] = None) -> Dict[str, Any]:
        return {"id": str(uuid.uuid4())}
    
    async def get_pending_feedback(self, teacher_id: str) -> List[Dict[str, Any]]:
        return []
    
    async def resolve_feedback(self, feedback_id: str, status: str, feedback_notes: Optional[str] = None) -> bool:
        return True
    
    async def get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(cache_key)
    
    async def set_cache(self, cache_key: str, prompt_hash: str, response: str, agent_type: str, expires_at: datetime) -> Dict[str, Any]:
        entry = {"cache_key": cache_key, "response": response, "agent_type": agent_type}
        self._cache[cache_key] = entry
        return entry
    
    async def increment_cache_hit(self, cache_key: str) -> bool:
        return True
    
    async def delete_cache(self, cache_key: str) -> bool:
        self._cache.pop(cache_key, None)
        return True
    
    async def clear_expired_cache(self) -> int:
        return 0
    
    async def log_llm_usage(self, model: str, prompt_tokens: int, completion_tokens: int, cost: float, agent_type: Optional[str] = None) -> Dict[str, Any]:
        return {"id": str(uuid.uuid4())}
    
    async def get_total_spent(self) -> float:
        return 0.0

    async def get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        return self._students.get(student_id)

    async def get_student_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        name_lower = name.lower()
        for student in self._students.values():
            if name_lower in student.get("name", "").lower():
                return student
        return None

    async def list_students(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self._students.values())[:limit]

    async def create_student(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        student_id = student_data.get("id", str(uuid.uuid4()))
        student_data["id"] = student_id
        self._students[student_id] = student_data
        return student_data

    async def update_student(self, student_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if student_id in self._students:
            self._students[student_id].update(updates)
            return self._students[student_id]
        return None

    async def delete_student(self, student_id: str) -> bool:
        return self._students.pop(student_id, None) is not None

    async def search_students_by_disability(self, disability_type: str) -> List[Dict[str, Any]]:
        disability_lower = disability_type.lower()
        return [s for s in self._students.values() if disability_lower in s.get("disability_type", "").lower()]

    async def search_students_by_grade(self, grade: str) -> List[Dict[str, Any]]:
        return [s for s in self._students.values() if s.get("grade") == grade]

    # ==================== Events Operations ====================

    async def create_event(
        self,
        teacher_id: str,
        title: str,
        event_type: str,
        event_date: date,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        is_recurring: bool = False,
        recurrence_pattern: Optional[str] = None,
        sensory_factors: Optional[Dict[str, bool]] = None,
        affected_students: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "teacher_id": teacher_id,
            "title": title,
            "event_type": event_type,
            "event_date": event_date.isoformat() if isinstance(event_date, date) else event_date,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "is_recurring": is_recurring,
            "recurrence_pattern": recurrence_pattern,
            "sensory_factors": sensory_factors or {},
            "affected_students": affected_students or [],
            "notes": notes,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        if not hasattr(self, '_events'):
            self._events = {}
        self._events[event_id] = event
        return event

    async def get_events_by_date(
        self,
        teacher_id: str,
        event_date: date
    ) -> List[Dict[str, Any]]:
        if not hasattr(self, '_events'):
            self._events = {}
        date_str = event_date.isoformat() if isinstance(event_date, date) else event_date
        return [
            e for e in self._events.values()
            if e.get("teacher_id") == teacher_id and e.get("event_date") == date_str
        ]

    async def get_schedule_templates_for_day(
        self,
        teacher_id: str,
        day_of_week: int
    ) -> List[Dict[str, Any]]:
        """
        Get schedule templates that apply to a specific day of week.
        day_of_week: 1=Monday, 2=Tuesday, ..., 5=Friday, 6=Saturday, 0=Sunday
        """
        if not hasattr(self, '_schedule_templates'):
            self._schedule_templates = {}

        results = []
        for template in self._schedule_templates.values():
            if template.get("teacher_id") != teacher_id:
                continue
            if not template.get("is_active", True):
                continue

            # Check if this template applies to the given day
            days = template.get("days_of_week", [])
            if days and day_of_week in days:
                results.append(template)

        return sorted(results, key=lambda x: x.get("start_time") or "00:00")

    async def get_upcoming_events(
        self,
        teacher_id: str,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        if not hasattr(self, '_events'):
            self._events = {}
        from datetime import timedelta
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        results = []
        for e in self._events.values():
            if e.get("teacher_id") != teacher_id:
                continue
            event_date_str = e.get("event_date")
            if event_date_str:
                event_date_obj = date.fromisoformat(event_date_str) if isinstance(event_date_str, str) else event_date_str
                if today <= event_date_obj <= end_date:
                    results.append(e)
        return sorted(results, key=lambda x: x.get("event_date", ""))

    async def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not hasattr(self, '_events'):
            self._events = {}
        if event_id in self._events:
            self._events[event_id].update(updates)
            self._events[event_id]["updated_at"] = datetime.now().isoformat()
            return self._events[event_id]
        return None

    async def delete_event(self, event_id: str) -> bool:
        if not hasattr(self, '_events'):
            self._events = {}
        return self._events.pop(event_id, None) is not None


class SupabaseClient:
    """
    Client for Supabase operations.
    Manages short-term memory: conversations, daily context, cache.
    """

    def __init__(self):
        settings = get_settings()
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )

    # ==================== Conversations ====================

    async def create_conversation(
        self,
        session_id: str,
        teacher_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation."""
        result = self.client.table("conversations").insert({
            "session_id": session_id,
            "teacher_id": teacher_id
        }).execute()
        return result.data[0] if result.data else None

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID."""
        result = self.client.table("conversations").select("*").eq(
            "id", conversation_id
        ).execute()
        return result.data[0] if result.data else None

    async def get_conversation_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by session ID."""
        result = self.client.table("conversations").select("*").eq(
            "session_id", session_id
        ).order("created_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    # ==================== Conversation Messages ====================

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        agent_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a message to a conversation."""
        result = self.client.table("conversation_messages").insert({
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "agent_used": agent_used
        }).execute()
        return result.data[0] if result.data else None

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get messages from a conversation."""
        result = self.client.table("conversation_messages").select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at", desc=False).limit(limit).execute()
        return result.data or []

    # ==================== Daily Context ====================

    async def add_daily_context(
        self,
        teacher_id: str,
        context_type: str,
        content: str,
        student_id: Optional[str] = None,
        priority: int = 0
    ) -> Dict[str, Any]:
        """Add a daily context entry (alert, observation, note, event)."""
        result = self.client.table("daily_context").insert({
            "teacher_id": teacher_id,
            "context_type": context_type,
            "content": content,
            "student_id": student_id,
            "priority": priority,
            "date": date.today().isoformat()
        }).execute()
        return result.data[0] if result.data else None

    async def get_daily_context(
        self,
        teacher_id: str,
        context_date: Optional[date] = None,
        student_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get daily context for a teacher."""
        context_date = context_date or date.today()
        query = self.client.table("daily_context").select("*").eq(
            "teacher_id", teacher_id
        ).eq("date", context_date.isoformat())

        if student_id:
            query = query.eq("student_id", student_id)

        result = query.order("priority", desc=True).execute()
        return result.data or []

    async def resolve_context(self, context_id: str) -> bool:
        """Mark a context entry as resolved."""
        result = self.client.table("daily_context").update({
            "is_resolved": True
        }).eq("id", context_id).execute()
        return bool(result.data)

    # ==================== Alerts Sent ====================

    async def record_alert(
        self,
        teacher_id: str,
        alert_type: str,
        alert_content: str,
        student_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record that an alert was sent."""
        result = self.client.table("alerts_sent").insert({
            "teacher_id": teacher_id,
            "alert_type": alert_type,
            "alert_content": alert_content,
            "student_id": student_id
        }).execute()
        return result.data[0] if result.data else None

    async def was_alert_sent(
        self,
        teacher_id: str,
        alert_type: str,
        student_id: Optional[str] = None,
        hours_ago: int = 24
    ) -> bool:
        """Check if a similar alert was sent recently."""
        query = self.client.table("alerts_sent").select("id").eq(
            "teacher_id", teacher_id
        ).eq("alert_type", alert_type)

        if student_id:
            query = query.eq("student_id", student_id)

        # Filter by time (Supabase uses gte for comparison)
        result = query.execute()
        return bool(result.data)

    # ==================== Pending Feedback ====================

    async def add_pending_feedback(
        self,
        teacher_id: str,
        action_type: str,
        original_suggestion: str,
        student_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a pending feedback request."""
        result = self.client.table("pending_feedback").insert({
            "teacher_id": teacher_id,
            "action_type": action_type,
            "original_suggestion": original_suggestion,
            "student_id": student_id
        }).execute()
        return result.data[0] if result.data else None

    async def get_pending_feedback(
        self,
        teacher_id: str
    ) -> List[Dict[str, Any]]:
        """Get all pending feedback for a teacher."""
        result = self.client.table("pending_feedback").select("*").eq(
            "teacher_id", teacher_id
        ).eq("status", "pending").execute()
        return result.data or []

    async def resolve_feedback(
        self,
        feedback_id: str,
        status: str,
        feedback_notes: Optional[str] = None
    ) -> bool:
        """Resolve a feedback request."""
        result = self.client.table("pending_feedback").update({
            "status": status,
            "feedback_notes": feedback_notes,
            "resolved_at": datetime.now().isoformat()
        }).eq("id", feedback_id).execute()
        return bool(result.data)

    # ==================== Response Cache ====================

    async def get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get a cached response."""
        result = self.client.table("response_cache").select("*").eq(
            "cache_key", cache_key
        ).gt("expires_at", datetime.now().isoformat()).execute()
        return result.data[0] if result.data else None

    async def set_cache(
        self,
        cache_key: str,
        prompt_hash: str,
        response: str,
        agent_type: str,
        expires_at: datetime
    ) -> Dict[str, Any]:
        """Set a cached response."""
        result = self.client.table("response_cache").upsert({
            "cache_key": cache_key,
            "prompt_hash": prompt_hash,
            "response": response,
            "agent_type": agent_type,
            "expires_at": expires_at.isoformat()
        }).execute()
        return result.data[0] if result.data else None

    async def increment_cache_hit(self, cache_key: str) -> bool:
        """Increment the hit count for a cache entry."""
        # Supabase doesn't support increment directly, so we need to fetch and update
        current = await self.get_cache(cache_key)
        if current:
            result = self.client.table("response_cache").update({
                "hit_count": current.get("hit_count", 0) + 1
            }).eq("cache_key", cache_key).execute()
            return bool(result.data)
        return False

    async def delete_cache(self, cache_key: str) -> bool:
        """Delete a cache entry."""
        result = self.client.table("response_cache").delete().eq(
            "cache_key", cache_key
        ).execute()
        return True

    async def clear_expired_cache(self) -> int:
        """Clear expired cache entries."""
        result = self.client.table("response_cache").delete().lt(
            "expires_at", datetime.now().isoformat()
        ).execute()
        return len(result.data) if result.data else 0

    # ==================== Budget Tracking ====================

    async def log_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log LLM API usage for budget tracking."""
        result = self.client.table("budget_tracking").insert({
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "agent_type": agent_type
        }).execute()
        return result.data[0] if result.data else None

    async def get_total_spent(self) -> float:
        """Get total amount spent on LLM calls."""
        result = self.client.table("budget_tracking").select("cost").execute()
        if result.data:
            return sum(row["cost"] for row in result.data)
        return 0.0

    # ==================== Students ====================

    async def get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get a student by ID."""
        result = self.client.table("students").select("*").eq(
            "id", student_id
        ).execute()
        return result.data[0] if result.data else None

    async def get_student_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a student by exact name match."""
        result = self.client.table("students").select("*").ilike(
            "name", f"%{name}%"
        ).execute()
        return result.data[0] if result.data else None

    async def list_students(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all students."""
        result = self.client.table("students").select("*").limit(limit).execute()
        return result.data or []

    async def create_student(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new student."""
        result = self.client.table("students").insert(student_data).execute()
        return result.data[0] if result.data else None

    async def update_student(
        self,
        student_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a student's profile."""
        result = self.client.table("students").update(updates).eq(
            "id", student_id
        ).execute()
        return result.data[0] if result.data else None

    async def delete_student(self, student_id: str) -> bool:
        """Delete a student."""
        result = self.client.table("students").delete().eq(
            "id", student_id
        ).execute()
        return bool(result.data)

    async def search_students_by_disability(
        self,
        disability_type: str
    ) -> List[Dict[str, Any]]:
        """Search students by disability type."""
        result = self.client.table("students").select("*").ilike(
            "disability_type", f"%{disability_type}%"
        ).execute()
        return result.data or []

    async def search_students_by_grade(self, grade: str) -> List[Dict[str, Any]]:
        """Search students by grade."""
        result = self.client.table("students").select("*").eq(
            "grade", grade
        ).execute()
        return result.data or []

    # ==================== Events Operations ====================

    async def create_event(
        self,
        teacher_id: str,
        title: str,
        event_type: str,
        event_date: date,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        is_recurring: bool = False,
        recurrence_pattern: Optional[str] = None,
        sensory_factors: Optional[Dict[str, bool]] = None,
        affected_students: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new event."""
        data = {
            "teacher_id": teacher_id,
            "title": title,
            "event_type": event_type,
            "event_date": event_date.isoformat() if isinstance(event_date, date) else event_date,
            "is_recurring": is_recurring
        }
        if description:
            data["description"] = description
        if start_time:
            data["start_time"] = start_time
        if end_time:
            data["end_time"] = end_time
        if recurrence_pattern:
            data["recurrence_pattern"] = recurrence_pattern
        if sensory_factors:
            data["sensory_factors"] = sensory_factors
        if affected_students:
            data["affected_students"] = affected_students
        if notes:
            data["notes"] = notes

        result = self.client.table("events").insert(data).execute()
        return result.data[0] if result.data else None

    async def get_events_by_date(
        self,
        teacher_id: str,
        event_date: date
    ) -> List[Dict[str, Any]]:
        """Get events for a specific date."""
        date_str = event_date.isoformat() if isinstance(event_date, date) else event_date
        result = self.client.table("events").select("*").eq(
            "teacher_id", teacher_id
        ).eq("event_date", date_str).order("start_time").execute()
        return result.data or []

    async def get_schedule_templates_for_day(
        self,
        teacher_id: str,
        day_of_week: int
    ) -> List[Dict[str, Any]]:
        """
        Get schedule templates that apply to a specific day of week.
        day_of_week: 1=Monday, 2=Tuesday, ..., 5=Friday, 6=Saturday, 0=Sunday
        """
        try:
            # Use filter with cs (contains) operator for array column
            # Format: column=cs.{value} for PostgreSQL array contains
            result = self.client.table("schedule_templates").select("*").eq(
                "teacher_id", teacher_id
            ).eq("is_active", True).filter(
                "days_of_week", "cs", f"{{{day_of_week}}}"
            ).order("start_time").execute()
            return result.data or []
        except Exception as e:
            print(f"Warning: Could not fetch schedule templates: {e}")
            return []

    async def get_upcoming_events(
        self,
        teacher_id: str,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get upcoming events for the next N days."""
        from datetime import timedelta
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        result = self.client.table("events").select("*").eq(
            "teacher_id", teacher_id
        ).gte("event_date", today.isoformat()).lte(
            "event_date", end_date.isoformat()
        ).order("event_date").order("start_time").execute()
        return result.data or []

    async def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an event."""
        result = self.client.table("events").update(updates).eq(
            "id", event_id
        ).execute()
        return result.data[0] if result.data else None

    async def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        result = self.client.table("events").delete().eq(
            "id", event_id
        ).execute()
        return bool(result.data)


# Singleton instance
_supabase_client = None


def get_supabase_client():
    """Get or create the Supabase client singleton. Returns MockSupabaseClient if connection fails or USE_MOCK_SERVICES is set."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        
        # Force mock client if USE_MOCK_SERVICES is set
        if settings.use_mock_services:
            print("INFO: USE_MOCK_SERVICES=true, using MockSupabaseClient")
            _supabase_client = MockSupabaseClient()
            return _supabase_client
        
        try:
            _supabase_client = SupabaseClient()
        except Exception as e:
            print(f"WARNING: Failed to connect to Supabase: {e}")
            print("WARNING: Using MockSupabaseClient for local testing")
            _supabase_client = MockSupabaseClient()
    return _supabase_client
