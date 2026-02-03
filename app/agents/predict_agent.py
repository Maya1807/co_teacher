"""
Predict Agent.
Handles predictive analysis and proactive intervention suggestions based on
upcoming events and student profiles.
"""
from typing import Dict, Any, Optional, List

from app.agents.base_agent import BaseAgent
from app.utils.prompts import (
    PREDICT_AGENT_SYSTEM,
    PREDICT_DAILY_BRIEFING_PROMPT,
    PREDICT_EVENT_ANALYSIS_PROMPT,
    PREDICT_STUDENT_RISK_PROMPT,
    format_student_profile
)


class PredictAgent(BaseAgent):
    """
    Agent for predictive analysis and proactive intervention suggestions.

    Responsibilities:
    - Analyze upcoming events for potential student triggers
    - Generate early warnings for teachers
    - Suggest preventive strategies based on student profiles
    - Provide daily briefings with predictions
    """

    MODULE_NAME = "PREDICT_AGENT"

    # Sensory factor keywords for matching triggers
    SENSORY_FACTOR_KEYWORDS = {
        "loud_sounds": ["loud", "noise", "noisy", "sound", "alarm", "bell", "siren"],
        "bright_lights": ["light", "bright", "flash", "strobe", "fluorescent"],
        "crowds": ["crowd", "crowded", "people", "busy", "packed", "assembly"],
        "unexpected": ["unexpected", "surprise", "sudden", "unannounced", "change"],
        "transitions": ["transition", "change", "schedule", "routine", "different"],
        "physical_contact": ["touch", "contact", "physical", "bumping", "crowded"],
        "time_pressure": ["timed", "rush", "hurry", "deadline", "pressure", "test"],
        "confined_spaces": ["small", "confined", "cramped", "enclosed", "tight"],
        "new_environment": ["new", "unfamiliar", "different", "outside", "field trip"],
    }

    async def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a prediction-related query.

        Args:
            input_data: Contains 'query' and optionally:
                - 'action': "daily_briefing" | "event_analysis" | "student_risk"
                - 'student_id': For student-specific risk analysis
                - 'event_id': For event-specific analysis
            context: Optional context with teacher_id

        Returns:
            Dict with 'response', 'predictions', 'action_taken'
        """
        query = input_data.get("prompt", "")
        action = input_data.get("action", "daily_briefing")
        teacher_id = context.get("teacher_id", "default") if context else "default"

        if action == "event_analysis":
            event_id = input_data.get("event_id")
            return await self._analyze_event(event_id, teacher_id, context)
        elif action == "student_risk":
            student_id = input_data.get("student_id")
            event_id = input_data.get("event_id")
            return await self._analyze_student_risk(student_id, event_id, teacher_id, context)
        else:
            # Default: daily_briefing
            return await self.generate_daily_briefing(teacher_id, query, context)

    async def generate_daily_briefing(
        self,
        teacher_id: str,
        query: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a morning briefing with predictions for today's events.

        Returns predictions for students who may be affected by today's schedule.
        """
        # Get today's events
        events = await self.memory.get_todays_events(teacher_id)

        if not events:
            return {
                "response": "No scheduled events for today. It looks like a regular day.",
                "predictions": [],
                "action_taken": "daily_briefing",
                "events_analyzed": 0
            }

        # Get all students to check against events
        students = await self.memory.list_students(limit=50)

        # Analyze risks for all event-student combinations
        predictions = []
        for event in events:
            event_predictions = await self.analyze_event_risks(event, students)
            predictions.extend(event_predictions)

        # Sort by risk level (high first)
        risk_order = {"high": 0, "medium": 1, "low": 2}
        predictions.sort(key=lambda p: risk_order.get(p.get("risk_level", "low"), 2))

        # Format for LLM to synthesize
        events_summary = self._format_events_for_prompt(events)
        at_risk_summary = self._format_at_risk_students(predictions)

        # Generate natural language briefing
        prompt = PREDICT_DAILY_BRIEFING_PROMPT.format(
            events=events_summary,
            at_risk_students=at_risk_summary
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": PREDICT_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "daily_briefing",
                "events_count": len(events),
                "predictions_count": len(predictions)
            },
            temperature=0.7,
            max_tokens=800
        )

        return {
            "response": response,
            "predictions": predictions,
            "action_taken": "daily_briefing",
            "events_analyzed": len(events)
        }

    async def analyze_event_risks(
        self,
        event: Dict[str, Any],
        students: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze a specific event against all student profiles.

        Returns a list of predictions for students who may be affected.
        """
        predictions = []

        for student in students:
            risk_result = self._calculate_risk(student, event)

            if risk_result["risk_level"] != "none":
                predictions.append({
                    "student_id": student.get("id") or student.get("student_id"),
                    "student_name": student.get("name"),
                    "event_id": event.get("id"),
                    "event_title": event.get("title"),
                    "event_time": event.get("start_time"),
                    "risk_level": risk_result["risk_level"],
                    "triggers_matched": risk_result["triggers_matched"],
                    "factors_matched": risk_result["factors_matched"],
                    "recommendations": risk_result["recommendations"]
                })

        return predictions

    async def get_student_risk_for_event(
        self,
        student_profile: Dict[str, Any],
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate detailed risk analysis for a specific student-event pair.

        Uses LLM for detailed strategy generation.
        """
        risk_result = self._calculate_risk(student_profile, event)

        # If significant risk, get detailed LLM recommendations
        if risk_result["risk_level"] in ["medium", "high"]:
            prompt = PREDICT_STUDENT_RISK_PROMPT.format(
                student_name=student_profile.get("name", "Unknown"),
                student_profile=format_student_profile(student_profile),
                event_title=event.get("title"),
                event_type=event.get("event_type"),
                sensory_factors=self._format_sensory_factors(event.get("sensory_factors"))
            )

            detailed_response = await self.call_llm(
                messages=[
                    {"role": "system", "content": PREDICT_AGENT_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                prompt_summary={
                    "action": "student_risk_detail",
                    "student": student_profile.get("name"),
                    "event": event.get("title")
                },
                temperature=0.7,
                max_tokens=500
            )

            risk_result["detailed_analysis"] = detailed_response

        return risk_result

    def _calculate_risk(
        self,
        student_profile: Dict[str, Any],
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate risk level for a specific student-event pair.

        Risk factors:
        - Student triggers matching event sensory_factors
        - Event type (drills and transitions are inherently higher risk)
        - Number of triggers matched

        Returns:
            Dict with risk_level, triggers_matched, factors_matched, recommendations
        """
        triggers = student_profile.get("triggers") or []
        sensory_factors = event.get("sensory_factors") or {}
        event_type = event.get("event_type", "")

        triggers_matched = []
        factors_matched = []

        # Check each sensory factor against student triggers
        for factor, is_present in sensory_factors.items():
            if not is_present:
                continue

            factor_keywords = self.SENSORY_FACTOR_KEYWORDS.get(factor, factor.replace("_", " ").split())

            for trigger in triggers:
                trigger_lower = trigger.lower()
                if any(kw in trigger_lower for kw in factor_keywords):
                    if trigger not in triggers_matched:
                        triggers_matched.append(trigger)
                    if factor not in factors_matched:
                        factors_matched.append(factor)

        # Calculate base risk from matches
        match_count = len(triggers_matched)
        if match_count == 0:
            base_risk = "none"
        elif match_count == 1:
            base_risk = "low"
        elif match_count == 2:
            base_risk = "medium"
        else:
            base_risk = "high"

        # Event type modifiers - drills and transitions are inherently risky
        high_risk_types = ["drill", "transition", "testing"]

        if base_risk == "none" and event_type in high_risk_types:
            # Check if student has any anxiety/sensory triggers
            anxiety_keywords = ["anxiety", "change", "unexpected", "routine", "sensory"]
            for trigger in triggers:
                if any(kw in trigger.lower() for kw in anxiety_keywords):
                    base_risk = "low"
                    triggers_matched.append(trigger)
                    factors_matched.append(f"event_type:{event_type}")
                    break
        elif base_risk == "low" and event_type in high_risk_types:
            base_risk = "medium"
        elif base_risk == "medium" and event_type in high_risk_types:
            base_risk = "high"

        # Generate basic recommendations
        recommendations = self._generate_recommendations(
            student_profile, event, triggers_matched, factors_matched
        )

        return {
            "risk_level": base_risk,
            "triggers_matched": triggers_matched,
            "factors_matched": factors_matched,
            "recommendations": recommendations
        }

    def _generate_recommendations(
        self,
        student: Dict[str, Any],
        event: Dict[str, Any],
        triggers_matched: List[str],
        factors_matched: List[str]
    ) -> List[str]:
        """Generate basic recommendations based on matched triggers and factors."""
        recommendations = []
        student_name = student.get("name", "the student")
        successful_methods = student.get("successful_methods") or []

        # Add timing recommendation
        start_time = event.get("start_time")
        if start_time:
            recommendations.append(f"Give {student_name} a 5-10 minute warning before {start_time}")

        # Factor-specific recommendations
        for factor in factors_matched:
            if "loud" in factor or "sound" in factor:
                recommendations.append(f"Offer noise-reducing headphones to {student_name}")
            if "crowd" in factor:
                recommendations.append(f"Position {student_name} near an exit or quieter area")
            if "unexpected" in factor or "transition" in factor:
                recommendations.append(f"Review what will happen with {student_name} beforehand")
            if "bright" in factor or "light" in factor:
                recommendations.append(f"Let {student_name} wear sunglasses or sit away from bright areas")

        # Include successful methods if relevant
        if successful_methods:
            method = successful_methods[0]
            recommendations.append(f"Consider using {method} (has worked before)")

        # Ensure at least one general recommendation
        if not recommendations:
            recommendations.append(f"Check in with {student_name} before and after the event")

        return recommendations[:4]  # Limit to 4 recommendations

    async def _analyze_event(
        self,
        event_id: Optional[str],
        teacher_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze a specific event for all students."""
        if not event_id:
            return {
                "response": "I need an event ID to analyze. Try asking about today's schedule instead.",
                "action_taken": "event_analysis_failed",
                "error": "no_event_id"
            }

        # Get the event and students
        events = await self.memory.get_upcoming_events(teacher_id, days_ahead=30)
        event = next((e for e in events if e.get("id") == event_id), None)

        if not event:
            return {
                "response": f"I couldn't find an event with ID {event_id}.",
                "action_taken": "event_analysis_failed",
                "error": "event_not_found"
            }

        students = await self.memory.list_students(limit=50)
        predictions = await self.analyze_event_risks(event, students)

        # Generate detailed analysis
        students_summary = self._format_students_for_prompt(students, predictions)
        prompt = PREDICT_EVENT_ANALYSIS_PROMPT.format(
            event_title=event.get("title"),
            event_type=event.get("event_type"),
            event_date=event.get("event_date"),
            event_time=event.get("start_time") or "Not specified",
            sensory_factors=self._format_sensory_factors(event.get("sensory_factors")),
            event_description=event.get("description") or "No description",
            students_summary=students_summary
        )

        response = await self.call_llm(
            messages=[
                {"role": "system", "content": PREDICT_AGENT_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            prompt_summary={
                "action": "event_analysis",
                "event": event.get("title"),
                "students_at_risk": len(predictions)
            },
            temperature=0.7,
            max_tokens=800
        )

        return {
            "response": response,
            "predictions": predictions,
            "action_taken": "event_analysis",
            "event": event
        }

    async def _analyze_student_risk(
        self,
        student_id: Optional[str],
        event_id: Optional[str],
        teacher_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze risk for a specific student and event."""
        if not student_id:
            return {
                "response": "I need to know which student to analyze.",
                "action_taken": "student_risk_failed",
                "error": "no_student_id"
            }

        student = await self.memory.get_student_profile(student_id)
        if not student:
            return {
                "response": f"I couldn't find a student with ID {student_id}.",
                "action_taken": "student_risk_failed",
                "error": "student_not_found"
            }

        # If no specific event, analyze today's events
        if event_id:
            events = await self.memory.get_upcoming_events(teacher_id, days_ahead=30)
            event = next((e for e in events if e.get("id") == event_id), None)
            if not event:
                return {
                    "response": "I couldn't find that event.",
                    "action_taken": "student_risk_failed",
                    "error": "event_not_found"
                }
            events_to_analyze = [event]
        else:
            events_to_analyze = await self.memory.get_todays_events(teacher_id)

        if not events_to_analyze:
            return {
                "response": f"No events scheduled to analyze for {student.get('name')}.",
                "action_taken": "student_risk",
                "predictions": []
            }

        # Analyze each event
        predictions = []
        for event in events_to_analyze:
            risk_result = await self.get_student_risk_for_event(student, event)
            if risk_result["risk_level"] != "none":
                predictions.append({
                    "event_title": event.get("title"),
                    "event_time": event.get("start_time"),
                    **risk_result
                })

        # Format response
        if predictions:
            risk_summary = "\n".join([
                f"- {p['event_title']}: {p['risk_level']} risk"
                for p in predictions
            ])
            response = f"Risk analysis for {student.get('name')}:\n{risk_summary}"
            if predictions[0].get("detailed_analysis"):
                response = predictions[0]["detailed_analysis"]
        else:
            response = f"No significant risks identified for {student.get('name')} with today's events."

        return {
            "response": response,
            "predictions": predictions,
            "action_taken": "student_risk",
            "student_name": student.get("name")
        }

    def _format_events_for_prompt(self, events: List[Dict[str, Any]]) -> str:
        """Format events list for inclusion in prompts."""
        if not events:
            return "No events scheduled"

        lines = []
        for event in events:
            time_str = event.get("start_time") or "Time TBD"
            factors = event.get("sensory_factors") or {}
            active_factors = [k for k, v in factors.items() if v]
            factors_str = f" [{', '.join(active_factors)}]" if active_factors else ""

            lines.append(
                f"- {time_str}: {event.get('title')} ({event.get('event_type')}){factors_str}"
            )

        return "\n".join(lines)

    def _format_at_risk_students(self, predictions: List[Dict[str, Any]]) -> str:
        """Format at-risk student predictions for prompts."""
        if not predictions:
            return "No students identified as at-risk for today's events."

        lines = []
        for pred in predictions:
            triggers = ", ".join(pred.get("triggers_matched", []))
            lines.append(
                f"- {pred.get('student_name')} ({pred.get('risk_level')} risk for {pred.get('event_title')}): "
                f"Triggers: {triggers}"
            )

        return "\n".join(lines)

    def _format_students_for_prompt(
        self,
        students: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]]
    ) -> str:
        """Format students with their risk info for prompts."""
        if not students:
            return "No students in database"

        # Create a map of student_id -> prediction
        pred_map = {p.get("student_id"): p for p in predictions}

        lines = []
        for student in students:
            sid = student.get("id") or student.get("student_id")
            name = student.get("name", "Unknown")
            triggers = student.get("triggers") or []

            pred = pred_map.get(sid)
            if pred:
                risk = pred.get("risk_level", "unknown")
                lines.append(f"- {name} [{risk} RISK]: Triggers: {', '.join(triggers)}")
            elif triggers:
                lines.append(f"- {name}: Triggers: {', '.join(triggers)}")

        return "\n".join(lines) if lines else "No relevant student triggers found"

    def _format_sensory_factors(self, factors: Optional[Dict[str, bool]]) -> str:
        """Format sensory factors dict into readable string."""
        if not factors:
            return "None specified"

        active = [k.replace("_", " ") for k, v in factors.items() if v]
        return ", ".join(active) if active else "None specified"
