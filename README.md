# Co-Teacher: Multi-Agent AI System for Special Education

A multi-agent AI system designed to assist special education teachers with student management, teaching strategies, administrative tasks, and daily predictions.

**Live Demo**: https://co-teacher-nl17.onrender.com

## Team Information

- **Team Name**: avi_yehoraz_maya
- **Batch/Order**: batch_1_order_9
- **Members**:
  - Avi Simkin (avi.simkin@campus.technion.ac.il)
  - Yehoraz Ben-Yehuda (yehoraz.ben@campus.technion.ac.il)
  - Maya Meirovich (mmeirovich@campus.technion.ac.il)

## Project Overview

Co-Teacher is an autonomous AI agent that helps special education teachers by:
- Retrieving and updating student profiles, triggers, and learning preferences
- Recommending evidence-based teaching strategies via RAG (Retrieval-Augmented Generation)
- Generating administrative documents (IEP reports, parent communications, summaries)
- Providing daily briefings and predictions about potential student challenges

## Architecture

The system uses a **multi-agent architecture** with LLM-based planning:

![Architecture Diagram](./static/architecture.png)

### How It Works

1. **Teacher sends a query** via `POST /api/execute`
2. **Orchestrator** initializes request-scoped tracing, persists the message to Supabase, and loads conversation history
3. **PLANNER** 🤖 decomposes the query into typed plan steps (e.g., `student_lookup`, `rag_search`, `admin_doc`, `predict`)
4. **PLAN_EXECUTOR** dispatches each step to the appropriate specialized agent
5. **Agents** 🤖 execute their tasks using LLM calls, reading from memory stores (STUDENT/ADMIN/PREDICT → Supabase, RAG → Pinecone). Results are passed back to PLAN_EXECUTOR as context for subsequent agents
6. **PLAN_EXECUTOR** formats agent results and passes them to PRESENTER
7. **PRESENTER** 🤖 merges multi-agent results and applies voice transformation in a single LLM call
8. **Orchestrator** persists the assistant response to Supabase and returns the result with full step traces (cost, tokens, timing)

### Agent Descriptions

**STUDENT_AGENT** *(✓ Makes LLM calls)* — Manages individualized student profiles including disability type, sensory triggers, successful and failed teaching methods, and learning styles. Detects implicit profile updates from natural teacher messages (e.g., "Alex had a meltdown during the fire drill" automatically flags loud noises as a trigger). Provides student context to all other agents so that every recommendation is personalized.
- *Example queries*: "What are Alex's triggers?", "Tell me about Jordan's learning style", "Alex had a panic attack during the assembly"

**RAG_AGENT** *(✓ Makes LLM calls)* — Retrieves evidence-based teaching strategies from a vector knowledge base (Pinecone) using semantic search. Filters recommendations by disability type (autism, ADHD, dyslexia, sensory processing, emotional/behavioral) and automatically excludes methods that have previously failed for a specific student. Supports both general strategy queries and student-personalized recommendations.
- *Example queries*: "What de-escalation techniques work for EBD students?", "How should I teach reading to a student with dyslexia?", "What sensory strategies can I use for Alex?"

**ADMIN_AGENT** *(✓ Makes LLM calls)* — Generates special education administrative documents: IEP progress reports with SMART goals and measurable data, parent communication emails in a warm and professional tone, daily/weekly/monthly classroom summaries, and factual incident reports. Pulls student profiles and daily context observations to ground documents in real data rather than generic templates.
- *Example queries*: "Draft an IEP progress report for Jordan", "Write an email to Riley's parents about today's incident", "Give me a weekly summary"

**PREDICT_AGENT** *(✓ Makes LLM calls)* — Provides proactive daily briefings by cross-referencing all student triggers against today's scheduled events (fire drills, assemblies, substitute teachers, field trips). Uses rule-based risk calculation (high/medium/low) to flag students who may struggle, then generates actionable intervention suggestions with specific timing and scripts the teacher can use immediately.
- *Example queries*: "What should I watch for today?", "Any students at risk during the field trip?", "Daily briefing"

### Services

| Service | LLM Calls | Role |
|---------|-----------|------|
| **Orchestrator** | ✗ | Coordinates the entire request pipeline — initializes tracing, persists conversation history to Supabase, invokes PLANNER → PLAN_EXECUTOR (which internally calls agents and PRESENTER) |
| **PLANNER** | ✓ | Receives the teacher's query along with conversation context and produces a typed execution plan — a sequence of steps like `student_lookup`, `rag_search`, `admin_doc`, `predict`, each with dependencies, so agents execute in the correct order |
| **PLAN_EXECUTOR** | ✗ | Walks through the plan steps sequentially, dispatching each to the appropriate agent and passing results from earlier steps as context to later ones. Formats multi-step results for PRESENTER |
| **PRESENTER** | ✓ | Merges multi-agent results and applies voice transformation in a single LLM call using a warm and respectful tone, with a calmer grounding variant for sensitive situations (meltdowns, crises, parent conflicts) |

