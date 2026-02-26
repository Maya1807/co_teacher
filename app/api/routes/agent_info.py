"""
GET /api/agent_info endpoint.
Returns agent meta + how to use it.
"""
from fastapi import APIRouter
from typing import Dict, Any

from app.utils.prompts import (
    PLANNER_SYSTEM,
    PLANNER_USER_PROMPT,
    STUDENT_AGENT_SYSTEM,
    STUDENT_AGENT_UPDATE_EXTRACT_PROMPT,
    RAG_AGENT_SYSTEM,
    RAG_AGENT_SEARCH_PROMPT,
    RAG_AGENT_NO_CONTEXT_PROMPT,
    ADMIN_AGENT_SYSTEM,
    ADMIN_AGENT_IEP_PROMPT,
    PREDICT_AGENT_SYSTEM,
    PREDICT_DAILY_BRIEFING_PROMPT,
    FINAL_PRESENTATION_PROMPT,
    format_student_profile,
)

router = APIRouter()


# Module names must match step_tracker.VALID_MODULES
VALID_MODULES = ["ORCHESTRATOR", "PLANNER", "PLAN_EXECUTOR", "PRESENTER", "STUDENT_AGENT", "RAG_AGENT", "ADMIN_AGENT", "PREDICT_AGENT"]

# Sample data used to build full prompt messages in examples
ALEX_PROFILE = {
    "name": "Alex Johnson",
    "grade": "4",
    "disability_type": "autism",
    "learning_style": "visual",
    "triggers": [
        "loud noises",
        "schedule changes",
        "fire drills",
        "unexpected transitions",
        "crowded hallways",
    ],
    "successful_methods": [
        "visual schedules",
        "fidget tools",
        "social stories",
        "advance warnings",
        "quiet corner access",
        "clear written instructions",
    ],
    "failed_methods": [
        "group work without support",
        "verbal-only instructions",
        "sudden changes to routine",
    ],
}

JORDAN_PROFILE = {
    "name": "Jordan Smith",
    "grade": "3",
    "disability_type": "ADHD",
    "learning_style": "kinesthetic",
    "triggers": [
        "long sitting periods",
        "transitions between activities",
        "waiting for turn",
        "boring or repetitive tasks",
    ],
    "successful_methods": [
        "movement breaks every 15 minutes",
        "hands-on activities",
        "chunked tasks with clear endpoints",
        "visual timers",
        "standing desk option",
        "fidget tools",
    ],
    "failed_methods": [
        "long lectures",
        "worksheets without breaks",
        "extended sitting",
        "tasks without clear structure",
    ],
}

ALEX_PROFILE_TEXT = format_student_profile(ALEX_PROFILE)
JORDAN_PROFILE_TEXT = format_student_profile(JORDAN_PROFILE)

RAG_METHODS_EMPTY = "No methods retrieved"
RAG_METHODS_SAMPLE = (
    "1. Calm Corner Reset\n"
    "   Category: de-escalation\n"
    "   Description: A brief, structured cool-down space with a timer and calming tools.\n\n"
    "2. Choice + Countdown\n"
    "   Category: behavior support\n"
    "   Description: Offer two concrete options with a short countdown to reduce escalation.\n\n"
    "3. Visual Coping Cue Cards\n"
    "   Category: self-regulation\n"
    "   Description: Simple visual prompts for breathing and break requests."
)

PREDICT_EVENTS_SAMPLE = (
    "- Science Class (10:15) — group work and hands-on activity\n"
    "- Art Class (13:00) — mixed media and peer feedback\n"
    "- PE Class (14:15) — loud environment, transitions"
)

PREDICT_AT_RISK_SAMPLE = (
    "- Riley Martinez: peer conflict risk during group work\n"
    "- Jordan Smith: transitions + prolonged sitting\n"
    "- Taylor Williams: anxiety with read-aloud and new vocabulary"
)

JORDAN_STUDENT_INFO = (
    f"{JORDAN_PROFILE_TEXT}\n"
    "Notes: Grade not provided in file; please update student record."
)

JORDAN_OBSERVATIONS = (
    "Weekly interval recordings show on-task average ~72%. "
    "Work completion ~82% and accuracy ~78% in recent samples."
)

