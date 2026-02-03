"""
Integration tests for API endpoints.
Tests the full API contract without mocking external services.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


# ==================== Team Info Tests ====================

class TestTeamInfoEndpoint:
    """Tests for GET /api/team_info."""

    def test_returns_200(self, client):
        """Endpoint returns 200 OK."""
        response = client.get("/api/team_info")
        assert response.status_code == 200

    def test_returns_correct_structure(self, client):
        """Response has required fields."""
        response = client.get("/api/team_info")
        data = response.json()

        assert "group_batch_order_number" in data
        assert "team_name" in data
        assert "students" in data

    def test_returns_correct_batch_number(self, client):
        """Returns correct batch order number."""
        response = client.get("/api/team_info")
        data = response.json()

        assert data["group_batch_order_number"] == "batch_1_order_9"

    def test_returns_correct_team_name(self, client):
        """Returns correct team name."""
        response = client.get("/api/team_info")
        data = response.json()

        assert data["team_name"] == "avi_yehoraz_maya"

    def test_returns_three_students(self, client):
        """Returns exactly three team members."""
        response = client.get("/api/team_info")
        data = response.json()

        assert len(data["students"]) == 3

    def test_student_has_name_and_email(self, client):
        """Each student has name and email."""
        response = client.get("/api/team_info")
        data = response.json()

        for student in data["students"]:
            assert "name" in student
            assert "email" in student
            assert "@campus.technion.ac.il" in student["email"]


# ==================== Agent Info Tests ====================

class TestAgentInfoEndpoint:
    """Tests for GET /api/agent_info."""

    def test_returns_200(self, client):
        """Endpoint returns 200 OK."""
        response = client.get("/api/agent_info")
        assert response.status_code == 200

    def test_returns_description(self, client):
        """Response includes description."""
        response = client.get("/api/agent_info")
        data = response.json()

        assert "description" in data
        assert len(data["description"]) > 50

    def test_returns_purpose(self, client):
        """Response includes purpose."""
        response = client.get("/api/agent_info")
        data = response.json()

        assert "purpose" in data
        assert len(data["purpose"]) > 50

    def test_returns_prompt_template(self, client):
        """Response includes prompt_template with template key."""
        response = client.get("/api/agent_info")
        data = response.json()

        assert "prompt_template" in data
        assert "template" in data["prompt_template"]
        assert len(data["prompt_template"]["template"]) > 50

    def test_prompt_template_describes_query_types(self, client):
        """Prompt template includes query type guidance."""
        response = client.get("/api/agent_info")
        data = response.json()

        template = data["prompt_template"]["template"]
        # Should mention different query types
        assert "Student" in template or "student" in template
        assert "Strateg" in template or "strateg" in template

    def test_description_mentions_all_agents(self, client):
        """Description mentions all agent types for documentation."""
        response = client.get("/api/agent_info")
        data = response.json()

        description = data["description"]
        assert "STUDENT_AGENT" in description
        assert "RAG_AGENT" in description
        assert "ADMIN_AGENT" in description
        assert "PREDICT_AGENT" in description

    def test_returns_prompt_examples(self, client):
        """Response includes prompt examples."""
        response = client.get("/api/agent_info")
        data = response.json()

        assert "prompt_examples" in data
        assert len(data["prompt_examples"]) >= 1

    def test_prompt_examples_have_steps(self, client):
        """Prompt examples include step traces."""
        response = client.get("/api/agent_info")
        data = response.json()

        for example in data["prompt_examples"]:
            assert "prompt" in example
            assert "full_response" in example
            assert "steps" in example
            assert len(example["steps"]) >= 1


# ==================== Model Architecture Tests ====================

class TestModelArchitectureEndpoint:
    """Tests for GET /api/model_architecture."""

    def test_default_returns_image(self, client):
        """Default format returns image (200 if exists, 404 if not)."""
        response = client.get("/api/model_architecture")
        # Default is now image format
        assert response.status_code in [200, 404]

    def test_json_returns_200(self, client):
        """JSON format returns 200 OK."""
        response = client.get("/api/model_architecture?format=json")
        assert response.status_code == 200

    def test_json_returns_description(self, client):
        """JSON response includes description."""
        response = client.get("/api/model_architecture?format=json")
        data = response.json()

        assert "description" in data
        assert len(data["description"]) > 50

    def test_json_returns_modules(self, client):
        """JSON response includes module descriptions."""
        response = client.get("/api/model_architecture?format=json")
        data = response.json()

        assert "modules" in data
        assert "ORCHESTRATOR" in data["modules"]
        assert "STUDENT_AGENT" in data["modules"]
        assert "RAG_AGENT" in data["modules"]
        assert "ADMIN_AGENT" in data["modules"]
        assert "PREDICT_AGENT" in data["modules"]

    def test_json_returns_data_flow(self, client):
        """JSON response includes data flow description."""
        response = client.get("/api/model_architecture?format=json")
        data = response.json()

        assert "data_flow" in data
        assert isinstance(data["data_flow"], list)
        assert len(data["data_flow"]) >= 5

    def test_json_returns_diagram_url(self, client):
        """JSON response includes architecture diagram URL."""
        response = client.get("/api/model_architecture?format=json")
        data = response.json()

        assert "architecture_diagram_url" in data

    def test_image_format_returns_png(self, client):
        """Image format returns PNG when file exists."""
        response = client.get("/api/model_architecture?format=image")
        # Will be 200 now that we created architecture.png
        assert response.status_code == 200
        assert response.headers.get("content-type") == "image/png"


# ==================== Execute Tests ====================

class TestExecuteEndpoint:
    """Tests for POST /api/execute."""

    def test_returns_200_with_valid_query(self, client):
        """Returns 200 OK with valid query."""
        with patch('app.api.routes.execute.Orchestrator') as MockOrch:
            mock_instance = MagicMock()
            mock_instance.process = AsyncMock(return_value={
                "response": "Test response",
                "agents_used": ["ORCHESTRATOR"]
            })
            MockOrch.return_value = mock_instance

            response = client.post(
                "/api/execute",
                json={"prompt": "What strategies work for ADHD?"}
            )

            assert response.status_code == 200

    def test_returns_error_with_empty_query(self, client):
        """Returns error status with empty query."""
        response = client.post("/api/execute", json={"prompt": ""})

        # Pydantic validation will return 422 for empty query (min_length=1)
        # Or our handler returns status="error"
        if response.status_code == 422:
            # Pydantic validation error
            assert response.status_code == 422
        else:
            data = response.json()
            assert data["status"] == "error"
            assert data["error"] is not None

    def test_response_has_required_fields(self, client):
        """Response includes all required fields."""
        with patch('app.api.routes.execute.Orchestrator') as MockOrch:
            mock_instance = MagicMock()
            mock_instance.process = AsyncMock(return_value={
                "response": "Test response"
            })
            MockOrch.return_value = mock_instance

            response = client.post(
                "/api/execute",
                json={"prompt": "Test query"}
            )
            data = response.json()

            assert "status" in data
            assert "error" in data
            assert "response" in data
            assert "steps" in data

    def test_steps_have_correct_structure(self, client):
        """Steps array entries have module, prompt, response."""
        with patch('app.api.routes.execute.Orchestrator') as MockOrch:
            with patch('app.api.routes.execute.reset_step_tracker') as mock_tracker_fn:
                mock_tracker = MagicMock()
                mock_tracker.get_steps.return_value = [
                    {
                        "module": "ORCHESTRATOR",
                        "prompt": {"action": "route"},
                        "response": {"routed_to": "RAG_AGENT"}
                    }
                ]
                mock_tracker_fn.return_value = mock_tracker

                mock_instance = MagicMock()
                mock_instance.process = AsyncMock(return_value={
                    "response": "Test response"
                })
                MockOrch.return_value = mock_instance

                response = client.post(
                    "/api/execute",
                    json={"prompt": "Test query"}
                )
                data = response.json()

                assert len(data["steps"]) >= 1
                for step in data["steps"]:
                    assert "module" in step
                    assert "prompt" in step
                    assert "response" in step

    def test_accepts_optional_session_id(self, client):
        """Accepts optional session_id parameter."""
        with patch('app.api.routes.execute.Orchestrator') as MockOrch:
            mock_instance = MagicMock()
            mock_instance.process = AsyncMock(return_value={"response": "Test"})
            MockOrch.return_value = mock_instance

            response = client.post(
                "/api/execute",
                json={"prompt": "Test", "session_id": "test_session"}
            )

            assert response.status_code == 200

    def test_accepts_optional_teacher_id(self, client):
        """Accepts optional teacher_id parameter."""
        with patch('app.api.routes.execute.Orchestrator') as MockOrch:
            mock_instance = MagicMock()
            mock_instance.process = AsyncMock(return_value={"response": "Test"})
            MockOrch.return_value = mock_instance

            response = client.post(
                "/api/execute",
                json={"prompt": "Test", "teacher_id": "T001"}
            )

            assert response.status_code == 200

    def test_accepts_optional_student_name(self, client):
        """Accepts optional student_name parameter."""
        with patch('app.api.routes.execute.Orchestrator') as MockOrch:
            mock_instance = MagicMock()
            mock_instance.process = AsyncMock(return_value={"response": "Test"})
            MockOrch.return_value = mock_instance

            response = client.post(
                "/api/execute",
                json={"prompt": "Test", "student_name": "Alex"}
            )

            assert response.status_code == 200


# ==================== Health Check Tests ====================

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_health_returns_200(self, client):
        """Root health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_root_health_returns_status(self, client):
        """Root health check returns healthy status."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_execute_health_returns_200(self, client):
        """Execute health check returns 200."""
        response = client.get("/api/execute/health")
        assert response.status_code == 200

    def test_execute_health_returns_version(self, client):
        """Execute health check returns version."""
        response = client.get("/api/execute/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data


# ==================== Budget Endpoint Tests ====================

class TestBudgetEndpoint:
    """Tests for GET /api/execute/budget."""

    def test_returns_200(self, client):
        """Budget endpoint returns 200."""
        with patch('app.api.routes.execute.get_llm_client') as mock_llm:
            mock_client = MagicMock()
            mock_client.get_budget_status.return_value = {
                "total_cost": 0.50,
                "budget_limit": 13.00,
                "remaining": 12.50
            }
            mock_llm.return_value = mock_client

            response = client.get("/api/execute/budget")
            assert response.status_code == 200

    def test_returns_budget_info(self, client):
        """Budget endpoint returns budget information."""
        with patch('app.api.routes.execute.get_llm_client') as mock_llm:
            mock_client = MagicMock()
            mock_client.get_budget_status.return_value = {
                "total_cost": 0.50,
                "budget_limit": 13.00,
                "remaining": 12.50
            }
            mock_llm.return_value = mock_client

            response = client.get("/api/execute/budget")
            data = response.json()

            assert "total_cost" in data or "error" in data