### Memory Architecture

| Store | Type | Contents |
|-------|------|----------|
| **Supabase** | Short-term (PostgreSQL) | 10 tables: `students` (profiles), `conversations` and `conversation_messages` (chat history), `daily_context` (teacher observations), `events` and `schedule_templates` (calendar), `budget_tracking` (LLM spend), `response_cache` (cached answers), `alerts_sent` and `pending_feedback` (prediction follow-ups) |
| **Pinecone** | Long-term (Vector DB) | `student-profiles` namespace (1536-dim embeddings of student profiles for semantic matching), `teaching-methods` namespace (evidence-based teaching strategies knowledge base scraped from ERIC, IRIS Center, and Wikipedia), `interventions` namespace (intervention outcome tracking) |

### Optimization Strategies

1. **LLM-Based Planning**: The **PLANNER** decomposes each query into the minimal set of agent calls needed — a simple "tell me about Alex" triggers only STUDENT_AGENT, while "prepare Alex for the fire drill" triggers STUDENT_AGENT then RAG_AGENT with dependency chaining
2. **Two-Tier Response Caching**: Supabase (persistent) + in-memory (fast) cache for RAG, Admin, and Predict queries — identical or semantically similar queries return cached results without additional LLM calls
3. **Budget Tracking**: Hard spending limit ($13) enforced with an async lock per LLM call; every call logs model, tokens, and cost to `budget_tracking` in Supabase for full auditability
4. **Lazy Agent Initialization**: Agents, services, and memory clients are created only on first use — if a request only needs RAG_AGENT, the other agents are never instantiated
5. **Rule-Based Risk Calculation**: PREDICT_AGENT uses deterministic trigger-event matching before calling the LLM, reducing unnecessary generation for low-risk students

## API Endpoints

### Required Endpoints (Course Project)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/team_info` | Returns team name, batch/order number, and student members with emails |
| `GET` | `/api/agent_info` | Returns agent description, purpose, prompt template, and 5 prompt examples with full responses and step traces captured from the live deployment |
| `GET` | `/api/model_architecture` | Returns a PNG image of the architecture diagram. Add `?format=json` to get JSON metadata describing all modules, memory stores, and cost optimizations |
| `POST` | `/api/execute` | Main entry point — accepts `{ "prompt": "..." }` and returns `{ status, error, response, steps }` with full execution trace |

### Additional Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/students` | Returns all students with profiles, triggers, and learning preferences |
| `GET` | `/api/students/{student_id}` | Returns a specific student's detailed profile |
| `GET` | `/api/schedule/today` | Returns today's scheduled events and activities |
| `GET` | `/api/predictions/today` | Returns daily risk predictions for all students based on today's schedule |
| `GET` | `/health` | Health check for Render deployment |

### Example: POST /api/execute

**Request:**
```bash
curl -X POST https://co-teacher-nl17.onrender.com/api/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are Alex'\''s sensory triggers and how should I prepare him for the fire drill today?"}'
```

**Response:**
```json
{
  "status": "ok",
  "error": null,
  "response": "That sounds like it could be overwhelming for Alex; here's a short, practical plan...",
  "steps": [
    {
      "module": "PLANNER",
      "prompt": { "action": "create_plan", "query_snippet": "What are Alex's sensory triggers..." },
      "response": { "content": "{ \"student_name\": \"Alex\", \"steps\": [...] }", "tokens": { "prompt": 689, "completion": 959, "total": 1648 }, "cost": 0.00068 }
    },
    {
      "module": "STUDENT_AGENT",
      "prompt": { "action": "get_context", "student": "Alex" },
      "response": { "found": true, "student_id": "STU001" }
    },
    {
      "module": "RAG_AGENT",
      "prompt": { "action": "general_search", "query_snippet": "What are Alex's sensory triggers..." },
      "response": { "content": "Evidence-based sensory strategies...", "tokens": { "total": 2507 }, "cost": 0.00128 }
    },
    {
      "module": "PRESENTER",
      "prompt": { "action": "present_response", "query_snippet": "What are Alex's sensory triggers..." },
      "response": { "content": "Final teacher-friendly response...", "tokens": { "total": 2780 }, "cost": 0.00082 }
    }
  ]
}
```

