"""
End-to-End Tests for Co-Teacher System.
Tests complete user flows from API request to response.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestCompleteUserFlow:
    """
    Tests simulating complete user journeys through the system.
    
    Note: These tests verify the API structure and response format.
    When external services (Pinecone, LLM) are unavailable, they verify
    proper error handling. Full E2E tests require network access.
    """

    @pytest.mark.asyncio
    async def test_basic_query_flow(self):
        """Test: User asks a simple question and gets a response or handled error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: User visits homepage
            response = await client.get("/")
            assert response.status_code == 200
            assert "Co-Teacher" in response.text

            # Step 2: User loads student list
            response = await client.get("/api/students")
            assert response.status_code == 200
            data = response.json()
            assert "students" in data

            # Step 3: User sends a query
            response = await client.post(
                "/api/execute",
                json={"prompt": "What strategies work for ADHD students?"}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure (may be ok or error depending on services)
            assert "status" in data
            assert "response" in data
            assert "steps" in data
            assert data["status"] in ["ok", "error"]

    @pytest.mark.asyncio
    async def test_student_specific_query_flow(self):
        """Test: User asks about a specific student."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={
                    "prompt": "What are Alex's triggers?",
                    "student_name": "Alex Johnson"
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "status" in data
            assert "response" in data
            assert data["status"] in ["ok", "error"]

    @pytest.mark.asyncio
    async def test_crisis_support_flow(self):
        """Test: Teacher requests crisis support."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={
                    "prompt": "Jordan is having a meltdown right now. What should I do?",
                    "student_name": "Jordan Smith"
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "status" in data
            assert data["status"] in ["ok", "error"]

    @pytest.mark.asyncio
    async def test_iep_draft_flow(self):
        """Test: Teacher requests IEP document draft."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={
                    "prompt": "Draft an IEP progress report for Taylor Williams"
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "status" in data
            assert data["status"] in ["ok", "error"]

    @pytest.mark.asyncio
    async def test_teaching_method_recommendation_flow(self):
        """Test: Teacher asks for teaching method recommendations."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={
                    "prompt": "What evidence-based methods work for sensory processing disorders?"
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "status" in data
            assert data["status"] in ["ok", "error"]


class TestStudentsAPIFlow:
    """Tests for the students API endpoints."""

    @pytest.mark.asyncio
    async def test_list_all_students(self):
        """Test listing all students."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/students")
            assert response.status_code == 200
            data = response.json()
            
            assert "students" in data
            assert "total" in data
            assert data["total"] > 0
            
            # Verify student structure
            for student in data["students"]:
                assert "student_id" in student
                assert "name" in student
                assert "grade" in student
                assert "disability_type" in student

    @pytest.mark.asyncio
    async def test_filter_students_by_disability(self):
        """Test filtering students by disability type."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/students?disability_type=autism")
            assert response.status_code == 200
            data = response.json()
            
            # All returned students should have autism
            for student in data["students"]:
                assert student["disability_type"] == "autism"

    @pytest.mark.asyncio
    async def test_get_student_by_id(self):
        """Test getting a specific student by ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/students/STU001")
            assert response.status_code == 200
            data = response.json()
            
            assert data["student_id"] == "STU001"
            assert "name" in data
            assert "triggers" in data
            assert "successful_methods" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_student(self):
        """Test getting a student that doesn't exist."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/students/NONEXISTENT")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_disability_types(self):
        """Test getting list of disability types."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/disability-types")
            assert response.status_code == 200
            data = response.json()
            
            assert "disability_types" in data
            assert "count" in data
            assert data["count"] > 0


class TestAPIEndpointsIntegration:
    """Integration tests for all API endpoints working together."""

    @pytest.mark.asyncio
    async def test_all_required_endpoints_available(self):
        """Verify all required course endpoints are available."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Required endpoints
            endpoints = [
                ("GET", "/api/team_info"),
                ("GET", "/api/agent_info"),
                ("GET", "/api/model_architecture"),
                ("POST", "/api/execute"),
            ]
            
            for method, endpoint in endpoints:
                if method == "GET":
                    response = await client.get(endpoint)
                else:
                    response = await client.post(endpoint, json={"prompt": "test"})
                
                assert response.status_code in [200, 422], f"Endpoint {endpoint} failed with {response.status_code}"

    @pytest.mark.asyncio
    async def test_team_info_has_all_members(self):
        """Verify team info contains all team members."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/team_info")
            data = response.json()
            
            assert data["group_batch_order_number"] == "batch_1_order_9"
            assert data["team_name"] == "avi_yehoraz_maya"
            assert len(data["students"]) == 3
            
            # Verify all team members
            names = [s["name"] for s in data["students"]]
            assert "Avi Simkin" in names
            assert "Yehoraz Ben-Yehuda" in names
            assert "Maya Meirovich" in names

    @pytest.mark.asyncio
    async def test_agent_info_describes_all_agents(self):
        """Verify agent info describes all agents in the system."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/agent_info")
            data = response.json()

            # Required fields per Course Project spec
            assert "description" in data
            assert "purpose" in data
            assert "prompt_template" in data
            assert "template" in data["prompt_template"]
            assert "prompt_examples" in data

            # Description should mention all agents
            description = data["description"]
            assert "STUDENT_AGENT" in description
            assert "RAG_AGENT" in description
            assert "ADMIN_AGENT" in description
            assert "PREDICT_AGENT" in description

    @pytest.mark.asyncio
    async def test_execute_returns_traced_steps(self):
        """Verify execute endpoint returns step traces."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={"prompt": "What strategies work for visual learners?"}
            )
            data = response.json()
            
            assert "steps" in data
            assert isinstance(data["steps"], list)
            
            # Each step should have module, prompt, response
            for step in data["steps"]:
                assert "module" in step
                assert "prompt" in step
                assert "response" in step


class TestFrontendBackendIntegration:
    """Tests verifying frontend and backend work together."""

    @pytest.mark.asyncio
    async def test_frontend_loads_students_from_api(self):
        """Verify frontend student dropdown is populated from API."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Get students from API
            api_response = await client.get("/api/students")
            api_students = api_response.json()["students"]
            
            # Frontend should have JavaScript that calls this endpoint
            frontend_response = await client.get("/static/app.js")
            js_content = frontend_response.text
            
            assert "/api/students" in js_content
            assert "loadStudents" in js_content

    @pytest.mark.asyncio
    async def test_frontend_sends_correct_request_format(self):
        """Verify frontend sends requests in the correct format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Check that frontend uses 'prompt' (the correct field name)
            js_response = await client.get("/static/app.js")
            js_content = js_response.text

            assert "prompt:" in js_content or '"prompt":' in js_content
            # The old bug was using 'query'
            assert 'body: JSON.stringify({ query })' not in js_content


class TestErrorHandling:
    """Tests for error handling across the system."""

    @pytest.mark.asyncio
    async def test_empty_query_handled_gracefully(self):
        """Test that empty queries are handled gracefully."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={"prompt": ""}
            )
            # Should return 422 (validation) or error response
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_missing_query_field_returns_422(self):
        """Test that missing query field returns validation error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={}
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_json_handled(self):
        """Test that invalid JSON is handled."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                content="not valid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422


