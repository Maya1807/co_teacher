"""
Pytest configuration and shared fixtures.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_llm_client():
    """Mock LLM client to avoid actual API calls in unit tests."""
    client = Mock()
    client.complete = AsyncMock(return_value={
        "content": "Mock response",
        "tokens_used": {"prompt": 50, "completion": 100},
        "cost": 0.0001
    })
    client.embed = AsyncMock(return_value=[0.1] * 1536)
    return client


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = Mock()
    client.table = Mock(return_value=Mock(
        select=Mock(return_value=Mock(execute=Mock(return_value=Mock(data=[])))),
        insert=Mock(return_value=Mock(execute=Mock(return_value=Mock(data=[])))),
        update=Mock(return_value=Mock(execute=Mock(return_value=Mock(data=[])))),
        delete=Mock(return_value=Mock(execute=Mock(return_value=Mock(data=[]))))
    ))
    return client


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone client."""
    index = Mock()
    index.query = Mock(return_value=Mock(matches=[]))
    index.upsert = Mock(return_value=None)
    index.delete = Mock(return_value=None)
    return index


@pytest.fixture
def sample_student_profile():
    """Sample student data for testing."""
    return {
        "student_id": "STU001",
        "name": "Alex Johnson",
        "grade": "4",
        "disability_type": "autism",
        "learning_style": "visual",
        "triggers": ["loud noises", "schedule changes", "fire drills"],
        "successful_methods": ["visual schedules", "fidget tools", "social stories", "advance warnings"],
        "failed_methods": ["group work without support", "verbal-only instructions"]
    }


@pytest.fixture
def sample_teaching_methods():
    """Sample RAG knowledge base entries."""
    return [
        {
            "method_id": "MTH001",
            "method_name": "Visual Schedule",
            "category": "behavior",
            "description": "Use visual representations of daily activities and transitions.",
            "applicable_disabilities": ["autism", "ADHD"],
            "evidence_level": "research-based"
        },
        {
            "method_id": "MTH002",
            "method_name": "Movement Breaks",
            "category": "behavior",
            "description": "Short physical activity breaks to help with focus and regulation.",
            "applicable_disabilities": ["ADHD", "sensory_processing"],
            "evidence_level": "research-based"
        },
        {
            "method_id": "MTH003",
            "method_name": "Graphic Organizers",
            "category": "academic",
            "description": "Visual tools to organize information and support comprehension.",
            "applicable_disabilities": ["dyslexia", "autism", "ADHD"],
            "evidence_level": "research-based"
        }
    ]


@pytest.fixture
def test_client():
    """FastAPI test client."""
    from app.main import app
    return TestClient(app)