## Technology Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Backend** | FastAPI (Python 3.11+) | Async API with Pydantic validation and automatic OpenAPI docs |
| **LLM** | LLMod.ai | `gpt-5-mini` for chat completions, `text-embedding-3-small` for 1536-dim embeddings |
| **Short-term Memory** | Supabase (PostgreSQL) | 10 tables covering students, conversations, events, budget tracking, and caching |
| **Long-term Memory** | Pinecone (Vector DB) | Cosine similarity search across student profiles and teaching methods knowledge base |
| **Knowledge Base** | ERIC, IRIS Center, Wikipedia | Scraped and chunked evidence-based teaching strategies for special education |
| **Frontend** | Vanilla HTML/CSS/JS | Chat interface with student sidebar, daily predictions, and step-trace accordion |
| **Deployment** | Render | Auto-deploy from GitHub `main` branch |

## Local Development

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
git clone https://github.com/Maya1807/co_teacher.git
cd co_teacher

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:
```env
LLMOD_API_KEY=your_api_key
LLMOD_BASE_URL=https://api.llmod.ai/v1
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=co-teacher-memory
```

### Database

The Supabase and Pinecone databases are already populated with student profiles, schedules, and the teaching methods knowledge base. No setup is needed to run the app.

If you ever need to re-seed the data from scratch:
```bash
python scripts/seed_data.py       # Supabase (students, schedules, events)
python scripts/seed_pinecone.py   # Pinecone (student profiles, teaching methods KB)
```

### Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the web UI at http://localhost:8000

## Project Structure

```
co_teacher/
├── app/
│   ├── agents/                  # Specialized agent implementations
│   │   ├── base_agent.py        #   Abstract base with step tracking
│   │   ├── orchestrator.py      #   Central coordinator (lazy init, plan dispatch)
│   │   ├── student_agent.py     #   Student profiles, triggers, implicit updates
│   │   ├── rag_agent.py         #   Teaching strategies via Pinecone vector search
│   │   ├── admin_agent.py       #   IEP reports, parent emails, summaries
│   │   └── predict_agent.py     #   Daily briefings, risk predictions
│   ├── api/
│   │   ├── routes/              # API endpoint handlers
│   │   │   ├── execute.py       #   POST /api/execute (main entry point)
│   │   │   ├── agent_info.py    #   GET /api/agent_info
│   │   │   ├── team_info.py     #   GET /api/team_info
│   │   │   ├── model_architecture.py  # GET /api/model_architecture
│   │   │   ├── students.py      #   GET /api/students
│   │   │   ├── schedule.py      #   GET /api/schedule/today
│   │   │   └── predictions.py   #   GET /api/predictions/today
│   │   └── schemas/             # Pydantic request/response models
│   ├── core/
│   │   ├── planner.py           # LLMPlanner — query decomposition into typed steps
│   │   ├── llm_client.py        # LLMod.ai client with budget tracking ($13 limit)
│   │   ├── step_tracker.py      # Request-scoped execution tracing (ContextVar)
│   │   ├── cache.py             # Two-tier response caching (Supabase + in-memory)
│   │   └── router.py            # Rule-based router (regex + keyword fallback)
│   ├── memory/
│   │   ├── supabase_client.py   # Short-term memory — PostgreSQL via Supabase
│   │   ├── pinecone_client.py   # Long-term memory — vector search via Pinecone
│   │   └── memory_manager.py    # Unified memory interface for all agents
│   ├── services/
│   │   ├── conversation_service.py  # Conversation lifecycle and message persistence
│   │   ├── context_resolver.py      # Student/topic extraction from chat history
│   │   ├── plan_executor.py         # Sequential agent dispatch with dependency chaining
│   │   ├── agent_executor.py        # Simple single-agent dispatch
│   │   └── presenter.py             # Voice transformation + multi-step merging
│   ├── utils/
│   │   └── prompts.py           # System prompt templates for all agents
│   ├── config.py                # Environment-based app configuration
│   └── main.py                  # FastAPI application entry point
├── static/                      # Frontend assets
│   ├── index.html               #   Chat UI with student sidebar and predictions
│   ├── app.js                   #   Frontend logic with step-trace accordion
│   ├── styles.css               #   Styling (colorful theme, back-to-school pattern)
│   ├── architecture.mmd         #   Architecture diagram source (Mermaid)
│   └── architecture.png         #   Rendered architecture diagram
├── data/                        # Seed data (students, schedules, teaching methods)
├── scrapers/                    # Knowledge base scrapers (ERIC, IRIS, Wikipedia)
├── scripts/                     # Database setup and seeding scripts
├── tests/                       # Test suites
│   ├── unit/                    #   Agent, service, and core component tests
│   ├── integration/             #   API endpoint and frontend tests
│   ├── e2e/                     #   End-to-end workflow tests
│   └── manual/                  #   Manual testing utilities
├── requirements.txt
├── render.yaml                  # Render deployment configuration
└── README.md
```

## Deployment

The application is deployed on **Render** with auto-deploy from the `main` branch:

- **Live URL**: https://co-teacher-nl17.onrender.com
