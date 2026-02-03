"""
GET /api/agent_info endpoint.
Returns agent meta + how to use it.
"""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()


# Module names must match step_tracker.VALID_MODULES
VALID_MODULES = ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT", "ADMIN_AGENT", "PREDICT_AGENT"]


@router.get("/agent_info")
async def get_agent_info() -> Dict[str, Any]:
    """
    Returns agent meta + how to use it.

    Must include:
    - description
    - purpose
    - prompt_template (suggested way to work with the agent)
    - prompt_examples and full responses

    Returns:
        Dict matching the required Course Project schema
    """
    return {
        "description": (
            "The Proactive Co-Teacher is a multi-agent AI assistant designed to support "
            "special education teachers. It uses a central Orchestrator that coordinates "
            "four specialized agents: STUDENT_AGENT (student profiles and triggers), "
            "RAG_AGENT (evidence-based teaching strategies via vector search), "
            "ADMIN_AGENT (IEP reports, parent communications, summaries), and "
            "PREDICT_AGENT (daily briefings and risk predictions). The system uses "
            "rule-based routing to minimize LLM costs, falling back to LLM routing "
            "only when needed."
        ),
        "purpose": (
            "To reduce administrative burden on special education teachers by providing "
            "proactive, personalized support. The agent retrieves student profiles, "
            "recommends teaching strategies that exclude previously failed methods, "
            "generates administrative documents (IEPs, parent emails), and predicts "
            "potential issues based on upcoming events and student triggers."
        ),
        "prompt_template": {
            "template": (
                "[QUERY_TYPE] [STUDENT_NAME (optional)]: [DETAILS]\n\n"
                "Query types:\n"
                "- Student info: 'Tell me about [name]', 'What are [name]'s triggers?'\n"
                "- Strategies: 'What strategies work for [condition/situation]?'\n"
                "- Personalized help: '[name] is [situation]. What should I do?'\n"
                "- Admin tasks: 'Draft an IEP report for [name]', 'Write email to parents'\n"
                "- Predictions: 'What should I watch for today?', 'Daily briefing'"
            )
        },
        "prompt_examples": [
            {
                "prompt": "Alex is getting frustrated during math. What strategies should I try?",
                "full_response": (
                    "Based on Alex's profile, he responds well to visual supports and needs "
                    "frequent breaks. Here are recommended strategies:\n\n"
                    "1. **Visual Math Manipulatives** - Use physical counters or digital visualizations\n"
                    "2. **Chunking** - Break problems into smaller steps with visual checklists\n"
                    "3. **Movement Breaks** - Incorporate 2-minute movement breaks every 10 minutes\n\n"
                    "Note: Avoid group work without support, as this has been unsuccessful for Alex in the past."
                ),
                "steps": [
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {
                            "action": "route_query",
                            "query": "Alex is getting frustrated during math. What strategies should I try?",
                            "context": {"session_id": "example-session"}
                        },
                        "response": {
                            "routed_to": ["STUDENT_AGENT", "RAG_AGENT"],
                            "is_multi_agent": True,
                            "confidence": 0.92,
                            "extracted_entities": {"name": "Alex"}
                        }
                    },
                    {
                        "module": "STUDENT_AGENT",
                        "prompt": {
                            "action": "get_student_context",
                            "student_name": "Alex"
                        },
                        "response": {
                            "found": True,
                            "student_id": "STU001",
                            "name": "Alex",
                            "triggers": ["frustration", "sudden transitions", "loud noises"],
                            "successful_methods": ["visual supports", "movement breaks", "one-on-one attention"],
                            "failed_methods": ["group work without support", "timed tests"],
                            "learning_style": "visual"
                        }
                    },
                    {
                        "module": "RAG_AGENT",
                        "prompt": {
                            "action": "search_teaching_methods",
                            "query": "strategies for math frustration",
                            "context": {
                                "disability_type": "autism",
                                "exclude_methods": ["group work without support", "timed tests"]
                            }
                        },
                        "response": {
                            "methods_found": 3,
                            "methods": [
                                {"name": "Visual Math Manipulatives", "relevance": 0.94},
                                {"name": "Chunking", "relevance": 0.89},
                                {"name": "Movement Breaks", "relevance": 0.85}
                            ],
                            "from_cache": False
                        }
                    },
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {
                            "action": "combine_responses",
                            "student_context": "Alex profile retrieved",
                            "rag_results": "3 methods found"
                        },
                        "response": {
                            "action": "synthesize_personalized_response",
                            "agents_used": ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT"]
                        }
                    }
                ]
            },
            {
                "prompt": "Draft a progress report for Jordan's IEP meeting",
                "full_response": (
                    "**IEP Progress Report**\n\n"
                    "Student: Jordan Smith\n"
                    "Report Date: February 3, 2026\n"
                    "Reporting Period: Fall Semester 2025\n\n"
                    "**Goal 1: Attention & Focus**\n"
                    "Objective: Jordan will maintain on-task behavior for 15-minute intervals "
                    "with no more than 2 prompts, in 4 out of 5 trials.\n"
                    "Progress: Jordan has shown 40% improvement, now averaging 12 minutes of "
                    "sustained focus with 1-2 prompts. Meeting benchmark trajectory.\n\n"
                    "**Goal 2: Social Interaction**\n"
                    "Objective: Jordan will initiate peer interactions 3 times per day.\n"
                    "Progress: Currently averaging 2 initiations per day. Continuing to work "
                    "toward goal with social stories support.\n\n"
                    "**Recommendations:**\n"
                    "- Continue movement breaks between activities\n"
                    "- Implement timer-based task completion\n"
                    "- Consider fidget tools for longer activities\n"
                    "- Increase peer buddy program to 2x daily"
                ),
                "steps": [
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {
                            "action": "route_query",
                            "query": "Draft a progress report for Jordan's IEP meeting"
                        },
                        "response": {
                            "routed_to": ["ADMIN_AGENT"],
                            "is_multi_agent": False,
                            "confidence": 0.95,
                            "document_type": "iep"
                        }
                    },
                    {
                        "module": "STUDENT_AGENT",
                        "prompt": {
                            "action": "get_student_context",
                            "student_name": "Jordan"
                        },
                        "response": {
                            "found": True,
                            "student_id": "STU002",
                            "name": "Jordan Smith",
                            "iep_goals": ["attention_focus", "social_interaction"],
                            "accommodations": ["movement breaks", "visual schedules"]
                        }
                    },
                    {
                        "module": "ADMIN_AGENT",
                        "prompt": {
                            "action": "generate_document",
                            "document_type": "iep_progress_report",
                            "student": "Jordan Smith",
                            "student_context": {"goals": ["attention_focus", "social_interaction"]}
                        },
                        "response": {
                            "document_generated": True,
                            "document_type": "iep_progress_report",
                            "sections": ["header", "goal_progress", "recommendations"]
                        }
                    }
                ]
            },
            {
                "prompt": "What strategies work for students with sensory processing issues?",
                "full_response": (
                    "For students with sensory processing issues, consider these evidence-based strategies:\n\n"
                    "1. **Sensory Breaks** - Schedule regular sensory breaks throughout the day "
                    "(every 30-45 minutes for most students)\n\n"
                    "2. **Environmental Modifications**\n"
                    "   - Reduce fluorescent lighting (use natural light or lamps)\n"
                    "   - Offer quiet spaces or noise-reducing areas\n"
                    "   - Minimize visual clutter on walls and desks\n\n"
                    "3. **Weighted Items** - Provide weighted lap pads, vests, or blankets for calming "
                    "proprioceptive input\n\n"
                    "4. **Noise-Canceling Headphones** - Reduce auditory overload during independent "
                    "work or transitions\n\n"
                    "5. **Sensory Diet** - Work with OT to create individualized sensory activities "
                    "scheduled throughout the day\n\n"
                    "6. **Fidget Tools** - Offer appropriate fidgets that don't distract others "
                    "(stress balls, textured strips)\n\n"
                    "Always collaborate with the occupational therapist for student-specific recommendations."
                ),
                "steps": [
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {
                            "action": "route_query",
                            "query": "What strategies work for students with sensory processing issues?"
                        },
                        "response": {
                            "routed_to": ["RAG_AGENT"],
                            "is_multi_agent": False,
                            "confidence": 0.88,
                            "query_type": "general_strategy"
                        }
                    },
                    {
                        "module": "RAG_AGENT",
                        "prompt": {
                            "action": "search_teaching_methods",
                            "query": "sensory processing strategies",
                            "filters": {"disability_type": "sensory_processing"}
                        },
                        "response": {
                            "methods_found": 6,
                            "methods": [
                                {"name": "Sensory Breaks", "relevance": 0.96},
                                {"name": "Environmental Modifications", "relevance": 0.94},
                                {"name": "Weighted Items", "relevance": 0.91},
                                {"name": "Noise-Canceling Headphones", "relevance": 0.89},
                                {"name": "Sensory Diet", "relevance": 0.87},
                                {"name": "Fidget Tools", "relevance": 0.85}
                            ],
                            "from_cache": False
                        }
                    }
                ]
            },
            {
                "prompt": "What should I watch for today? Any students at risk?",
                "full_response": (
                    "**Daily Briefing - February 3, 2026**\n\n"
                    "**High Priority Alerts:**\n\n"
                    "1. **Alex** - Fire drill scheduled at 10:30 AM\n"
                    "   - Risk: Loud noises are a known trigger\n"
                    "   - Suggestion: Give 10-minute warning, provide noise-canceling headphones, "
                    "assign a buddy\n\n"
                    "2. **Maya** - Substitute teacher in afternoon\n"
                    "   - Risk: Change in routine may cause anxiety\n"
                    "   - Suggestion: Review visual schedule with her, prepare social story about "
                    "substitute teachers\n\n"
                    "**Moderate Alerts:**\n\n"
                    "3. **Jordan** - Assembly after lunch (change in schedule)\n"
                    "   - Monitor for signs of overstimulation\n"
                    "   - Have quiet space available if needed\n\n"
                    "**General Notes:**\n"
                    "- Weather: Rain expected, indoor recess likely\n"
                    "- Prepare alternative movement activities for students who need physical outlets"
                ),
                "steps": [
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {
                            "action": "route_query",
                            "query": "What should I watch for today? Any students at risk?"
                        },
                        "response": {
                            "routed_to": ["PREDICT_AGENT"],
                            "is_multi_agent": False,
                            "confidence": 0.93,
                            "query_type": "daily_briefing"
                        }
                    },
                    {
                        "module": "PREDICT_AGENT",
                        "prompt": {
                            "action": "generate_daily_briefing",
                            "date": "2026-02-03",
                            "include": ["schedule_events", "weather", "student_risks"]
                        },
                        "response": {
                            "briefing_generated": True,
                            "high_priority_alerts": 2,
                            "moderate_alerts": 1,
                            "students_flagged": ["Alex", "Maya", "Jordan"],
                            "events_analyzed": ["fire_drill", "substitute_teacher", "assembly"]
                        }
                    }
                ]
            },
            {
                "prompt": "Update: movement breaks are really helping Alex focus better",
                "full_response": (
                    "Great observation! I've updated Alex's profile:\n\n"
                    "**Update Applied:**\n"
                    "- Added 'movement breaks' to Alex's successful methods\n\n"
                    "This will be factored into future strategy recommendations for Alex. "
                    "The system will now prioritize suggesting movement breaks and similar "
                    "kinesthetic approaches when Alex is struggling.\n\n"
                    "Would you like me to suggest a specific movement break schedule for different activities?"
                ),
                "steps": [
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {
                            "action": "route_query",
                            "query": "Update: movement breaks are really helping Alex focus better"
                        },
                        "response": {
                            "routed_to": ["STUDENT_AGENT"],
                            "is_multi_agent": False,
                            "confidence": 0.91,
                            "detected_intent": "profile_update"
                        }
                    },
                    {
                        "module": "STUDENT_AGENT",
                        "prompt": {
                            "action": "update_student_profile",
                            "student_name": "Alex",
                            "update_type": "add_successful_method",
                            "method": "movement breaks"
                        },
                        "response": {
                            "update_applied": True,
                            "student_id": "STU001",
                            "field_updated": "successful_methods",
                            "new_value": ["visual supports", "movement breaks", "one-on-one attention"]
                        }
                    }
                ]
            }
        ]
    }
