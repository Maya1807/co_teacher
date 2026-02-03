"""
Comprehensive manual tests for Co-Teacher system.

Tests:
1. Single query tests for different students/scenarios
2. Response quality checks (tone, content, personalization)
3. Trace structure verification
4. Multi-turn conversation tests (short-term memory)

Run with:
    PYTHONPATH=/Users/maya/CursorProjects/co_teacher python tests/manual/test_comprehensive.py

Or run specific test:
    PYTHONPATH=/Users/maya/CursorProjects/co_teacher python tests/manual/test_comprehensive.py --test student_queries
"""

import asyncio
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    response: Optional[str] = None
    trace: Optional[List[Dict]] = None


class CoTeacherTester:
    """Test harness for Co-Teacher system."""

    def __init__(self):
        from app.agents.orchestrator import Orchestrator
        from app.memory.memory_manager import get_memory_manager
        from app.core.llm_client import get_llm_client
        from app.core.step_tracker import get_step_tracker

        self.memory = get_memory_manager()
        self.llm = get_llm_client()
        self.tracker = get_step_tracker()
        self.orchestrator = Orchestrator(
            llm_client=self.llm,
            memory_manager=self.memory,
            step_tracker=self.tracker
        )
        self.results: List[TestResult] = []

    async def run_query(
        self,
        query: str,
        session_id: str = None,
        teacher_id: str = "test_teacher"
    ) -> Dict[str, Any]:
        """Run a query through the orchestrator."""
        # Generate unique session_id if not provided to avoid context bleed
        if session_id is None:
            import uuid
            session_id = f"test_{uuid.uuid4().hex[:8]}"

        result = await self.orchestrator.process({
            "prompt": query,
            "session_id": session_id,
            "teacher_id": teacher_id
        }, context={"teacher_id": teacher_id})
        return result

    def check_response_quality(
        self,
        response: str,
        must_contain: List[str] = None,
        must_not_contain: List[str] = None,
        min_length: int = 100
    ) -> tuple[bool, str]:
        """Check response quality."""
        issues = []

        if len(response) < min_length:
            issues.append(f"Response too short ({len(response)} chars, expected {min_length}+)")

        if must_contain:
            for term in must_contain:
                if term.lower() not in response.lower():
                    issues.append(f"Missing expected term: '{term}'")

        if must_not_contain:
            for term in must_not_contain:
                if term.lower() in response.lower():
                    issues.append(f"Contains unwanted term: '{term}'")

        return (len(issues) == 0, "; ".join(issues) if issues else "OK")

    def check_trace_structure(
        self,
        steps: List[Dict],
        expected_modules: List[str]
    ) -> tuple[bool, str]:
        """Verify trace contains expected modules."""
        actual_modules = [s.get("module") for s in steps]
        missing = [m for m in expected_modules if m not in actual_modules]

        if missing:
            return (False, f"Missing modules: {missing}. Got: {actual_modules}")
        return (True, f"All expected modules present: {actual_modules}")

    # ==================== Test: Student-Specific Queries ====================

    async def test_student_queries(self):
        """Test queries about different students."""
        print("\n" + "=" * 60)
        print("TEST: Student-Specific Queries")
        print("=" * 60)

        test_cases = [
            {
                "name": "Alex (ADHD) - strategies",
                "prompt": "What strategies work for Alex?",
                "expected_modules": ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT"],
                "must_contain": ["Alex", "ADHD"],
                # Note: "timed tests" may be mentioned as something to AVOID, which is correct
            },
            {
                "name": "Jordan (Autism) - triggers",
                "prompt": "Tell me about Jordan's triggers",
                "expected_modules": ["ORCHESTRATOR", "STUDENT_AGENT"],
                "must_contain": ["Jordan"],
            },
            {
                "name": "Maya (Dyslexia) - reading help",
                "prompt": "How can I help Maya with reading?",
                "expected_modules": ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT"],
                "must_contain": ["Maya"],
            },
            {
                "name": "Unknown student",
                "prompt": "What works for a student named Zzzzzz?",
                "expected_modules": ["ORCHESTRATOR", "STUDENT_AGENT"],
                # Should handle gracefully
            },
        ]

        for tc in test_cases:
            print(f"\n--- {tc['name']} ---")
            print(f"Query: {tc['query']}")

            result = await self.run_query(tc["query"])
            response = result.get("response", "")
            steps = result.get("steps", [])

            # Check trace
            trace_ok, trace_msg = self.check_trace_structure(
                steps, tc["expected_modules"]
            )

            # Check response
            resp_ok, resp_msg = self.check_response_quality(
                response,
                must_contain=tc.get("must_contain"),
                must_not_contain=tc.get("must_not_contain")
            )

            passed = trace_ok and resp_ok
            details = f"Trace: {trace_msg} | Response: {resp_msg}"

            print(f"Response preview: {response[:200]}...")
            print(f"Result: {'PASS' if passed else 'FAIL'} - {details}")

            self.results.append(TestResult(
                name=f"student_query_{tc['name']}",
                passed=passed,
                details=details,
                response=response,
                trace=steps
            ))

    # ==================== Test: General RAG Queries ====================

    async def test_rag_queries(self):
        """Test general teaching strategy queries (no specific student)."""
        print("\n" + "=" * 60)
        print("TEST: General RAG Queries")
        print("=" * 60)

        test_cases = [
            {
                "name": "ADHD strategies general",
                "prompt": "What are effective strategies for students with ADHD?",
                "expected_modules": ["ORCHESTRATOR", "RAG_AGENT"],
                "must_contain": ["ADHD"],
            },
            {
                "name": "Autism classroom management",
                "prompt": "How do I manage a classroom with autistic students?",
                "expected_modules": ["ORCHESTRATOR", "RAG_AGENT"],
            },
            {
                "name": "Sensory breaks",
                "prompt": "When should I use sensory breaks?",
                "expected_modules": ["ORCHESTRATOR", "RAG_AGENT"],
            },
        ]

        for tc in test_cases:
            print(f"\n--- {tc['name']} ---")
            print(f"Query: {tc['query']}")

            result = await self.run_query(tc["query"])
            response = result.get("response", "")
            steps = result.get("steps", [])

            trace_ok, trace_msg = self.check_trace_structure(
                steps, tc["expected_modules"]
            )
            resp_ok, resp_msg = self.check_response_quality(
                response,
                must_contain=tc.get("must_contain")
            )

            passed = trace_ok and resp_ok
            details = f"Trace: {trace_msg} | Response: {resp_msg}"

            print(f"Response preview: {response[:200]}...")
            print(f"Result: {'PASS' if passed else 'FAIL'} - {details}")

            self.results.append(TestResult(
                name=f"rag_query_{tc['name']}",
                passed=passed,
                details=details,
                response=response,
                trace=steps
            ))

    # ==================== Test: Admin Document Queries ====================

    async def test_admin_queries(self):
        """Test administrative document generation."""
        print("\n" + "=" * 60)
        print("TEST: Admin Document Queries")
        print("=" * 60)

        test_cases = [
            {
                "name": "IEP draft for Alex",
                "prompt": "Draft an IEP update for Alex",
                "expected_modules": ["ORCHESTRATOR"],  # Should route to ADMIN_AGENT
                "must_contain": ["Alex"],
            },
            {
                "name": "Parent email",
                "prompt": "Help me write an email to Jordan's parents about his progress",
                "expected_modules": ["ORCHESTRATOR"],
            },
            {
                "name": "Incident report",
                "prompt": "I need to write an incident report for today",
                "expected_modules": ["ORCHESTRATOR"],
            },
        ]

        for tc in test_cases:
            print(f"\n--- {tc['name']} ---")
            print(f"Query: {tc['query']}")

            result = await self.run_query(tc["query"])
            response = result.get("response", "")
            steps = result.get("steps", [])

            # For admin queries, just check we got a response
            resp_ok = len(response) > 50
            resp_msg = "OK" if resp_ok else "Response too short"

            print(f"Response preview: {response[:200]}...")
            print(f"Agents used: {result.get('agents_used', [])}")
            print(f"Result: {'PASS' if resp_ok else 'FAIL'} - {resp_msg}")

            self.results.append(TestResult(
                name=f"admin_query_{tc['name']}",
                passed=resp_ok,
                details=resp_msg,
                response=response,
                trace=steps
            ))

    # ==================== Test: Response Tone ====================

    async def test_response_tone(self):
        """Test that responses have appropriate professional but friendly tone."""
        print("\n" + "=" * 60)
        print("TEST: Response Tone")
        print("=" * 60)

        # Tone indicators - expanded list
        professional_markers = [
            "strategy", "recommend", "consider", "approach",
            "suggest", "effective", "help", "support", "benefit",
            "works", "method", "technique", "practice", "tip"
        ]
        overly_formal_markers = ["hereby", "pursuant", "aforementioned", "henceforth"]
        friendly_markers = ["you", "try", "might", "let's", "here's", "can", "could", "would"]

        result = await self.run_query("What strategies work for Alex?")
        response = result.get("response", "").lower()

        # Check for professional but friendly tone
        has_professional = any(m in response for m in professional_markers)
        has_overly_formal = any(m in response for m in overly_formal_markers)
        has_friendly = any(m in response for m in friendly_markers)

        issues = []
        if not has_professional:
            issues.append("Missing professional language markers")
        if has_overly_formal:
            issues.append("Contains overly formal language")
        if not has_friendly:
            issues.append("Missing friendly/conversational markers")

        passed = has_professional and not has_overly_formal and has_friendly
        details = "; ".join(issues) if issues else "Good professional-friendly balance"

        print(f"Professional markers: {has_professional}")
        print(f"Overly formal: {has_overly_formal}")
        print(f"Friendly markers: {has_friendly}")
        print(f"Result: {'PASS' if passed else 'FAIL'} - {details}")

        self.results.append(TestResult(
            name="response_tone",
            passed=passed,
            details=details,
            response=result.get("response")
        ))

    # ==================== Test: Multi-Turn Conversation ====================

    async def test_conversation_memory(self):
        """Test that conversation context is maintained across turns."""
        print("\n" + "=" * 60)
        print("TEST: Multi-Turn Conversation (Short-Term Memory)")
        print("=" * 60)

        session_id = "test_conversation_123"

        # Turn 1: Ask about a student
        print("\n--- Turn 1 ---")
        query1 = "Tell me about Alex's profile"
        print(f"Query: {query1}")
        result1 = await self.run_query(query1, session_id=session_id)
        print(f"Response: {result1.get('response', '')[:200]}...")

        # Turn 2: Follow-up without naming the student
        print("\n--- Turn 2 ---")
        query2 = "What triggers should I watch out for?"
        print(f"Query: {query2}")
        result2 = await self.run_query(query2, session_id=session_id)
        response2 = result2.get("response", "")
        print(f"Response: {response2[:200]}...")

        # Check if the system remembered we were talking about Alex
        mentions_alex = "alex" in response2.lower()
        mentions_adhd = "adhd" in response2.lower()

        # Also check if conversation was stored
        conversation = await self.memory.supabase.get_conversation_by_session(session_id)
        has_conversation = conversation is not None

        print(f"\nMemory check:")
        print(f"  Mentions Alex in follow-up: {mentions_alex}")
        print(f"  Mentions ADHD in follow-up: {mentions_adhd}")
        print(f"  Conversation stored: {has_conversation}")

        # Turn 3: Another follow-up
        print("\n--- Turn 3 ---")
        query3 = "What about successful methods that have worked before?"
        print(f"Query: {query3}")
        result3 = await self.run_query(query3, session_id=session_id)
        response3 = result3.get("response", "")
        print(f"Response: {response3[:200]}...")

        # Check conversation history
        if has_conversation:
            messages = await self.memory.get_conversation_history(
                conversation["id"], limit=10
            )
            print(f"  Messages in conversation: {len(messages)}")
        else:
            messages = []
            print("  No conversation history stored")

        # Evaluate
        # Note: Currently the orchestrator may not be using conversation history
        # This test will reveal if that feature is working
        passed = mentions_alex or mentions_adhd  # Relaxed - may need context feature
        details = f"Follow-up context: Alex={mentions_alex}, ADHD={mentions_adhd}, Conv stored={has_conversation}, Msgs={len(messages)}"

        print(f"\nResult: {'PASS' if passed else 'FAIL'} - {details}")
        print("NOTE: If FAIL, conversation history feature may need implementation")

        self.results.append(TestResult(
            name="conversation_memory",
            passed=passed,
            details=details
        ))

    # ==================== Test: Trace Detail Verification ====================

    async def test_trace_details(self):
        """Verify trace contains useful debugging information."""
        print("\n" + "=" * 60)
        print("TEST: Trace Detail Verification")
        print("=" * 60)

        result = await self.run_query("What strategies work for Alex?")
        steps = result.get("steps", [])

        print(f"Total steps: {len(steps)}")

        issues = []

        # Check each step has required fields
        for i, step in enumerate(steps):
            module = step.get("module")
            prompt = step.get("prompt", {})
            response = step.get("response", {})

            print(f"\nStep {i+1}: {module}")
            print(f"  Prompt keys: {list(prompt.keys())}")
            print(f"  Response keys: {list(response.keys())}")

            if not module:
                issues.append(f"Step {i+1} missing module name")
            if not prompt:
                issues.append(f"Step {i+1} missing prompt")
            if not response:
                issues.append(f"Step {i+1} missing response")

        # Check specific expected data
        rag_step = next((s for s in steps if s.get("module") == "RAG_AGENT"), None)
        if rag_step:
            methods_found = rag_step.get("response", {}).get("methods_found", 0)
            method_names = rag_step.get("response", {}).get("method_names", [])
            print(f"\nRAG Agent details:")
            print(f"  Methods found: {methods_found}")
            print(f"  Method names (first 3): {method_names}")

            if methods_found == 0:
                issues.append("RAG returned 0 methods")
            if method_names and all(n is None for n in method_names):
                issues.append("RAG method names are all null")

        student_step = next((s for s in steps if s.get("module") == "STUDENT_AGENT"), None)
        if student_step:
            found = student_step.get("response", {}).get("found", False)
            student_id = student_step.get("response", {}).get("student_id")
            print(f"\nStudent Agent details:")
            print(f"  Found: {found}")
            print(f"  Student ID: {student_id}")

            if not found:
                issues.append("Student not found")
            if found and not student_id:
                issues.append("Student found but no ID")

        passed = len(issues) == 0
        details = "; ".join(issues) if issues else "All trace details present and valid"

        print(f"\nResult: {'PASS' if passed else 'FAIL'} - {details}")

        self.results.append(TestResult(
            name="trace_details",
            passed=passed,
            details=details,
            trace=steps
        ))

    # ==================== Test: Router Confidence ====================

    async def test_router_confidence(self):
        """Test that router confidence is appropriate for different queries."""
        print("\n" + "=" * 60)
        print("TEST: Router Confidence")
        print("=" * 60)

        test_cases = [
            {
                "prompt": "What strategies work for Alex?",
                "expected_min_confidence": 0.7,
                "description": "Clear student + strategy query"
            },
            {
                "prompt": "Tell me about ADHD",
                "expected_min_confidence": 0.5,
                "description": "General topic query"
            },
            {
                "prompt": "Help",
                "expected_min_confidence": 0.0,  # Ambiguous
                "description": "Ambiguous single word"
            },
        ]

        for tc in test_cases:
            print(f"\n--- {tc['description']} ---")
            print(f"Query: {tc['query']}")

            result = await self.run_query(tc["query"])
            confidence = result.get("router_confidence", 0)
            routing = result.get("routing", {})

            print(f"Router confidence: {confidence}")
            print(f"Routed to: {routing.get('agents', [])}")

            passed = confidence >= tc["expected_min_confidence"]
            details = f"Confidence {confidence} (expected >= {tc['expected_min_confidence']})"

            print(f"Result: {'PASS' if passed else 'FAIL'} - {details}")

            self.results.append(TestResult(
                name=f"router_confidence_{tc['description']}",
                passed=passed,
                details=details
            ))

    # ==================== Run All Tests ====================

    async def run_all_tests(self):
        """Run all test suites."""
        await self.test_student_queries()
        await self.test_rag_queries()
        await self.test_admin_queries()
        await self.test_response_tone()
        await self.test_conversation_memory()
        await self.test_trace_details()
        await self.test_router_confidence()

        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        print(f"\nTotal: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        print("-" * 60)

        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            print(f"[{status}] {r.name}")
            if not r.passed:
                print(f"       {r.details}")

        print("\n" + "=" * 60)
        if failed == 0:
            print("ALL TESTS PASSED!")
        else:
            print(f"{failed} TEST(S) FAILED - see details above")
        print("=" * 60)


async def main():
    """Main entry point."""
    tester = CoTeacherTester()

    # Check for specific test argument
    if len(sys.argv) > 2 and sys.argv[1] == "--test":
        test_name = sys.argv[2]
        test_method = getattr(tester, f"test_{test_name}", None)
        if test_method:
            await test_method()
            tester.print_summary()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: student_queries, rag_queries, admin_queries, response_tone, conversation_memory, trace_details, router_confidence")
    else:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