# Actual API responses captured from live deployment
PROMPT_EXAMPLES = [
    {
        'prompt': "What are Alex's sensory triggers and how should I prepare him for the fire drill today?",
        'full_response': 'That sounds like it could be overwhelming for Alex; here’s a short, practical plan to reduce his stress during today’s drill.\n\n- Before: place a one‑page visual schedule/First–Then card and a very short (1–3 sentence) social story at his desk; have his preferred fidget and ear defenders within reach or pre‑fit them, choose a less‑crowded exit route to a quiet spot, and give a calm 10‑minute and 1‑minute reminder using the same script (for example: “In 10 minutes we will practice a fire drill; the alarm will be loud; you can wear your headphones and use your fidget; I will stay with you.”).\n- During: keep language minimal, offer two concrete choices (headphones or the quiet spot), keep Alex on the quieter side of the line, and use a 1‑minute “countdown + put‑on” routine to hand him headphones right before the alarm.\n- After: do a brief 1–2 minute praise/debrief and allow a short quiet break or token reward.\n\nI can prepare a laminated visual card and the 3‑sentence social story for you to print—would you like me to leave them at his desk or email the files?',
        'steps': [
            {
                'module': 'PLANNER',
                'prompt': {
                    'action': 'create_plan',
                    'query_snippet': "What are Alex's sensory triggers and how should I prepare him for the fire drill today?",
                    'messages': [
                        {
                            'role': 'system',
                            'content': PLANNER_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': PLANNER_USER_PROMPT.format(
                                query="What are Alex's sensory triggers and how should I prepare him for the fire drill today?"
                            )
                        }
                    ]
                },
                'response': {
                    'content': '{\n  "student_name": "Alex",\n  "steps": [\n    {\n      "step_index": 0,\n      "agent": "STUDENT_AGENT",\n      "task": "Retrieve Alex\'s stored student profile. Return the following fields and any recent updates: name, grade, disability_type, learning_style, triggers (sensory or other), successful_methods, failed_methods, notes, and any documented responses to previous fire drills or loud auditory events.",\n      "depends_on": []\n    },\n    {\n      "step_index": 1,\n      "agent": "RAG_AGENT",\n      "task": "Using the profile data returned for Alex in step 0, generate evidence-based, practical guidance focused on sensory triggers and preparing him for today\'s fire drill. Provide: (a) a concise list of Alex\'s likely sensory triggers (auditory, visual, tactile, olfactory, movement) inferred from his profile fields; (b) a step-by-step, time-lined plan for today with clear before/during/after actions (including exact short pre-notification script to tell Alex, a short social-story/script text he can be read, and estimated timing for each step); (c) specific sensory accommodations and materials to prepare now (e.g., ear defenders, sunglasses, fidget item, quiet space) and where/how to position them; (d) staff roles and brief scripts for staff to use if Alex becomes distressed (including de-escalation steps and a contingency plan if he refuses or has a meltdown); and (e) observable signs to watch that indicate readiness or increasing distress. Tailor all recommendations to Alex\'s documented successful_methods and triggers, and cite evidence-based rationale in brief for each major recommendation so the teacher understands why it will help today.",\n      "depends_on": [\n        0\n      ]\n    }\n  ]\n}',
                    'tokens': {
                        'prompt': 689,
                        'completion': 959,
                        'total': 1648
                    },
                    'cost': 0.0006787499999999999
                }
            },
            {
                'module': 'STUDENT_AGENT',
                'prompt': {
                    'action': 'extract_update_info',
                    'student': 'Alex Johnson',
                    'query_snippet': "What are Alex's sensory triggers and how should I prepare him for the fire drill today?",
                    'messages': [
                        {
                            'role': 'user',
                            'content': STUDENT_AGENT_UPDATE_EXTRACT_PROMPT.format(
                                profile=ALEX_PROFILE_TEXT,
                                query="What are Alex's sensory triggers and how should I prepare him for the fire drill today?"
                            )
                        }
                    ]
                },
                'response': {
                    'content': '{\n  "is_update": false,\n  "already_exists": [\n    "loud noises",\n    "schedule changes",\n    "fire drills",\n    "unexpected transitions",\n    "crowded hallways",\n    "visual schedules",\n    "advance warnings",\n    "quiet corner access",\n    "clear written instructions"\n  ],\n  "reason": "Teacher asked a question about Alex\'s triggers and how to prepare for a fire drill but did not provide any new observations or instructions to change the profile.",\n  "updates": {\n    "add_triggers": null,\n    "remove_triggers": null,\n    "add_successful_methods": null,\n    "remove_successful_methods": null,\n    "add_failed_methods": null,\n    "remove_failed_methods": null,\n    "notes": null\n  }\n}',
                    'tokens': {
                        'prompt': 526,
                        'completion': 1071,
                        'total': 1597
                    },
                    'cost': 0.0007214999999999999
                }
            },
            {
                'module': 'RAG_AGENT',
                'prompt': {
                    'action': 'contextual_search',
                    'student': 'Alex Johnson',
                    'query_snippet': 'Using the profile data returned for Alex in step 0, generate evidence-based, practical guidance focu',
                    'disability_type': 'autism',
                    'methods_found': 0,
                    'messages': [
                        {
                            'role': 'system',
                            'content': RAG_AGENT_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': RAG_AGENT_SEARCH_PROMPT.format(
                                query="What are Alex's sensory triggers and how should I prepare him for the fire drill today?",
                                student_name="Alex Johnson",
                                disability_type=ALEX_PROFILE["disability_type"],
                                learning_style=ALEX_PROFILE["learning_style"],
                                successful_methods=", ".join(ALEX_PROFILE["successful_methods"]),
                                failed_methods=", ".join(ALEX_PROFILE["failed_methods"]),
                                retrieved_methods=RAG_METHODS_EMPTY,
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'Context summary (short)\n- Alex Johnson: student with autism; strong visual learner. Documented triggers: loud noises (alarms), schedule changes, fire drills, unexpected transitions, crowded hallways. What helps: visual schedules, social stories, fidget tools, advance warnings, quiet corner access, clear written instructions. Avoid verbal-only instructions, unsupported group work, and sudden routine changes.\n\n(a) Alex’s likely sensory triggers (inferred)\n- Auditory: loud alarms, sirens, shouting, crowded hallway noise. (Primary)\n- Visual: flashing alarm lights, many moving people, bright lights, smoke or emergency signage.\n- Tactile: being jostled in crowded hallways, accidental bumps, touch from staff if guiding.\n- Movement/proprioceptive: quick pulls/pushes, sudden changes in walking pace, stair navigation during drill.\n- Olfactory: smoke alarm odor or any strong/sudden smells (less likely but possible).\n\n(b) Step-by-step, time-lined plan for TODAY (exact scripts + timings)\nOverview: total window ≈ 35–45 minutes around the drill. Adjust times to when your school schedules the drill.\n\nBefore (30 → 0 minutes before drill)\n- 30 minutes before: Prep materials & staff roles (see section c & d). (5–10 min)\n- 20 minutes before: Visual priming at Alex’s desk (2 min)\n  - Show a one-page visual schedule card: “Class → Practice math → Fire drill at 10:30 → Return to class.”\n  - Give Alex his fidget tool and place ear defenders beside him.\n- 10 minutes before: Short pre-notification to Alex (30–45 sec)\n  - Script to say calmly, with card: “Alex, in 10 minutes we will practice leaving the room for a fire drill. The alarm will be loud. You can wear your headphones and use your fidget. I will stay with you. We will be back in about 10 minutes.” (Point to visual card for each phrase.)\n- 5 minutes before: Read the social story (30–60 sec) and show a 1–2 step “first–then” card.\n  - Social story (short, to be read aloud): “Today we will practice a fire drill. When the alarm rings, we will walk outside quietly with our class. The alarm will be loud and that is okay. You can wear your noise protectors and hold your fidget. I will be with you the whole time. After the drill, we will go back to class and have a break.”\n  - Show a visual “First: Fire drill (loud alarm) → Then: Quiet corner/Choice” card.\n- 1 minute before: Put on his ear defenders (or hand the headphones) and give a 1-line reminder: “Now—alarm soon. Hold your fidget. Walk with me.”\n\nDuring (drill moment; assume drill lasts 2–5 minutes)\n- Alarm starts (0–5 min)\n  - Primary staff action (teacher): Move to Alex’s side, say calmly (10–15 sec): “Alarm is loud. Walk with me. We will go to the lineup spot.” Show the “exit” visual card and model calm breathing.\n  - If hallway will be crowded: choose a less crowded route if possible. Keep Alex near an adult on the quieter wall side.\n  - If Alex becomes distressed but can walk: offer options: “We can put on headphones, or go to the quiet spot.” Point to those visuals and let him choose.\n  - If Alex freezes/refuses to move: use the de-escalation script (see section d). If actual evacuation is mandated and he still refuses, use the contingency (see d) to safely remove him—no physical restraint unless staff are trained and school protocol directs otherwise.\n- Immediately after drill (0–5 min)\n  - Teacher leads Alex back to classroom or to pre-planned quiet spot if he needs a break. Offer a short tangible/visual “after” reward (sticker, token, 2 minutes quiet time).\n\nAfter (post-drill; 5–20 minutes after)\n- 5 minutes after: Short debrief at desk (1–2 min)\n  - Script: “You did the fire drill. The alarm was loud. You stayed safe and calm. Now you can have (fidget/quiet corner/5-minute preferred activity).”\n  - Mark the event on his visual schedule (check or move icon).\n- 10–20 minutes after: Return to normal routine; if residual anxiety, allow extended quiet time (5–10 min) in the quiet corner before resuming class.\n\nEstimated overall timeline: prepare 10–20 min before; 1 min pre-notification, 30–60 sec social story; 0–5 min drill; 5–20 min recovery.\n\n(c) Sensory accommodations and materials to prepare now (what, where, how to position)\n- Ear protection (option A: foam ear defenders or noise-reducing headphones)\n  - Where/how: Place on desk in reach, pre-fit so staff can hand it to Alex quickly. If he tolerates wearing them ahead of time, put them on 1 minute before alarm.\n  - Rationale: reduces alarm peak decibel (evidence: sound attenuation reduces physiological arousal in children with sensory sensitivity).\n- Sunglasses or visor (if flashing lights are strong)\n  - Where/how: in a labeled pouch on his desk; staff can offer them quickly.\n- Fidget tool (known preferred item)\n  - Where/how: in his pocket or on top of desk; offer it continuously through transition to aid self-regulation.\n- Quiet spot / retreat\n  - Where/how: pre-designated low-stimulation corner in classroom or adjacent room with clear route. Position it on the side of the room away from hallway and loud traffic. Place a soft visual cue (small sign with his name) so staff and Alex know where to go.\n- Visual cues/cards\n  - One-page social story printed and laminated; “First-Then” card; “Exit” and “Return” picture cards. Keep in a visible folder on his desk.\n- Physical routing\n  - Plan a less-crowded exit route and share with hall monitor/security. Station a familiar staff member at the quieter side of the hallway to lead Alex’s group if possible.\n- Optional: small neutral-scent cloth or breathing cue (only if Alex tolerates). Avoid unfamiliar strong smells.\nFlag: If any materials are novel (new headphones, sunglasses), introduce them now quickly so they aren’t surprising during the drill.\n\n(d) Staff roles and brief scripts + de-escalation & contingency\nRoles (minimum)\n- Primary teacher (PT): supports Alex, communicates scripts, carries visual cards and fidget.\n- Secondary staff / aide (SS): positions at doorway/hallway to guide less-crowded route and monitor crowding.\n- Quiet-space attendant (QA): prepares quiet spot; ready to receive Alex if he needs to exit class early.\n- Safety lead (SL): communicates with office about drill timing and ensures alarm volume/route is as planned.\n\nBrief scripts (short, calm, same wording each time)\n- 10-minute pre-notify (PT): “Alex, in 10 minutes we will practice a fire drill. The alarm will be loud. You can wear your headphones and use your fidget. I will stay with you.”\n- 1-minute reminder (PT): “Now—alarm soon. Put on your headphones and hold your fidget.”\n- At alarm start (PT): “The alarm is loud. Walk with me. We will go to our safe spot.” (show exit card)\n- If Alex becomes upset (SS or PT): “I see you are upset. The alarm is loud. You can put on your headphones or come to the quiet corner with me. Which would you like?” (offer two concrete choices)\n- After calmer (PT): “You did it. Thank you. Now you can have [preferred calm activity].”\n\nDe-escalation steps (simple, evidence-based)\n1. Reduce sensory input: give headphones and fidget; move to quieter route/spot. (Immediate)\n2. Offer clear, concrete choices (two options) to increase sense of control. Keep language short.\n3. Use visual supports and gestures rather than extra verbal talk.\n4. If vocal distress escalates, give space: move to the quiet spot and remain calm; use slow tone and brief reassurance. Use a known calming routine (deep breaths counted with visuals).\n5. If physical agitation risks safety (running into hall), staff should gently guide by the forearm to the quiet spot—only trained staff should use physical guidance per school policy.\n\nContingency if he refuses or has a meltdown\n- If Alex refuses to leave classroom but alarm requires evacuation:\n  - Offer a very concrete visual choice: “Come now and wear the headphones” or “Stay with me in the doorway with headphones.” Offer the physical presence of a trusted staff beside him. Use minimal language.\n  - If still refusing and immediate evacuation required, one staff with pre-existing rapport (and training) calmly escorts him by guiding hand-to-hand to safe exit—do not use force. Notify safety lead. Prioritize safety of all students.\n- If meltdown occurs outside (crowded): immediately move him to pre-arranged quiet spot off the main flow (QA takes him). Provide minimal stimulation, allow recovery time, delay debrief until calm.\n- If meltdown involves self-injury or aggressive behavior: follow school crisis plan, remove others, call for trained behavior support and health staff.\n\n(e) Observable signs (readiness vs increasing distress)\nReady / regulated signs\n- Following the visual schedule or pointing to the “First-Then” card\n- Calm or steady breathing, hands relaxed around fidget\n- Making eye contact or following teacher prompts\n- Walking with staff without hesitation\n- Using words/gestures to choose an option\n\nEarly signs of increasing distress\n- Repeatedly covering ears or tensing shoulders\n- Increased pace of movements, pacing, or rigidity\n- Facial signs: tensed jaw, furrowed brow, wide eyes\n- Increased vocalizations (whining, short cries), staring/freezing\n- Refusal language: “No,” turning away, pushing away materials\n\nEscalation signs (intervene ASAP)\n- Hiding head, immediate panic behaviors, running or aggressive movements\n- Attempts to bolt into crowded areas or block exits\n- Crying that does not settle with headphones/fidget\n- Self-injurious behavior\n\nEvidence-based rationale (brief for major recommendations)\n- Social Stories (Carol Gray): helps set expectations and reduce uncertainty by describing step-by-step what will happen and appropriate responses—effective for preparing autistic students for novel or stressful events.\n- Visual schedules/First-Then boards: increase predictability and reduce anxiety by showing sequence; align with Alex’s visual learning preference.\n- Noise reduction (ear defenders/headphones): attenuating sound reduces sympathetic arousal and behavioral meltdown likelihood in students sensitive to auditory stimuli.\n- Fidget tools and quiet retreat: provide sensory regulation and a safe low-stimulation environment to restore regulation; sensory regulation supports self-calming.\n- Priming/advance notice: research shows priming before transitions reduces behavioral outbursts in students with autism because it reduces surprise and gives time to prepare.\n\n2–3 strategies tailored to Alex (structured as requested)\n1) Method name: Visual Schedule + First–Then Board\n- What it is and why it works: A simple, pictured sequence showing “what will happen” and “what comes next.” It reduces uncertainty and gives small, concrete steps. Works because Alex is a visual learner and responds well to predictable routine.\n- How to implement: Put a one-page card on his desk showing the drill time and the after-break. Use a velcro token to move from “First: Fire drill” to “Then: Quiet corner.” Review 10 and 1 minute before.\n- Best for: Alex when he needs predictability and short prompts before transitions.\n\n2) Method name: Social Story (short, scripted)\n- What it is and why it works: Short story explaining the drill in first-person, describing sensory aspects and expected behavior. It sets cognitive expectation and models calm responses.\n- How to implement: Read the 3–5 sentence social story aloud 5–10 minutes before drill and keep laminated copy available to show during the event.\n- Best for: Alex to reduce fear of the unknown and clarify steps.\n\n3) Method name: Sensory Modulation (ear defenders + fidget + quiet spot)\n- What it is and why it works: Use of sensory tools and a low-stimulus area to reduce overload; fidgets help channel sensory need. Reduces physiological arousal and supports regulation.\n- How to implement: Place ear defenders on desk, fidget in hand, and map route to quiet spot; offer choices during alarm.\n- Best for: Alex during high-noise events like the fire drill.\n\nOne practical tip to try today (quick, high-impact)\n- 1-minute “countdown + put-on” routine: One minute before the drill, hand Alex his headphones and say: “One minute—put on your headphones now. Hold your fidget. Walk with me.” Practice this once now so it’s familiar. The combination of brief countdown, immediate sensory control, and a tactile item often prevents escalation.\n\nIf you want, I can produce a single laminated one-page visual card and the 3-sentence social story formatted for printing.',
                    'tokens': {
                        'prompt': 714,
                        'completion': 4083,
                        'total': 4797
                    },
                    'cost': 0.0025569
                }
            },
            {
                'module': 'PRESENTER',
                'prompt': {
                    'action': 'present_response',
                    'query_snippet': "What are Alex's sensory triggers and how should I ",
                    'original_length': 1154,
                    'messages': [
                        {
                            'role': 'user',
                            'content': FINAL_PRESENTATION_PROMPT.format(
                                query="What are Alex's sensory triggers and how should I prepare him for the fire drill today?",
                                agent_response=(
                                    "Context summary (short)\n"
                                    "- Alex Johnson: student with autism; strong visual learner. Documented triggers: loud noises (alarms), schedule changes, fire drills, unexpected transitions, crowded hallways. "
                                    "What helps: visual schedules, social stories, fidget tools, advance warnings, quiet corner access, clear written instructions. "
                                    "Avoid verbal-only instructions, unsupported group work, and sudden routine changes."
                                )
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'That sounds like it could be overwhelming for Alex; here’s a short, practical plan to reduce his stress during today’s drill.\n\n- Before: place a one‑page visual schedule/First–Then card and a very short (1–3 sentence) social story at his desk; have his preferred fidget and ear defenders within reach or pre‑fit them, choose a less‑crowded exit route to a quiet spot, and give a calm 10‑minute and 1‑minute reminder using the same script (for example: “In 10 minutes we will practice a fire drill; the alarm will be loud; you can wear your headphones and use your fidget; I will stay with you.”).\n- During: keep language minimal, offer two concrete choices (headphones or the quiet spot), keep Alex on the quieter side of the line, and use a 1‑minute “countdown + put‑on” routine to hand him headphones right before the alarm.\n- After: do a brief 1–2 minute praise/debrief and allow a short quiet break or token reward.\n\nI can prepare a laminated visual card and the 3‑sentence social story for you to print—would you like me to leave them at his desk or email the files?',
                    'tokens': {
                        'prompt': 666,
                        'completion': 1675,
                        'total': 2341
                    },
                    'cost': 0.0011049
                }
            }
        ]
    },
    {
        'prompt': 'Draft an IEP progress report for Jordan Smith',
        'full_response': 'I’ve drafted Jordan Smith’s IEP progress report for 9/1/2025–2/24/2026: overall strong progress but not yet at annual targets. Jordan is on-task ~72% (target 80%), completes work on time ~82% with ~78% accuracy (targets 85%/80%), and uses self-regulation tools independently in ~60% of transitions (still averaging ~1–2 prompts). Movement breaks, chunking, standing desk, visual timers, and para support are effective; fading prompts toward student self-monitoring is the next instructional focus. \n\n- Recommend increasing special education consultation to 2x/week for 8 weeks, shift paraeducator role to coaching/fading prompts, and consider OT consult plus small-group counseling for wait/turn-taking skills.  \n- Continue weekly interval and assignment monitoring and review data at the IEP team meeting in 6–8 weeks; please update Jordan’s grade in the student file.\n\nI can finalize this into the official IEP progress report and draft the meeting notice—would you like me to do that?',
        'steps': [
            {
                'module': 'PLANNER',
                'prompt': {
                    'action': 'create_plan',
                    'query_snippet': 'Draft an IEP progress report for Jordan Smith',
                    'messages': [
                        {
                            'role': 'system',
                            'content': PLANNER_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': PLANNER_USER_PROMPT.format(
                                query='Draft an IEP progress report for Jordan Smith'
                            )
                        }
                    ]
                },
                'response': {
                    'content': '{\n  "student_name": "Jordan Smith",\n  "steps": [\n    {\n      "step_index": 0,\n      "agent": "ADMIN_AGENT",\n      "task": "Draft a comprehensive IEP progress report for Jordan Smith for the current reporting period. Pull Jordan\'s stored student profile and recent progress notes internally. Include: report period dates; student identifying info (grade, disability); summary of services provided; each IEP goal with baseline, measurable progress data, examples/evidence (assessments, work samples, observations), and a clear statement of current level of performance; a percentage or qualitative rating of goal attainment where possible; accommodations and modifications used and their effectiveness; behavior/support information if relevant (incidents, antecedents, interventions, outcomes); recommendations and next steps (changes in services, new goals, referrals); parent communication log summary; and signature lines for case manager, service provider(s), and parent/guardian with dates. Use objective, evidence-based language and keep the report ready to paste into the IEP platform in plain text.",\n      "depends_on": []\n    }\n  ]\n}',
                    'tokens': {
                        'prompt': 681,
                        'completion': 682,
                        'total': 1363
                    },
                    'cost': 0.0005113499999999999
                }
            },
            {
                'module': 'ADMIN_AGENT',
                'prompt': {
                    'action': 'iep_document',
                    'student': 'Jordan Smith',
                    'query_type': 'IEP',
                    'messages': [
                        {
                            'role': 'system',
                            'content': ADMIN_AGENT_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': ADMIN_AGENT_IEP_PROMPT.format(
                                query='Draft an IEP progress report for Jordan Smith',
                                student_info=JORDAN_STUDENT_INFO,
                                observations=JORDAN_OBSERVATIONS,
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'IEP Progress Report — Jordan Smith\nReporting period: 09/01/2025 – 02/24/2026\n\nStudent Identifying Information\n- Name: Jordan Smith\n- Grade: Unknown (grade not provided in file; please update student record)\n- Disability: Attention-Deficit/Hyperactivity Disorder (ADHD)\n- Preferred learning style: Kinesthetic\n- Known triggers: Long sitting periods; transitions between activities; waiting for turn; boring or repetitive tasks\n- Successful instructional methods: Movement breaks every 15 minutes; hands-on activities; chunked tasks with clear endpoints; visual timers; standing desk option; fidget tools\n- Methods to avoid: Long lectures; worksheets without breaks; extended sitting; tasks without clear structure\n\nSummary of Services Provided During Reporting Period\n- Special education consultation (weekly, 30 minutes) with classroom teacher to implement accommodations and monitor progress.\n- Direct support in-class from a paraeducator (daily, up to 30 minutes per day) for task chunking, cueing, and prompting during identified high-demand lessons.\n- Behavior strategy plan implemented classroom-wide with teacher and paraeducator support; movement breaks scheduled every 15 minutes.\n- Progress monitoring via weekly teacher-completed interval recording (partial-interval on-task sampling), work completion logs, and brief observational notes.\n- Parent communication by phone/email and one in-person meeting to review progress and strategies.\n\nIEP Goals, Baselines, Progress Data, Evidence, and Current Level of Performance\nNote: Goals are presented in SMART format. Short-term objectives (STOs) and progress monitoring methods are included for each goal.\n\nGoal 1 — On-Task Behavior and Attention\n- Goal (SMART): By 06/12/2026, when participating in classroom instruction for core academic tasks, Jordan will be actively on-task during teacher-led and independent work periods for 80% of monitored intervals across three consecutive weeks, as measured by partial-interval recording during 30-minute observation sessions.\n- Baseline (09/01/2025): Partial-interval sampling conducted during three baseline sessions indicated on-task behavior in 45% of intervals (range 40–50%).\n- Progress monitoring data (09/01/2025–02/24/2026): Weekly partial-interval recordings (30-minute sessions, 6 observations per week) show a progressive increase in on-task intervals. Aggregate average across reporting period = 72% on-task (weekly averages ranged 60%–82%).\n- Evidence/examples: Teacher weekly logs; six sample observation forms; video-assisted observation (one 20-minute clip reviewed by case manager); classroom work showing greater consistency when movement breaks and chunking used.\n- Current level of performance: Jordan is on-task approximately 72% of monitored intervals. Jordan has met short-term objectives demonstrating incremental increases from baseline and is approaching the annual goal but has not yet reached the 80% mastery target.\n- Goal attainment rating: Progressing — approximately 72% attainment toward target (qualitative: Significant improvement; near target).\n\nShort-term objectives for Goal 1 (examples being monitored):\n1. Within 8 weeks, Jordan will increase on-task intervals to at least 60% during monitored sessions.\n2. Within 16 weeks, Jordan will increase on-task intervals to at least 70% during monitored sessions.\n(Progress: both STOs achieved; current goal trending toward annual target.)\n\nGoal 2 — Task Completion and Work Accuracy\n- Goal (SMART): By 06/12/2026, Jordan will complete and submit 85% of assigned classroom tasks on time with at least 80% accuracy on grade-level supports, across a four-week monitoring window, as recorded by teacher assignment logs and accuracy checks.\n- Baseline (09/01/2025): Teacher assignment logs indicated 50% of assignments completed on time with an average accuracy of 68% (work samples reviewed).\n- Progress monitoring data (09/01/2025–02/24/2026): Weekly assignment completion logs indicate on-time completion increased to an average of 82% during the most recent four-week window; accuracy increased to an average of 78% on checked samples.\n- Evidence/examples: Collected work samples (10 assignments), teacher gradebook export for the period, rubrics showing accuracy, and paraeducator checklists used during task chunking.\n- Current level of performance: Jordan currently completes assignments on time at an average rate of 82% and achieves approximately 78% accuracy on monitored tasks. Jordan is close to the 85% on-time target and near the 80% accuracy target.\n- Goal attainment rating: Progressing — nearing mastery (on-time completion: ~97% of the annual target; accuracy: ~98% of target).\n\nShort-term objectives for Goal 2 (examples):\n1. With teacher supports and chunking, Jordan will complete 70% of assignments on time within 8 weeks.\n2. With accuracy checks and corrective feedback, Jordan will reach 75% accuracy within 12 weeks.\n(Progress: both STOs met; continued supports recommended to reach annual target.)\n\nGoal 3 — Self-Regulation and Transitioning\n- Goal (SMART): By 06/12/2026, Jordan will independently use self-regulation strategies (visual timer, mini-movement break, brief self-monitor checklist) to transition between activities with no more than 1 verbal prompt on average per transition across a two-week monitoring period.\n- Baseline (09/01/2025): Teacher and paraeducator recorded an average of 6 prompts per day needed to assist Jordan with transitions; frequent brief refusal or delay behaviors observed.\n- Progress monitoring data (09/01/2025–02/24/2026): Weekly transition logs show prompts per transition decreased to an average of 1.8 prompts per transition during the most recent three-week period; independent use of visual timer/self-checklist observed in approximately 60% of transitions.\n- Evidence/examples: Transition logs completed by paraeducator, teacher observation notes, student self-monitor checklist samples, and reduction in duration of transition-related disruptions.\n- Current level of performance: Jordan is using self-regulation strategies independently in approximately 60% of transitions and requires about 1–2 prompts per transition on average. This is improved from baseline but not yet at the target of no more than 1 prompt.\n- Goal attainment rating: Progressing — moderate gains; continued focus required.\n\nShort-term objectives for Goal 3:\n1. Within 6 weeks, Jordan will use a visual timer with prompting in 75% of transitions.\n2. Within 12 weeks, Jordan will demonstrate independent initiation of one brief self-regulation strategy in 60% of transitions.\n(Progress: STO1 met with prompts; STO2 met partially — independent initiation at 60%.)\n\nAccommodations, Modifications, and Their Effectiveness\nAll accommodations below were implemented consistently unless noted; effectiveness is rated based on teacher/para logs and observed outcomes.\n- Movement breaks every 15 minutes (effective): Immediate reductions in off-task behavior and transition outbursts; correlated with improved on-task intervals (noted increase of ~27 percentage points since baseline).\n- Chunking tasks with clear endpoints and check-ins (effective): Increased assignment completion and reduced refusal; improved accuracy through in-process feedback.\n- Visual timers for work periods/transitions (moderately effective): Increased student awareness of time; helped reduce protest behaviors during transitions when combined with movement breaks; independent use still emerging.\n- Standing desk option (effective when used): Observable increase in engagement during reading/math stations; preferred by Jordan several days/week.\n- Fidget tools (partially effective): Reduced some minor restlessness; helped during brief independent work but not sufficient alone during longer tasks.\n- Preferential seating near teacher (effective): Reduced distractions and improved response to prompts.\n- Extended time on timed tests (as needed) (effective): Maintained performance without increased anxiety.\n- Teacher-prepared chunked worksheets and oral directions (effective): Improved comprehension and task initiation.\n\nBehavior/Support Information\n- Incidents: During the reporting period there were 4 recorded minor noncompliance incidents (does not include disciplinary removals) related to prolonged sitting or waiting for turns. Incidents involved brief refusal to begin task or vocal protests; none escalated to physical aggression.\n- Antecedents: Long seated lessons (>20 minutes without break), unexpected change in routine, and waiting for peer turn during group work.\n- Interventions used: Immediate movement break, use of visual timer/countdown, brief proximity prompt from paraeducator, and offering an alternative hands-on entry task. Positive reinforcement provided on completion.\n- Outcomes: In all 4 incidents, the interventions reduced the duration of the behavior within 2–5 minutes and Jordan returned to task. No suspensions or office referrals during the period.\n- Functional considerations: Behaviors are consistent with ADHD-related difficulties managing sustained attention and tolerance for waiting; interventions focusing on active engagement and predictable structure are effective.\n\nRecommendations and Next Steps\n- Continue current effective accommodations: Continue movement breaks every 15 minutes, chunked tasks, standing desk access, visual timers, and paraeducator support during identified high-demand lessons.\n- Adjustments to services:\n  - Increase direct special education consultation to twice weekly (30 minutes each) for the next 8 weeks to support teachers in fading prompts and increasing student independence with self-monitoring strategies.\n  - Maintain paraeducator in-class support but shift focus from constant prompting to coaching Jordan in self-monitoring and using strategies independently.\n- New or revised goals:\n  - Maintain current goals with a revised target date of 06/12/2026; consider adding an explicit self-monitoring goal (e.g., Jordan will independently complete a 3-step self-monitor checklist before requesting a prompt in 80% of opportunities).\n- Additional referrals:\n  - Consider a consult with Occupational Therapy for sensory strategy refinement (if not already completed) to optimize standing/sensory options and fine-tune fidget tool selection.\n  - Consider school counseling or small-group social skills/self-regulation sessions (10–12 weeks) to support coping with waiting and turn-taking in social contexts.\n- Progress monitoring: Continue weekly interval recordings for on-task behavior and weekly assignment completion logs; review data in IEP team meeting in 6–8 weeks to determine if accommodations can be faded or goals adjusted.\n- Administrative note: Grade level should be updated in the student record to ensure alignment of curriculum expectations and accurate goal-setting.\n\nParent/Guardian Communication Log (Summary)\n- 09/10/2025 — Email from teacher: Positive note about increased engagement with standing desk and movement breaks; provided suggestions for home practice (short, structured tasks with timers). Parent acknowledged and implemented similar structure at home.\n- 11/05/2025 — Phone call: Case manager and parent discussed mid-term progress; parent reported Jordan is more willing to start homework when given movement break first. Agreed to continue movement breaks at school and home.\n- 01/20/2026 — In-person meeting: Reviewed collected data and work samples; parent provided permission to trial increased movement breaks and supported OT consultation. Parent expressed satisfaction with progress and requested continued regular updates.\n- Ongoing: Weekly brief email updates are sent to parent summarizing strategies used and notable successes. Parent prefers email and phone; contact information on file confirmed.\n\nSignatures\nCase Manager: _______________________________  Date: _______________\nName/Title: __________________________________\n\nService Provider (Classroom Teacher): _______________________________  Date: _______________\nService Provider (Paraeducator/Other): _______________________________  Date: _______________\n\nParent/Guardian: _______________________________  Date: _______________\nRelationship to Student: _______________________\n\nReport Prepared By: __________________________  Date: _______________\n(Notes: Please add Jordan’s current grade to the student file; consider scheduling the next IEP team review in 8 weeks to evaluate response to the recommended service adjustments.)\n\nEvidence-Based Practices Referenced\n- Frequent, brief movement breaks; chunking of tasks; visual supports and timers; preferential seating/standing desk; explicit self-monitoring and reinforcement; all are supported by evidence-based strategies for students with ADHD and kinesthetic learning preferences.\n\nEnd of Report',
                    'tokens': {
                        'prompt': 444,
                        'completion': 3464,
                        'total': 3908
                    },
                    'cost': 0.0021449999999999998
                }
            },
            {
                'module': 'PRESENTER',
                'prompt': {
                    'action': 'present_response',
                    'query_snippet': 'Draft an IEP progress report for Jordan Smith',
                    'original_length': 12830,
                    'messages': [
                        {
                            'role': 'user',
                            'content': FINAL_PRESENTATION_PROMPT.format(
                                query='Draft an IEP progress report for Jordan Smith',
                                agent_response=(
                                    "IEP Progress Report — Jordan Smith\n"
                                    "Reporting period: 09/01/2025 – 02/24/2026\n\n"
                                    "Student Identifying Information\n"
                                    "- Name: Jordan Smith\n"
                                    "- Grade: Unknown (grade not provided in file; please update student record)\n"
                                    "- Disability: Attention-Deficit/Hyperactivity Disorder (ADHD)\n"
                                    "- Preferred learning style: Kinesthetic\n"
                                    "- Known triggers: Long sitting periods; transitions between activities; waiting for turn; boring or repetitive tasks\n"
                                    "- Successful instructional methods: Movement breaks every 15 minutes; hands-on activities; chunked tasks with clear endpoints; visual timers; standing desk option; fidget tools\n"
                                    "- Methods to avoid: Long lectures; worksheets without breaks; extended sitting; tasks without clear structure"
                                )
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'I’ve drafted Jordan Smith’s IEP progress report for 9/1/2025–2/24/2026: overall strong progress but not yet at annual targets. Jordan is on-task ~72% (target 80%), completes work on time ~82% with ~78% accuracy (targets 85%/80%), and uses self-regulation tools independently in ~60% of transitions (still averaging ~1–2 prompts). Movement breaks, chunking, standing desk, visual timers, and para support are effective; fading prompts toward student self-monitoring is the next instructional focus. \n\n- Recommend increasing special education consultation to 2x/week for 8 weeks, shift paraeducator role to coaching/fading prompts, and consider OT consult plus small-group counseling for wait/turn-taking skills.  \n- Continue weekly interval and assignment monitoring and review data at the IEP team meeting in 6–8 weeks; please update Jordan’s grade in the student file.\n\nI can finalize this into the official IEP progress report and draft the meeting notice—would you like me to do that?',
                    'tokens': {
                        'prompt': 2884,
                        'completion': 809,
                        'total': 3693
                    },
                    'cost': 0.000918
                }
            }
        ]
    },
    {
        'prompt': 'What de-escalation techniques can I use for a student with emotional behavioral disorder who is becoming agitated?',
        'full_response': 'That sounds really difficult — here are short, practical steps that often stop escalation and keep everyone safe.\n\n- Use immediate, low-demand de-escalation: calm voice and slow pace, one simple instruction or a limited choice (“Sit here or step into the hallway for a minute”), and offer a very short timed break or 4-4-4 breathing.  \n- Offer a practiced cool-down space: brief, predictable time limit, visual timer, familiar calming items, and remove the peer audience when possible.  \n- Build long-term supports: teach 2–3 coping skills in 5–10 minute rehearsals with cue cards, do brief daily check-ins to build trust, and reduce triggers with seating/visual schedules.\n\nIf the student becomes a safety risk, follow your school crisis plan and call trained staff. If helpful, I can draft a one-page staff plan or a short script you can use with the student.',
        'steps': [
            {
                'module': 'PLANNER',
                'prompt': {
                    'action': 'create_plan',
                    'query_snippet': 'What de-escalation techniques can I use for a student with emotional behavioral disorder who is beco',
                    'messages': [
                        {
                            'role': 'system',
                            'content': PLANNER_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': PLANNER_USER_PROMPT.format(
                                query='What de-escalation techniques can I use for a student with emotional behavioral disorder who is becoming agitated?'
                            )
                        }
                    ]
                },
                'response': {
                    'content': '{\n  "student_name": null,\n  "steps": [\n    {\n      "step_index": 0,\n      "agent": "RAG_AGENT",\n      "task": "Provide evidence-based de-escalation techniques for a student with Emotional/Behavioral Disorder (EBD) who is becoming agitated. Include: 1) concise, prioritized immediate de-escalation steps a teacher can use in the moment (verbal scripts, tone/language, nonverbal strategies, use of proximity, safe body positioning); 2) short calming phrases and example teacher scripts for different levels of agitation; 3) sensory and environmental supports (low-stimulus spaces, break cards, sensory tools) and how to implement them quickly; 4) antecedent/preventive strategies to reduce future agitation (routines, choice, expectations, visual supports, reinforcement strategies); 5) clear decision points for when to remove the student, use a short cool-down, or call for additional staff; 6) safety and debriefing procedures (how to record incidents, communicate with parents/teams, post-incident teaching); 7) adaptations by age/grade and cognitive/communication level; and 8) brief citations or references to evidence-based sources and recommended further reading. Keep the guidance practical and classroom-ready, with bulletable steps and short example language teachers can use immediately."\n      "depends_on": []\n    }\n  ]\n}',
                    'tokens': {
                        'prompt': 693,
                        'completion': 749,
                        'total': 1442
                    },
                    'cost': 0.00055335
                }
            },
            {
                'module': 'RAG_AGENT',
                'prompt': {
                    'action': 'general_search',
                    'query_snippet': 'What de-escalation techniques can I use for a student with emotional behavioral disorder who is beco',
                    'methods_found': 7,
                    'messages': [
                        {
                            'role': 'system',
                            'content': RAG_AGENT_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': RAG_AGENT_NO_CONTEXT_PROMPT.format(
                                query='What de-escalation techniques can I use for a student with emotional behavioral disorder who is becoming agitated?',
                                retrieved_methods=RAG_METHODS_SAMPLE,
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'Short answer: Use a mix of immediate de-escalation techniques (low-demand, predictable actions that lower arousal), a safe cool-down option, teaching of coping skills so the student can use strategies independently, and ongoing relationship-building and environmental adjustments to prevent escalations. Below are specific, practical options you can pick from right away.\n\n1) De-escalation Strategies\n- What it is and why it works:\n  - Immediate, calm actions and language to reduce a student’s physiological arousal and defensiveness. It works because lowering heart rate and perceived threat restores capacity to think and choose behavior.\n- How to implement (pick 1–2 to use quickly):\n  - Use a calm voice, slow pace, and neutral language: “I can see you’re upset. I’m here to help.”\n  - Give one simple, low-demand instruction or choice: “You can sit here or step into the hallway for a minute—your choice.”\n  - Offer a short, timed break: “Let’s take two minutes to breathe and then check in.”\n  - Use tactical breathing or 4-4-4 breathing: breathe in 4, hold 4, out 4 (practice beforehand).\n  - Remove peer audience when possible (brief escort to quieter spot).\n  - If verbal prompts fail, offer a concrete alternative (seat change, sensory item).\n- Best for:\n  - Any student beginning to show agitation, especially when you need to stop escalation quickly.\n- If it’s not working:\n  - Move to a pre-planned cool-down space or call for trained support per school safety plan.\n\n2) Cool-Down Space\n- What it is and why it works:\n  - A designated, predictable place where a student can regain composure. It reduces perceived threat and provides sensory control.\n- How to implement:\n  - Keep it quick and available: “You can use the calm corner for five minutes and then we’ll check in.”\n  - Make rules explicit and visual (how long, what’s allowed).\n  - Stock with familiar calming items (soft chair, headphones, weighted lap pad if approved, visual timer).\n  - Teach and practice the routine when the student is calm so it’s known in the moment.\n- Best for:\n  - Students who need space from the classroom sensory load or who respond to a change of setting.\n- Sensory triggers to watch:\n  - Avoid bright lights, loud noises, or unexpected stimuli in the space. Provide dim lighting, soft textures, and quiet.\n- If it’s not working:\n  - Offer a supervised walk outside or another pre-teachened de-escalation routine, and notify support staff.\n\n3) Coping Skills Instruction\n- What it is and why it works:\n  - Explicit teaching of emotion-regulation skills (naming feelings, breathing, self-talk, problem-solving). It works by giving students tools to interrupt escalation before it becomes a crisis.\n- How to implement:\n  - Short, repeated lessons (5–10 min) teaching 2–3 strategies: stop-and-breathe, name-feeling-then-act, use-a-cue-card.\n  - Practice with role-play and visual supports (cue cards: “Take three breaths,” “Ask for a break”).\n  - Create a personalized coping plan with the student listing what helps and where they go.\n- Best for:\n  - Students who can learn and rehearse strategies during calm times and then use them with prompts.\n- If it’s not working:\n  - Break skills into smaller steps, use more modeling, or pair with immediate supports (cue cards, teacher prompts).\n\n4) Relationship Building\n- What it is and why it works:\n  - Intentional, consistent positive interactions so the student trusts staff. Trust reduces perceived threat and increases likelihood the student will accept help.\n- How to implement:\n  - Brief daily check-ins (1–2 minutes): “How’s your morning?” or a positive note home once a week.\n  - Use specific praise for small steps: “Thanks for taking that breath—that helped.”\n  - Keep predictable routines and follow-through on agreements.\n- Best for:\n  - All students, especially those whose escalation is linked to feeling misunderstood or targeted.\n- If it’s not working:\n  - Involve a counselor or trusted adult, or try different touchpoints (lunch check-ins, passing greeting).\n\n5) Self-Regulation Strategies (including sensory adjustments)\n- What it is and why it works:\n  - Teaching the student to recognize bodily warning signs and use sensory tools or activities to lower arousal. It works by addressing the physiological triggers of escalation.\n- How to implement:\n  - Teach early-warning signs (e.g., clenched jaw, racing thoughts) with visuals and practice.\n  - Offer quick sensory options: deep-pressure squeeze, chair push-downs, a short walk, use of a stress ball or chewing tool (if allowed).\n  - Build a simple “if-then” plan: “If I feel chest tight, I will go to the calm corner and do 5 slow breaths.”\n- Best for:\n  - Students whose escalation is linked to sensory overload or physical signs of stress.\n- Sensory triggers to watch:\n  - Loud noises, crowded spaces, uncomfortable textures—offer noise-reducing headphones, predictable seating, or soft materials.\n- If it’s not working:\n  - Collaborate with OT or counselor to assess sensory needs and try different tools.\n\n6) Environmental Modifications\n- What it is and why it works:\n  - Changing classroom factors that trigger or maintain agitation (noise, transitions, unpredictability). It works by reducing triggers and increasing predictability.\n- How to implement:\n  - Simplify transitions: give a 1–3 minute warning and visual countdown.\n  - Seat the student away from known triggers (door, noisy equipment) and near a calm adult.\n  - Use visual schedules and clear expectations to reduce surprise.\n- Best for:\n  - Students who escalate in specific settings or during transitions.\n- If it’s not working:\n  - Trial more targeted changes (alternate route for transitions, smaller group work) and collect quick data on what reduces incidents.\n\nQuick scripts and tips you can use now\n- Calming script: “I can see you’re upset. I want to help. Would you like to sit here and breathe with me for two minutes, or take a short walk?”\n- Offer choice (gives control): “Do you want to use the calm corner or listen to headphones?”\n- Use time-limited offers: “Take three minutes. I’ll check back then.”\n\nWhen to use backup supports\n- If the student becomes a danger to themselves or others, follow your school’s crisis/safety protocol and call trained staff. De-escalation must not replace safety plans.\n\nTwo quick combinations that work well together\n- Option A (short-term): Calm language + choice + cool-down space (use immediately).\n- Option B (long-term): Teach coping skills + scheduled check-ins + environmental tweaks (prevent future escalations).\n\nFinal note\n- Practice these routines with the student when they are calm so they’re familiar in the moment. Keep a short, written plan for staff to follow (what calms the student, triggers, and supports to call).',
                    'tokens': {
                        'prompt': 507,
                        'completion': 2000,
                        'total': 2507
                    },
                    'cost': 0.00127605
                }
            },
            {
                'module': 'PRESENTER',
                'prompt': {
                    'action': 'present_response',
                    'query_snippet': 'What de-escalation techniques can I use for a stud',
                    'original_length': 6774,
                    'messages': [
                        {
                            'role': 'user',
                            'content': FINAL_PRESENTATION_PROMPT.format(
                                query='What de-escalation techniques can I use for a student with emotional behavioral disorder who is becoming agitated?',
                                agent_response=(
                                    "Short answer: Use a mix of immediate de-escalation techniques (low-demand, predictable actions that lower arousal), "
                                    "a safe cool-down option, teaching of coping skills so the student can use strategies independently, and ongoing relationship-building."
                                )
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'That sounds really difficult — here are short, practical steps that often stop escalation and keep everyone safe.\n\n- Use immediate, low-demand de-escalation: calm voice and slow pace, one simple instruction or a limited choice (“Sit here or step into the hallway for a minute”), and offer a very short timed break or 4-4-4 breathing.  \n- Offer a practiced cool-down space: brief, predictable time limit, visual timer, familiar calming items, and remove the peer audience when possible.  \n- Build long-term supports: teach 2–3 coping skills in 5–10 minute rehearsals with cue cards, do brief daily check-ins to build trust, and reduce triggers with seating/visual schedules.\n\nIf the student becomes a safety risk, follow your school crisis plan and call trained staff. If helpful, I can draft a one-page staff plan or a short script you can use with the student.',
                    'tokens': {
                        'prompt': 1879,
                        'completion': 901,
                        'total': 2780
                    },
                    'cost': 0.00082245
                }
            }
        ]
    },
    {
        'prompt': 'What should I watch for today? Any students at risk?',
        'full_response': 'I know juggling multiple students with different needs today can feel high-stakes; here’s a calm, concise watchlist with key strategies and exact timing to use. Keep a private signal and a cool-down spot ready in case of escalation.\n\n- Riley Martinez — High risk: pre-assign a low-conflict role, give short chunked steps with a private check-in card, seat near you/calm peer and avoid public critique; do pre-class check-ins at 10:05 (Science) and 12:55 (Art) and intervene at the first sign of frustration.  \n- Jordan Smith — Medium risk: give a time-marked agenda and an active role, schedule a 1-minute movement break every ~15–20 minutes, and remind Jordan where to go during transitions; provide agenda and role at 10:15 and the first movement break ~10:30, with an alternate workspace ready by 12:55 for Art.  \n- Taylor Williams — Medium risk: provide written instructions plus a short vocab list and a visual glossary, avoid cold-calling, and pair with a supportive peer for previews; handouts at 10:15, quick vocab preview within 5 minutes, and glossary/expectations set at 12:55.  \n- Alex Johnson — Low risk: announce group plans and transition signals in advance, keep a consistent workspace, and offer a quiet sideline or headphones for PE; tell Alex plans at each class start (10:15, 13:00, 14:15) and give 1–2 minute warnings before transitions.  \n- Morgan Davis — Low risk: avoid strong-odor materials when possible, seat near ventilation/upwind, offer masks/gloves or a paint-free alternative, and warn before noisy activities; notify Morgan before experiments/paints and set seating/alternatives at 12:55.  \n- Casey Brown — Low risk: provide short numbered steps, one demo or visual exemplar, and a peer “clarifier” for hands-on tasks; distribute steps at class start and demo within the first 3–5 minutes.\n\nHighest-priority reminder: Riley in Science (10:15) and Art (13:00) — do the pre-class check-ins and have a discreet signal ready. For all group/hands-on work, keep written steps and a private break plan visible; if escalation occurs, remove the student to the cool-down spot quickly and notify admin if it becomes physical. \n\nIf you’d like, I can format this into a one-page quick-reference card with names, timings, and discreet signals.',
        'steps': [
            {
                'module': 'PLANNER',
                'prompt': {
                    'action': 'create_plan',
                    'query_snippet': 'What should I watch for today? Any students at risk?',
                    'messages': [
                        {
                            'role': 'system',
                            'content': PLANNER_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': PLANNER_USER_PROMPT.format(
                                query='What should I watch for today? Any students at risk?'
                            )
                        }
                    ]
                },
                'response': {
                    'content': '{\n  "student_name": "ALL_STUDENTS",\n  "steps": [\n    {\n      "step_index": 0,\n      "agent": "PREDICT_AGENT",\n      "task": "Review all stored student profiles and any available schedule or calendar info for today. Produce a prioritized, actionable \'watch list\' of students who are at elevated risk today. For each student flagged, include: (1) brief reason(s) they\'re at risk (triggers, recent incidents, disability-related vulnerabilities, notes), (2) specific times/events today when risk is highest, (3) observable early warning signs to watch for, (4) immediate in-the-moment strategies/interventions the teacher can use, (5) short environmental or seating adjustments and staff supports to notify, and (6) recommended monitoring/check-in frequency. Highlight the top 3 highest-priority students in a 1–2 sentence summary each. If no schedule is available, identify common high-risk periods (transitions, recess, assessments, substitutes) and flag students prone to those situations. Keep recommendations concise and classroom-ready.",\n      "depends_on": []\n    }\n  ]\n}',
                    'tokens': {
                        'prompt': 683,
                        'completion': 1012,
                        'total': 1695
                    },
                    'cost': 0.0007096499999999999
                }
            },
            {
                'module': 'PREDICT_AGENT',
                'prompt': {
                    'action': 'daily_briefing',
                    'events_count': 9,
                    'predictions_count': 15,
                    'messages': [
                        {
                            'role': 'system',
                            'content': PREDICT_AGENT_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': PREDICT_DAILY_BRIEFING_PROMPT.format(
                                events=PREDICT_EVENTS_SAMPLE,
                                at_risk_students=PREDICT_AT_RISK_SAMPLE,
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'Riley Martinez — Science Class (10:15)\n- Risk: Riley is high-risk: group work + hands-on tasks increase chances of peer conflict, frustration with difficult tasks, and being publicly corrected.\n- Strategies: 1) Pre-assign a clear, low-conflict role in the group (e.g., materials manager) to limit social friction; 2) Give short, chunked task steps with a private “check-in” card Riley can use instead of public questions; 3) Seat Riley near you or a calm peer and plan a discreet signal if they need a break.\n- Timing: Prep role and written steps 10 minutes before class (10:05); private check-in during first 5 minutes; intervene at first sign of frustration.\n\nRiley Martinez — Art Class (13:00)\n- Risk: High-risk: sensory materials and peer interactions can trigger frustration and conflicts; public critique may provoke negative reactions.\n- Strategies: 1) Offer a private “no public critique” agreement — feedback to be given privately; 2) Provide a simplified project rubric and one tangible alternative if materials/technique frustrates them; 3) Place Riley near the teacher and remind peers about respectful feedback.\n- Timing: Quick check-in after lunch (12:55–12:58) to set expectations; review rubric at project start.\n\nJordan Smith — Science Class (10:15)\n- Risk: Medium-risk: transitions between activities and prolonged sitting can elevate stress/withdrawal during group work.\n- Strategies: 1) Give a clear, time-marked agenda for the session and a role that reduces long sitting (active role or short rotation); 2) Allow a standing/stretching break or a 1-minute movement task every ~15–20 minutes; 3) Remind Jordan of where to go and what to do during the group-to-whole-class transition.\n- Timing: Provide agenda and role at start of class (10:15); schedule first movement break ~10:30.\n\nJordan Smith — Art Class (13:00)\n- Risk: Medium-risk: Art may require sitting for fine motor work and has transitions (setup/cleanup) that can be hard.\n- Strategies: 1) Offer an alternate standing table or a fidget tool for fine-motor focus; 2) Break the project into timed phases with explicit transition cues and a visual timer; 3) Assign a cleanup partner who can cue and help with transitions.\n- Timing: Prep alternate workspace before class (12:55); set visual timer at project start.\n\nTaylor Williams — Science Class (10:15)\n- Risk: Medium-risk: Science may involve reading instructions aloud and unfamiliar vocabulary, which can cause anxiety.\n- Strategies: 1) Provide written instructions and a short vocabulary list with simple definitions before group work; 2) Avoid cold-calling; allow volunteers or small-group reading instead of whole-class reading aloud; 3) Pair Taylor with a supportive peer to preview terms.\n- Timing: Hand out written materials right at class start (10:15); quick vocabulary preview within first 5 minutes.\n\nTaylor Williams — Art Class (13:00)\n- Risk: Medium-risk: unfamiliar art terms and occasional group read-alouds could trigger anxiety.\n- Strategies: 1) Provide a brief visual glossary (images + labels) at each station; 2) Offer instructions in written + verbal form and allow Taylor to read silently or with a partner; 3) Give advance notice if you plan to ask students to share aloud.\n- Timing: Place glossary at station before class (12:55); remind Taylor of sharing expectations at setup.\n\nAlex Johnson — Science Class (10:15)\n- Risk: Low-risk: sensitive to unexpected transitions; Science group shifts may be disruptive.\n- Strategies: 1) Tell Alex the group plan and signal for transitions in advance; 2) Keep their seat/work area consistent each rotation; 3) Use a 1–2 minute warning before transitions.\n- Timing: Announce rotation plan at start (10:15); give transition warnings 2 minutes prior.\n\nMorgan Davis — Science Class (10:15)\n- Risk: Low-risk: strong smells from experiments can be problematic.\n- Strategies: 1) If the experiment uses odors, provide alternatives (mask, sit near window) or choose low-odor materials; 2) Seat Morgan upwind/near ventilation; 3) Give notice that smells may occur and an escape route (step outside) if needed.\n- Timing: Notify Morgan prior to experiment start; position seating right before class begins.\n\nCasey Brown — Science Class (10:15)\n- Risk: Low-risk: ambiguous instructions can cause confusion during hands-on tasks.\n- Strategies: 1) Provide short, numbered written steps and check for understanding with a quick thumbs-up; 2) Assign a peer “clarifier” to help if instructions are unclear; 3) Use one demonstration example before groups start.\n- Timing: Distribute steps at class start; demo in first 3–5 minutes.\n\nAlex Johnson — Art Class (13:00)\n- Risk: Low-risk: unexpected transitions/setup changes in art can unsettle Alex.\n- Strategies: 1) Keep Alex’s workspace consistent and post a clear sequence of materials/setup steps; 2) Use a 2-minute warning before cleanup; 3) Offer a brief preview of each phase before students switch tasks.\n- Timing: Set workspace before class; preview phases at 13:00.\n\nMorgan Davis — Art Class (13:00)\n- Risk: Low-risk: strong smells from paints/solvents may trigger discomfort.\n- Strategies: 1) Use low-odor paints or provide gloves/mask; 2) Seat Morgan near ventilation or an open window; 3) Offer a paint-free alternative project if smells are strong.\n- Timing: Communicate alternatives at setup (12:55); seat placement at start.\n\nCasey Brown — Art Class (13:00)\n- Risk: Low-risk: ambiguous creative instructions can lead to frustration/anxiety.\n- Strategies: 1) Give a clear step-by-step tutorial and one visual exemplar; 2) Offer choice-limited options (A/B/C) to reduce ambiguity; 3) Check understanding privately after instructions.\n- Timing: Deliver steps and exemplar at project kickoff.\n\nAlex Johnson — PE Class (14:15)\n- Risk: Low-risk: loud noises in PE can be upsetting.\n- Strategies: 1) Warn Alex about potentially loud parts of the class and offer a quiet spot on the sidelines if needed; 2) Provide headphones/earplugs if appropriate and school policy allows; 3) Use visual signals for transitions rather than sudden vocal calls.\n- Timing: Notify Alex at start of PE; set aside quiet spot before activity begins.\n\nTaylor Williams — PE Class (14:15)\n- Risk: Low-risk: low tolerance for reading aloud — coach cues or roll-calls could require speaking.\n- Strategies: 1) Avoid calling students to read aloud; give instructions visually and verbally to whole group; 2) If names are called, give advance notice or allow nonverbal affirmation; 3) Position Taylor where they won’t be singled out for speaking.\n- Timing: Coach briefing at PE start; remind staff before class.\n\nMorgan Davis — PE Class (14:15)\n- Risk: Low-risk: loud unexpected sounds in PE may be triggering.\n- Strategies: 1) Give a pre-activity warning when noisy drills will happen; 2) Offer an alternate, quieter task area or ear protection; 3) Use a consistent starting signal so surprises are minimized.\n- Timing: Announce noisy activities before they begin; set alternate area at start.\n\nSafety/high-priority reminders\n- Highest priority: Riley in Science (10:15) and Art (13:00). Do pre-class check-ins (10:05, 12:55) and keep an agreed private signal ready.\n- For all group/hands-on activities: have clear, written steps and a private break plan visible to high- and medium-risk students.\n- If any escalation occurs, remove the student from peer setting quickly to a prepared cool-down spot; notify admin if conflict becomes physical.\n\nIf you want, I can format a one-page quick-reference card you can keep with you (timings, student names, discreet signals).',
                    'tokens': {
                        'prompt': 728,
                        'completion': 2870,
                        'total': 3598
                    },
                    'cost': 0.0018312
                }
            },
            {
                'module': 'PRESENTER',
                'prompt': {
                    'action': 'present_response',
                    'query_snippet': 'What should I watch for today? Any students at ris',
                    'original_length': 7575,
                    'messages': [
                        {
                            'role': 'user',
                            'content': FINAL_PRESENTATION_PROMPT.format(
                                query='What should I watch for today? Any students at risk?',
                                agent_response=(
                                    "Riley Martinez — Science Class (10:15)\n"
                                    "- Risk: Riley is high-risk: group work + hands-on tasks increase chances of peer conflict.\n"
                                    "- Strategies: Pre-assign a clear, low-conflict role; use private check-ins; keep a discreet signal."
                                )
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'I know juggling multiple students with different needs today can feel high-stakes; here’s a calm, concise watchlist with key strategies and exact timing to use. Keep a private signal and a cool-down spot ready in case of escalation.\n\n- Riley Martinez — High risk: pre-assign a low-conflict role, give short chunked steps with a private check-in card, seat near you/calm peer and avoid public critique; do pre-class check-ins at 10:05 (Science) and 12:55 (Art) and intervene at the first sign of frustration.  \n- Jordan Smith — Medium risk: give a time-marked agenda and an active role, schedule a 1-minute movement break every ~15–20 minutes, and remind Jordan where to go during transitions; provide agenda and role at 10:15 and the first movement break ~10:30, with an alternate workspace ready by 12:55 for Art.  \n- Taylor Williams — Medium risk: provide written instructions plus a short vocab list and a visual glossary, avoid cold-calling, and pair with a supportive peer for previews; handouts at 10:15, quick vocab preview within 5 minutes, and glossary/expectations set at 12:55.  \n- Alex Johnson — Low risk: announce group plans and transition signals in advance, keep a consistent workspace, and offer a quiet sideline or headphones for PE; tell Alex plans at each class start (10:15, 13:00, 14:15) and give 1–2 minute warnings before transitions.  \n- Morgan Davis — Low risk: avoid strong-odor materials when possible, seat near ventilation/upwind, offer masks/gloves or a paint-free alternative, and warn before noisy activities; notify Morgan before experiments/paints and set seating/alternatives at 12:55.  \n- Casey Brown — Low risk: provide short numbered steps, one demo or visual exemplar, and a peer “clarifier” for hands-on tasks; distribute steps at class start and demo within the first 3–5 minutes.\n\nHighest-priority reminder: Riley in Science (10:15) and Art (13:00) — do the pre-class check-ins and have a discreet signal ready. For all group/hands-on work, keep written steps and a private break plan visible; if escalation occurs, remove the student to the cool-down spot quickly and notify admin if it becomes physical. \n\nIf you’d like, I can format this into a one-page quick-reference card with names, timings, and discreet signals.',
                    'tokens': {
                        'prompt': 2099,
                        'completion': 1684,
                        'total': 3783
                    },
                    'cost': 0.0013252499999999998
                }
            }
        ]
    },
    {
        'prompt': 'Alex had a meltdown during the fire drill today - loud noises really set him off',
        'full_response': 'That sounds really difficult — loud fire drills can be very upsetting for Alex Johnson. I see "loud noises" and "fire drills" are already in his profile; here are a few brief options we could add or try next:\n\n- offer noise-reducing headphones or earplugs during drills  \n- set up a supervised quiet spot he can go to if overwhelmed  \n- give a short advance warning and a social story or rehearsal beforehand\n\nWould you like me to add any of these to his profile or draft a short support plan for the next drill?',
        'steps': [
            {
                'module': 'PLANNER',
                'prompt': {
                    'action': 'create_plan',
                    'query_snippet': 'Alex had a meltdown during the fire drill today - loud noises really set him off',
                    'messages': [
                        {
                            'role': 'system',
                            'content': PLANNER_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': PLANNER_USER_PROMPT.format(
                                query='Alex had a meltdown during the fire drill today - loud noises really set him off'
                            )
                        }
                    ]
                },
                'response': {
                    'content': '{\n  "student_name": "Alex",\n  "steps": [\n    {\n      "step_index": 0,\n      "agent": "STUDENT_AGENT",\n      "task": "Retrieve Alex\'s student profile. Append an incident log entry dated 2026-02-24 with the following text: \'Meltdown during scheduled fire drill; loud noises triggered the event.\' Update the profile\'s triggers field to include \'loud noises / fire alarms / fire drills\' (avoid duplicates). In the notes, record available context: \'Occurred during fire drill; observed as a meltdown.\' If the teacher can provide details now (interventions used, staff present, duration, severity, whether medical attention was needed), include those details in the incident entry and, if applicable, add any methods used to successful_methods or failed_methods. Finally, mark the profile with a follow-up flag recommending caregiver notification and review of supports for future fire drills.",\n      "depends_on": []\n    }\n  ]\n}',
                    'tokens': {
                        'prompt': 688,
                        'completion': 977,
                        'total': 1665
                    },
                    'cost': 0.0006894
                }
            },
            {
                'module': 'STUDENT_AGENT',
                'prompt': {
                    'action': 'extract_update_info',
                    'student': 'Alex Johnson',
                    'query_snippet': 'Alex had a meltdown during the fire drill today - loud noises really set him off',
                    'messages': [
                        {
                            'role': 'user',
                            'content': STUDENT_AGENT_UPDATE_EXTRACT_PROMPT.format(
                                profile=ALEX_PROFILE_TEXT,
                                query='Alex had a meltdown during the fire drill today - loud noises really set him off'
                            )
                        }
                    ]
                },
                'response': {
                    'content': '{\n  "is_update": false,\n  "already_exists": ["loud noises", "fire drills"],\n  "reason": "The message confirms triggers already listed in the profile (loud noises and fire drills); no new information to add.",\n  "updates": {\n    "add_triggers": null,\n    "remove_triggers": null,\n    "add_successful_methods": null,\n    "remove_successful_methods": null,\n    "add_failed_methods": null,\n    "remove_failed_methods": null,\n    "notes": null\n  }\n}',
                    'tokens': {
                        'prompt': 525,
                        'completion': 316,
                        'total': 841
                    },
                    'cost': 0.00026835
                }
            },
            {
                'module': 'PRESENTER',
                'prompt': {
                    'action': 'present_response',
                    'query_snippet': 'Alex had a meltdown during the fire drill today - ',
                    'original_length': 131,
                    'messages': [
                        {
                            'role': 'user',
                            'content': FINAL_PRESENTATION_PROMPT.format(
                                query='Alex had a meltdown during the fire drill today - loud noises really set him off',
                                agent_response=(
                                    "Update confirmation: loud noises and fire drills are already in Alex's profile. "
                                    "Suggested supports: noise-reducing headphones, a quiet spot, and a short advance warning."
                                )
                            )
                        }
                    ]
                },
                'response': {
                    'content': 'That sounds really difficult — loud fire drills can be very upsetting for Alex Johnson. I see "loud noises" and "fire drills" are already in his profile; here are a few brief options we could add or try next:\n\n- offer noise-reducing headphones or earplugs during drills  \n- set up a supervised quiet spot he can go to if overwhelmed  \n- give a short advance warning and a social story or rehearsal beforehand\n\nWould you like me to add any of these to his profile or draft a short support plan for the next drill?',
                    'tokens': {
                        'prompt': 427,
                        'completion': 698,
                        'total': 1125
                    },
                    'cost': 0.00048284999999999995
                }
            }
        ]
    }
]


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
            "The Proactive Co-Teacher is a multi-agent AI assistant designed specifically "
            "for special education teachers. It uses a central ORCHESTRATOR that coordinates "
            "four specialized agents through an LLM-based PLANNER:\n\n"
            "• STUDENT_AGENT — Manages individualized student profiles including disability type, "
            "sensory triggers, successful and failed teaching methods, and learning styles. "
            "Detects implicit profile updates from natural teacher messages (e.g., 'Alex had a "
            "meltdown during the fire drill' automatically flags loud noises as a trigger). "
            "Provides student context to all other agents for personalized responses.\n\n"
            "• RAG_AGENT — Retrieves evidence-based teaching strategies from a vector knowledge "
            "base (Pinecone) using semantic search. Filters recommendations by disability type "
            "(autism, ADHD, dyslexia, sensory processing, emotional/behavioral) and automatically "
            "excludes methods that have previously failed for a specific student. Supports both "
            "general strategy queries and student-personalized recommendations.\n\n"
            "• ADMIN_AGENT — Generates special education administrative documents: IEP progress "
            "reports with SMART goals and measurable data, parent communication emails in a warm "
            "and professional tone, daily/weekly/monthly classroom summaries, and factual incident "
            "reports. Pulls student profiles and daily context observations to ground documents in "
            "real data.\n\n"
            "• PREDICT_AGENT — Provides proactive daily briefings by cross-referencing all student "
            "triggers against today's scheduled events (fire drills, assemblies, substitute teachers, "
            "field trips). Uses rule-based risk calculation (high/medium/low) to flag students who "
            "may struggle, then generates actionable intervention suggestions with specific timing "
            "and scripts.\n\n"
            "The PLANNER uses an LLM call to parse each teacher query into a typed, dependency-ordered "
            "execution plan. Critically, it also extracts the student name from natural language (e.g., "
            "'What are Alex\\'s triggers?' → student_name: 'Alex'), which drives a Supabase lookup that "
            "pre-loads the relevant student profile before any agent runs, so every response is "
            "personalized without agents needing to re-fetch data independently. "
            "A PRESENTER service merges multi-agent "
            "results and applies voice transformation to ensure responses are warm, supportive, "
            "and classroom-ready — all in a single LLM call."
        ),
        "purpose": (
            "To reduce administrative burden on special education teachers by providing "
            "proactive, personalized support. The system handles the cognitive overhead of "
            "tracking multiple students with diverse needs — retrieving individual profiles and "
            "triggers, recommending disability-specific teaching strategies while excluding "
            "previously failed methods, generating IEP reports and parent communications grounded "
            "in real student data, and predicting which students may be at risk on any given day "
            "based on their triggers and the day's schedule. This allows teachers to focus on "
            "teaching and relationship-building rather than paperwork and manual cross-referencing."
        ),
        "prompt_template": {
            "template": (
                "[QUERY_TYPE] [STUDENT_NAME (optional)]: [DETAILS]\n\n"
                "Query types:\n"
                "- Student info: \'Tell me about [name]\', \'What are [name]\'s triggers?\'\n"
                "- Strategies: \'What strategies work for [condition/situation]?\'\n"
                "- Personalized help: \'[name] is [situation]. What should I do?\'\n"
                "- Admin tasks: \'Draft an IEP report for [name]\', \'Write email to parents\'\n"
                "- Predictions: \'What should I watch for today?\', \'Daily briefing\'"
            )
        },
        "prompt_examples": PROMPT_EXAMPLES
    }
