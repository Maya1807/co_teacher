"""
Manual test: Query "What strategies work for Alex?"

Run with:
    PYTHONPATH=/Users/maya/CursorProjects/co_teacher python tests/manual/test_alex_query.py
"""

import asyncio
import json


async def test_query():
    from app.agents.orchestrator import Orchestrator
    from app.memory.memory_manager import get_memory_manager
    from app.core.llm_client import get_llm_client
    from app.core.step_tracker import get_step_tracker

    # Initialize with correct parameter names
    memory = get_memory_manager()
    llm = get_llm_client()
    tracker = get_step_tracker()

    orchestrator = Orchestrator(
        llm_client=llm,
        memory_manager=memory,
        step_tracker=tracker
    )

    query = "What strategies work for Alex?"
    print("=" * 60)
    print(f"QUERY: {query}")
    print("=" * 60)

    # Execute
    result = await orchestrator.process({
        "prompt": query,
        "session_id": "test_session_123",
        "teacher_id": "test_teacher"
    })

    # Print response
    print()
    print("RESPONSE:")
    print("-" * 60)
    print(result.get("response", "No response"))
    print()

    # Print trace/steps
    print("TRACE (Steps):")
    print("-" * 60)
    steps = result.get("steps", [])
    for i, step in enumerate(steps):
        print(f"\nStep {i + 1}: {step.get('module', 'Unknown')}")
        prompt = step.get("prompt", {})
        response = step.get("response", {})
        print(f"  Prompt: {json.dumps(prompt, indent=4, default=str)[:800]}")
        print(f"  Response: {json.dumps(response, indent=4, default=str)[:800]}")

    # Print metadata
    print()
    print("METADATA:")
    print("-" * 60)
    print(f"  Agent used: {result.get('agent_used')}")
    print(f"  Router confidence: {result.get('router_confidence')}")
    if result.get("student_context"):
        print(f"  Student context: {json.dumps(result.get('student_context'), indent=4, default=str)[:500]}")

    return result


if __name__ == "__main__":
    asyncio.run(test_query())
