"""
Pinecone client for long-term memory operations.
Handles student profiles and teaching methods knowledge base.
"""
from typing import Optional, List, Dict, Any
import json
from pathlib import Path

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None

from app.config import get_settings


# Namespace constants
NAMESPACE_STUDENT_PROFILES = "student-profiles"
NAMESPACE_TEACHING_METHODS = "teaching-methods"
NAMESPACE_INTERVENTIONS = "interventions"


class MockPineconeClient:
    """
    Mock Pinecone client for local testing without Pinecone connection.
    Loads student data from JSON files.
    """
    
    def __init__(self):
        self._students = {}
        self._methods = {}
        self._interventions = {}
        self._load_sample_data()
        print("INFO: Using MockPineconeClient (loading from JSON files)")
    
    def _load_sample_data(self):
        """Load sample data from JSON files."""
        data_dir = Path(__file__).parent.parent.parent / "data"
        print(f"DEBUG MockPinecone: Looking for data in {data_dir}")
        
        # Load students
        students_file = data_dir / "sample_students.json"
        if students_file.exists():
            with open(students_file) as f:
                data = json.load(f)
                for student in data.get("students", []):
                    self._students[student["student_id"]] = student
            print(f"DEBUG MockPinecone: Loaded {len(self._students)} students")
        else:
            print(f"DEBUG MockPinecone: Students file not found at {students_file}")
        
        # Load teaching methods
        methods_file = data_dir / "teaching_methods.json"
        if methods_file.exists():
            with open(methods_file) as f:
                data = json.load(f)
                for category in data.get("categories", []):
                    for method in category.get("methods", []):
                        method_id = f"{category['id']}_{method['id']}"
                        self._methods[method_id] = {
                            "method_id": method_id,
                            "method_name": method["name"],
                            "category": category["name"],
                            "description": method["description"],
                            "techniques": method.get("techniques", []),
                            "when_to_use": method.get("when_to_use", ""),
                            "applicable_disabilities": [category["id"]]
                        }
            print(f"DEBUG MockPinecone: Loaded {len(self._methods)} teaching methods")
        else:
            print(f"DEBUG MockPinecone: Methods file not found at {methods_file}")
    
    async def upsert_student_profile(self, student_id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        self._students[student_id] = metadata
        return True
    
    async def get_student_profile(self, student_id: str) -> Optional[Dict[str, Any]]:
        return self._students.get(student_id)
    
    async def search_students(self, query_embedding: List[float], top_k: int = 5, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        results = list(self._students.values())[:top_k]
        return [{"student_id": s.get("student_id"), "score": 0.9, **s} for s in results]
    
    async def search_student_by_name(self, query_embedding: List[float], name: str, top_k: int = 3) -> List[Dict[str, Any]]:
        results = [
            {"student_id": s.get("student_id"), "score": 0.95, **s}
            for s in self._students.values()
            if name.lower() in s.get("name", "").lower()
        ]
        return results[:top_k]
    
    async def delete_student_profile(self, student_id: str) -> bool:
        self._students.pop(student_id, None)
        return True
    
    async def upsert_teaching_method(self, method_id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        self._methods[method_id] = metadata
        return True
    
    async def search_teaching_methods(self, query_embedding: List[float], top_k: int = 5, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        results = list(self._methods.values())[:top_k]
        print(f"DEBUG MockPinecone: search_teaching_methods returning {len(results)} methods")
        return [{"method_id": m.get("method_id"), "score": 0.85, **m} for m in results]
    
    async def get_teaching_method(self, method_id: str) -> Optional[Dict[str, Any]]:
        return self._methods.get(method_id)
    
    async def upsert_intervention(self, intervention_id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        self._interventions[intervention_id] = metadata
        return True
    
    async def search_interventions(self, query_embedding: List[float], top_k: int = 5, student_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self._interventions.values())
        if student_id:
            results = [i for i in results if i.get("student_id") == student_id]
        return results[:top_k]
    
    async def get_index_stats(self) -> Dict[str, Any]:
        return {
            "dimension": 1536,
            "total_vector_count": len(self._students) + len(self._methods) + len(self._interventions),
            "namespaces": {
                NAMESPACE_STUDENT_PROFILES: len(self._students),
                NAMESPACE_TEACHING_METHODS: len(self._methods),
                NAMESPACE_INTERVENTIONS: len(self._interventions)
            }
        }
    
    async def delete_all_in_namespace(self, namespace: str) -> bool:
        if namespace == NAMESPACE_STUDENT_PROFILES:
            self._students.clear()
        elif namespace == NAMESPACE_TEACHING_METHODS:
            self._methods.clear()
        elif namespace == NAMESPACE_INTERVENTIONS:
            self._interventions.clear()
        return True


class PineconeClient:
    """
    Client for Pinecone vector database operations.
    Manages long-term memory: student profiles, teaching methods, interventions.
    """

    def __init__(self):
        settings = get_settings()
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index = self.pc.Index(settings.pinecone_index_name)

    # ==================== Student Profiles ====================

    async def upsert_student_profile(
        self,
        student_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Upsert a student profile.

        Args:
            student_id: Unique student identifier
            embedding: Vector embedding of the profile
            metadata: Student profile data (name, triggers, methods, etc.)
        """
        self.index.upsert(
            vectors=[{
                "id": student_id,
                "values": embedding,
                "metadata": metadata
            }],
            namespace=NAMESPACE_STUDENT_PROFILES
        )
        return True

    async def get_student_profile(
        self,
        student_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a student profile by ID."""
        result = self.index.fetch(
            ids=[student_id],
            namespace=NAMESPACE_STUDENT_PROFILES
        )
        if result.vectors and student_id in result.vectors:
            return result.vectors[student_id].metadata
        return None

    async def search_students(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar students based on embedding.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
        """
        result = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=NAMESPACE_STUDENT_PROFILES,
            include_metadata=True,
            filter=filter_dict
        )
        return [
            {
                "student_id": match.id,
                "score": match.score,
                **match.metadata
            }
            for match in result.matches
        ]

    async def search_student_by_name(
        self,
        query_embedding: List[float],
        name: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Search for students with a specific name."""
        # Note: Pinecone doesn't support exact text matching in free tier
        # We search by embedding and filter results
        results = await self.search_students(query_embedding, top_k=10)
        return [
            r for r in results
            if name.lower() in r.get("name", "").lower()
        ][:top_k]

    async def delete_student_profile(self, student_id: str) -> bool:
        """Delete a student profile."""
        self.index.delete(
            ids=[student_id],
            namespace=NAMESPACE_STUDENT_PROFILES
        )
        return True

    # ==================== Teaching Methods ====================

    async def upsert_teaching_method(
        self,
        method_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Upsert a teaching method to the knowledge base.

        Args:
            method_id: Unique method identifier
            embedding: Vector embedding of the method description
            metadata: Method data (name, category, applicable disabilities, etc.)
        """
        self.index.upsert(
            vectors=[{
                "id": method_id,
                "values": embedding,
                "metadata": metadata
            }],
            namespace=NAMESPACE_TEACHING_METHODS
        )
        return True

    async def search_teaching_methods(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant teaching methods.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters (e.g., disability_type, category)
        """
        result = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=NAMESPACE_TEACHING_METHODS,
            include_metadata=True,
            filter=filter_dict
        )
        return [
            {
                "method_id": match.id,
                "score": match.score,
                **match.metadata
            }
            for match in result.matches
        ]

    async def get_teaching_method(
        self,
        method_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a teaching method by ID."""
        result = self.index.fetch(
            ids=[method_id],
            namespace=NAMESPACE_TEACHING_METHODS
        )
        if result.vectors and method_id in result.vectors:
            return result.vectors[method_id].metadata
        return None

    # ==================== Interventions ====================

    async def upsert_intervention(
        self,
        intervention_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Record an intervention outcome.

        Args:
            intervention_id: Unique intervention identifier
            embedding: Vector embedding of the intervention context
            metadata: Intervention data (student_id, method_used, outcome, etc.)
        """
        self.index.upsert(
            vectors=[{
                "id": intervention_id,
                "values": embedding,
                "metadata": metadata
            }],
            namespace=NAMESPACE_INTERVENTIONS
        )
        return True

    async def search_interventions(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        student_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar past interventions.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            student_id: Optional filter by student
        """
        filter_dict = None
        if student_id:
            filter_dict = {"student_id": {"$eq": student_id}}

        result = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=NAMESPACE_INTERVENTIONS,
            include_metadata=True,
            filter=filter_dict
        )
        return [
            {
                "intervention_id": match.id,
                "score": match.score,
                **match.metadata
            }
            for match in result.matches
        ]

    # ==================== Utility Methods ====================

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        stats = self.index.describe_index_stats()
        return {
            "dimension": stats.dimension,
            "total_vector_count": stats.total_vector_count,
            "namespaces": {
                name: ns.vector_count
                for name, ns in stats.namespaces.items()
            }
        }

    async def delete_all_in_namespace(self, namespace: str) -> bool:
        """Delete all vectors in a namespace (use with caution!)."""
        self.index.delete(delete_all=True, namespace=namespace)
        return True


# Singleton instance
_pinecone_client = None


def get_pinecone_client():
    """Get or create the Pinecone client singleton. Returns MockPineconeClient if connection fails or USE_MOCK_SERVICES is set."""
    global _pinecone_client
    if _pinecone_client is None:
        settings = get_settings()
        
        # Force mock client if USE_MOCK_SERVICES is set
        if settings.use_mock_services:
            print("INFO: USE_MOCK_SERVICES=true, using MockPineconeClient")
            _pinecone_client = MockPineconeClient()
            return _pinecone_client
        
        try:
            _pinecone_client = PineconeClient()
        except Exception as e:
            print(f"WARNING: Failed to connect to Pinecone: {e}")
            print("WARNING: Using MockPineconeClient (loading from JSON files)")
            _pinecone_client = MockPineconeClient()
    return _pinecone_client
