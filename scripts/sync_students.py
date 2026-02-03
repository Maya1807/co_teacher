"""
Sync students between Supabase and Pinecone.

Ensures both systems have consistent data:
- Supabase: Canonical student profiles
- Pinecone: Embeddings for semantic search
"""

import asyncio
from app.memory.memory_manager import get_memory_manager
from app.memory.supabase_client import get_supabase_client
from app.memory.pinecone_client import get_pinecone_client
from app.core.llm_client import get_llm_client


async def sync_students_to_pinecone():
    """
    Sync all students from Supabase to Pinecone.

    Creates/updates embeddings for each student profile.
    """
    supabase = get_supabase_client()
    pinecone = get_pinecone_client()
    llm = get_llm_client()
    mm = get_memory_manager()

    print("Fetching students from Supabase...")
    students = await supabase.list_students(limit=100)
    print(f"Found {len(students)} students")

    if not students:
        print("No students found in Supabase. Run the SQL to create the students table first.")
        return

    print("\nSyncing to Pinecone...")
    for i, student in enumerate(students):
        student_id = student.get("id")
        if not student_id:
            print(f"  Skipping student without ID: {student}")
            continue

        # Create embedding text
        profile_text = mm._profile_to_text(student)

        # Generate embedding
        try:
            embedding = await llm.embed(profile_text)

            # Upsert to Pinecone
            await pinecone.upsert_student_profile(student_id, embedding, student)
            print(f"  ✓ {student.get('name', student_id)}")
        except Exception as e:
            print(f"  ✗ {student.get('name', student_id)}: {e}")

    print("\nVerifying Pinecone stats...")
    stats = await pinecone.get_index_stats()
    print(f"Pinecone stats: {stats}")


async def verify_sync():
    """Verify students exist in both Supabase and Pinecone."""
    supabase = get_supabase_client()
    pinecone = get_pinecone_client()

    print("Checking Supabase...")
    students = await supabase.list_students()
    print(f"  Supabase: {len(students)} students")

    print("\nChecking Pinecone...")
    stats = await pinecone.get_index_stats()
    student_count = stats.get("namespaces", {}).get("student-profiles", 0)
    if isinstance(student_count, dict):
        student_count = student_count.get("vector_count", 0)
    print(f"  Pinecone student-profiles: {student_count} vectors")

    if students:
        print("\nStudents in Supabase:")
        for s in students:
            print(f"  - {s.get('id')}: {s.get('name')} ({s.get('disability_type')})")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        asyncio.run(verify_sync())
    else:
        asyncio.run(sync_students_to_pinecone())
