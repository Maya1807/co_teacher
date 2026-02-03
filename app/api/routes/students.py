"""
Students API endpoints.
Provides student data for frontend and agent operations.

Data source: Supabase only (single source of truth)
To seed initial data, run: python scripts/seed_data.py
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.memory.supabase_client import get_supabase_client

router = APIRouter()


class StudentSummary(BaseModel):
    """Summary of a student for listing."""
    student_id: str
    name: str
    grade: str
    disability_type: str
    learning_style: str


class StudentDetail(BaseModel):
    """Full student profile."""
    student_id: str
    name: str
    grade: str
    age: Optional[int] = None
    disability_type: str
    learning_style: str
    triggers: List[str]
    successful_methods: List[str]
    failed_methods: List[str]
    iep_goals: Optional[List[str]] = None
    accommodations: Optional[List[str]] = None
    notes: Optional[str] = None


class StudentsListResponse(BaseModel):
    """Response for students list endpoint."""
    students: List[StudentSummary]
    total: int


class StudentsFullListResponse(BaseModel):
    """Response for students list with full details."""
    students: List[StudentDetail]
    total: int


async def load_students_from_supabase() -> List[dict]:
    """Load students from Supabase database."""
    try:
        supabase = get_supabase_client()
        students = await supabase.list_students(limit=100)
        return students if students else []
    except Exception as e:
        print(f"Error loading students from Supabase: {e}")
        return []


@router.get("/students")
async def list_students(
    disability_type: Optional[str] = Query(None, description="Filter by disability type"),
    grade: Optional[str] = Query(None, description="Filter by grade level"),
    full: bool = Query(False, description="Include full student details")
):
    """
    Get list of all students with optional filtering.

    Use full=true to get complete student details including triggers, methods, etc.
    Reads from Supabase (live data), falls back to JSON if Supabase unavailable.
    """
    # Load from Supabase (single source of truth)
    students = await load_students_from_supabase()

    # Apply filters
    if disability_type:
        students = [s for s in students if s.get("disability_type", "").lower() == disability_type.lower()]

    if grade:
        students = [s for s in students if s.get("grade") == grade]

    if full:
        # Return full details
        details = [
            StudentDetail(
                student_id=s.get("student_id", s.get("id", "")),
                name=s["name"],
                grade=s.get("grade", ""),
                disability_type=s.get("disability_type", ""),
                learning_style=s.get("learning_style", ""),
                triggers=s.get("triggers", []),
                successful_methods=s.get("successful_methods", []),
                failed_methods=s.get("failed_methods", []),
                iep_goals=s.get("iep_goals"),
                accommodations=s.get("accommodations"),
                notes=s.get("notes")
            )
            for s in students
        ]
        return StudentsFullListResponse(
            students=details,
            total=len(details)
        )

    # Convert to summaries
    summaries = [
        StudentSummary(
            student_id=s.get("student_id", s.get("id", "")),
            name=s["name"],
            grade=s.get("grade", ""),
            disability_type=s.get("disability_type", ""),
            learning_style=s.get("learning_style", "")
        )
        for s in students
    ]

    return StudentsListResponse(
        students=summaries,
        total=len(summaries)
    )


@router.get("/students/{student_id}", response_model=StudentDetail)
async def get_student(student_id: str):
    """
    Get detailed information for a specific student.
    """
    supabase = get_supabase_client()
    student = await supabase.get_student(student_id)

    if student:
        return StudentDetail(
            student_id=student.get("id") or student.get("student_id", ""),
            name=student["name"],
            grade=student.get("grade", ""),
            disability_type=student.get("disability_type", ""),
            learning_style=student.get("learning_style", ""),
            triggers=student.get("triggers", []),
            successful_methods=student.get("successful_methods", []),
            failed_methods=student.get("failed_methods", []),
            iep_goals=student.get("iep_goals"),
            accommodations=student.get("accommodations"),
            notes=student.get("notes")
        )

    raise HTTPException(status_code=404, detail=f"Student {student_id} not found")


@router.get("/students/by-name/{name}")
async def get_student_by_name(name: str):
    """
    Search for a student by name (partial match).
    """
    students = await load_students_from_supabase()

    name_lower = name.lower()
    matches = [
        StudentDetail(
            student_id=s.get("student_id", s.get("id", "")),
            name=s.get("name", ""),
            grade=s.get("grade", ""),
            disability_type=s.get("disability_type", ""),
            learning_style=s.get("learning_style", ""),
            triggers=s.get("triggers", []),
            successful_methods=s.get("successful_methods", []),
            failed_methods=s.get("failed_methods", []),
            iep_goals=s.get("iep_goals"),
            accommodations=s.get("accommodations"),
            notes=s.get("notes")
        )
        for s in students
        if name_lower in s.get("name", "").lower()
    ]
    
    if not matches:
        raise HTTPException(status_code=404, detail=f"No student found matching '{name}'")
    
    return matches[0] if len(matches) == 1 else {"matches": matches, "count": len(matches)}


@router.get("/disability-types")
async def list_disability_types():
    """
    Get list of unique disability types for filtering.
    """
    students = await load_students_from_supabase()
    
    types = sorted(set(s.get("disability_type", "") for s in students if s.get("disability_type")))
    
    return {
        "disability_types": types,
        "count": len(types)
    }