class TestDataIntegrity:
    """Tests for data integrity and consistency."""

    @pytest.mark.asyncio
    async def test_student_data_matches_json_file(self):
        """Verify API returns data matching the JSON file."""
        import json
        from pathlib import Path
        
        # Load from JSON file
        data_file = Path(__file__).parent.parent.parent / "data" / "sample_students.json"
        with open(data_file) as f:
            file_data = json.load(f)
        
        file_students = {s["student_id"]: s for s in file_data["students"]}
        
        # Load from API
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/students")
            api_students = response.json()["students"]
        
        # Verify counts match
        assert len(api_students) == len(file_data["students"])
        
        # Verify each student's basic info matches
        for api_student in api_students:
            file_student = file_students[api_student["student_id"]]
            assert api_student["name"] == file_student["name"]
            assert api_student["grade"] == file_student["grade"]
            assert api_student["disability_type"] == file_student["disability_type"]

    @pytest.mark.asyncio
    async def test_student_detail_has_all_fields(self):
        """Verify student detail endpoint returns all expected fields."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/students/STU001")
            student = response.json()
            
            required_fields = [
                "student_id", "name", "grade", "disability_type",
                "learning_style", "triggers", "successful_methods",
                "failed_methods"
            ]
            
            for field in required_fields:
                assert field in student, f"Missing field: {field}"


class TestMultiAgentFlow:
    """Tests for complex multi-agent query scenarios."""

    @pytest.mark.asyncio
    async def test_jordan_allergy_update_and_lesson_plan(self):
        """
        Test multi-agent query: Update Jordan's profile with nut allergy
        AND create a lesson plan about allergies for the class.

        Expected agents in steps:
        - STUDENT_AGENT: Update Jordan's profile with nut allergy info
        - RAG_AGENT: Retrieve teaching strategies for explaining allergies (optional)
        - ORCHESTRATOR: Coordinate responses and generate final output
        """
        query = (
            "I want your help with Jordan. He started having allergies for nuts. "
            "please add this to his profile. also, please make a lesson plan on "
            "allergies to explain this to the kids."
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/execute",
                json={"prompt": query}
            )

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert "status" in data
            assert "response" in data
            assert "steps" in data

            # If services are available, verify agent routing through steps
            if data["status"] == "ok":
                # Verify steps were traced
                steps = data.get("steps", [])
                assert len(steps) > 0, "Should have traced steps"

                # Check which modules appear in steps
                step_modules = [step.get("module") for step in steps]

                # STUDENT_AGENT should be involved (profile query/update)
                assert "STUDENT_AGENT" in step_modules, \
                    f"STUDENT_AGENT should appear in steps for profile operations, got: {step_modules}"

                # ORCHESTRATOR should coordinate
                assert "ORCHESTRATOR" in step_modules, \
                    f"ORCHESTRATOR should appear in steps, got: {step_modules}"

                # Verify response mentions allergies (the topic was addressed)
                response_text = data.get("response", "").lower()
                assert "allergy" in response_text or "allergies" in response_text, \
                    f"Response should mention allergies: {response_text[:300]}"

                # Print for debugging
                print(f"\n[TEST] Modules used: {step_modules}")
                print(f"[TEST] Response preview: {data.get('response', '')[:200]}...")


class TestPerformance:
    """Basic performance and response time tests."""

    @pytest.mark.asyncio
    async def test_students_api_responds_quickly(self):
        """Verify students API responds in reasonable time."""
        import time
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.time()
            response = await client.get("/api/students")
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 1.0, f"Students API took {elapsed:.2f}s, expected < 1s"

    @pytest.mark.asyncio
    async def test_static_files_served_quickly(self):
        """Verify static files are served quickly."""
        import time
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = ["/", "/static/styles.css", "/static/app.js"]
            
            for file_path in files:
                start = time.time()
                response = await client.get(file_path)
                elapsed = time.time() - start
                
                assert response.status_code == 200
                assert elapsed < 0.5, f"{file_path} took {elapsed:.2f}s, expected < 0.5s"
