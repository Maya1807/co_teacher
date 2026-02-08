"""
Manual test: Send a query through the API (like the UI does) and print steps + response.

Run directly or via your IDE debugger (set breakpoints anywhere):
    python tests/manual/test_query.py
"""

import asyncio
import json
import os
import sys

# Ensure the project root is on sys.path so "app" is importable
# regardless of how the script is launched (terminal, IDE debugger, etc.)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))




def print_separator(title: str = "", char: str = "=", width: int = 70):
    if title:
        print(f"\n{char * 3} {title} {char * (width - len(title) - 5)}")
    else:
        print(char * width)


def print_steps(steps: list):
    if not steps:
        print("  (no steps recorded)")
        return

    for i, step in enumerate(steps, 1):
        module = step.get("module", "???")
        prompt = step.get("prompt", {})
        response = step.get("response", {})

        print(f"\n  Step {i}: [{module}]")
        print(f"    Prompt:   {json.dumps(prompt, indent=6, default=str)[:600]}")
        print(f"    Response: {json.dumps(response, indent=6, default=str)[:600]}")


async def run(query: str):
    # Import here so startup errors are visible
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    print_separator("QUERY")
    print(f"  {query}")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/execute",
            json={"prompt": query},
        )

    data = resp.json()

    # Status
    print_separator("STATUS")
    print(f"  HTTP {resp.status_code}  |  status={data.get('status')}")
    if data.get("error"):
        print(f"  ERROR: {data['error']}")

    # Steps
    print_separator("STEPS")
    print_steps(data.get("steps", []))

    # Response
    print_separator("RESPONSE")
    print(f"  {data.get('response', '(empty)')}")

    # Extra metadata
    if data.get("student_updated"):
        print_separator("METADATA")
        print(f"  student_updated: {data['student_updated']}")

    print_separator()
    return data


if __name__ == "__main__":
    # ── Change your query here ──────────────────────────────────────────
    query = "What strategies work for Alex?"
    # ────────────────────────────────────────────────────────────────────
    asyncio.run(run(query))
