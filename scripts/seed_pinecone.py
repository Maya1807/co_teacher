"""
Seed Pinecone with student profiles and teaching methods.
Run with: python -m scripts.seed_pinecone
"""
import asyncio
import json
from pathlib import Path

from app.memory.memory_manager import get_memory_manager
from app.core.llm_client import get_llm_client


async def seed_students():
    """Seed student profiles into Pinecone."""
    data_file = Path(__file__).parent.parent / "data" / "sample_students.json"

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return False

    with open(data_file) as f:
        data = json.load(f)

    students = data.get("students", [])
    print(f"Found {len(students)} students to seed")

    memory = get_memory_manager()
    llm = get_llm_client()

    for student in students:
        student_id = student["student_id"]
        print(f"  Seeding {student['name']} ({student_id})...")

        # Create text representation for embedding
        profile_text = f"""
        Student: {student['name']}
        Grade: {student['grade']}
        Age: {student.get('age', 'Unknown')}
        Disability Type: {student['disability_type']}
        Learning Style: {student['learning_style']}
        Triggers: {', '.join(student.get('triggers', []))}
        Successful Methods: {', '.join(student.get('successful_methods', []))}
        Failed Methods: {', '.join(student.get('failed_methods', []))}
        IEP Goals: {', '.join(student.get('iep_goals', []))}
        Notes: {student.get('notes', '')}
        """

        # Generate embedding
        embedding = await llm.embed(profile_text)

        # Upsert to Pinecone
        success = await memory.pinecone.upsert_student_profile(
            student_id=student_id,
            embedding=embedding,
            metadata=student
        )

        if success:
            print(f"    ✓ {student['name']} added")
        else:
            print(f"    ✗ Failed to add {student['name']}")

    return True


async def seed_teaching_methods():
    """Seed teaching methods into Pinecone."""
    data_file = Path(__file__).parent.parent / "data" / "teaching_methods.json"

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return False

    with open(data_file) as f:
        data = json.load(f)

    categories = data.get("categories", [])
    total_methods = sum(len(cat.get("methods", [])) for cat in categories)
    print(f"Found {total_methods} teaching methods to seed")

    memory = get_memory_manager()
    llm = get_llm_client()

    for category in categories:
        category_name = category["name"]
        category_id = category["id"]

        for method in category.get("methods", []):
            method_id = f"{category_id}_{method['id']}"
            method_name = method["name"]
            print(f"  Seeding {method_name}...")

            # Create text representation for embedding
            method_text = f"""
            Teaching Method: {method_name}
            Category: {category_name}
            Description: {method['description']}
            Techniques: {', '.join(method.get('techniques', []))}
            When to use: {method.get('when_to_use', '')}
            Applicable disabilities: {category_id}
            """

            # Generate embedding
            embedding = await llm.embed(method_text)

            # Build metadata
            metadata = {
                "method_id": method_id,
                "method_name": method_name,
                "category": category_name,
                "description": method["description"],
                "techniques": method.get("techniques", []),
                "when_to_use": method.get("when_to_use", ""),
                "applicable_disabilities": [category_id]
            }

            # Upsert to Pinecone
            success = await memory.pinecone.upsert_teaching_method(
                method_id=method_id,
                embedding=embedding,
                metadata=metadata
            )

            if success:
                print(f"    ✓ {method_name} added")
            else:
                print(f"    ✗ Failed to add {method_name}")

    return True


async def verify_data():
    """Verify data was seeded correctly."""
    memory = get_memory_manager()

    print("\nVerifying Pinecone data...")
    stats = await memory.pinecone.get_index_stats()
    print(f"  Total vectors: {stats['total_vector_count']}")
    print(f"  Namespaces: {stats['namespaces']}")

    # Try to find Alex
    print("\nTesting student search for 'Alex'...")
    results = await memory.search_student_by_name("Alex")
    if results:
        print(f"  ✓ Found {len(results)} result(s)")
        for r in results:
            print(f"    - {r.get('name')} ({r.get('student_id')})")
    else:
        print("  ✗ No results found")


async def main():
    print("=" * 50)
    print("Seeding Pinecone Database")
    print("=" * 50)

    print("\n1. Seeding student profiles...")
    await seed_students()

    print("\n2. Seeding teaching methods...")
    await seed_teaching_methods()

    print("\n3. Verifying data...")
    await verify_data()

    print("\n" + "=" * 50)
    print("Seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
