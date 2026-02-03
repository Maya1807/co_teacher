#!/usr/bin/env python3
"""
Seed Data Script
Loads sample students and teaching methods into the memory system.

Usage:
    python scripts/seed_data.py [--dry-run] [--students-only] [--methods-only]
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.memory.memory_manager import get_memory_manager
from app.core.llm_client import get_llm_client


DATA_DIR = project_root / "data"
STUDENTS_FILE = DATA_DIR / "seed_students.json"  # Seed data only, not runtime
METHODS_FILE = DATA_DIR / "teaching_methods.json"


def load_json_file(filepath: Path) -> dict:
    """Load data from a JSON file."""
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return {}
    
    with open(filepath, 'r') as f:
        return json.load(f)


async def seed_students(dry_run: bool = False) -> int:
    """
    Seed student profiles into Pinecone.
    
    Returns:
        Number of students seeded
    """
    print("\n=== Seeding Student Profiles ===")
    
    data = load_json_file(STUDENTS_FILE)
    students = data.get("students", [])
    
    if not students:
        print("No students found in data file.")
        return 0
    
    print(f"Found {len(students)} students to seed.")
    
    if dry_run:
        for student in students:
            print(f"  [DRY RUN] Would seed: {student['name']} ({student['student_id']})")
        return len(students)
    
    memory = get_memory_manager()
    seeded_count = 0
    
    for student in students:
        try:
            student_id = student["student_id"]
            print(f"  Seeding: {student['name']} ({student_id})...", end=" ")
            
            # Create profile data for memory
            profile_data = {
                "name": student["name"],
                "grade": student["grade"],
                "disability_type": student["disability_type"],
                "learning_style": student["learning_style"],
                "triggers": student.get("triggers", []),
                "successful_methods": student.get("successful_methods", []),
                "failed_methods": student.get("failed_methods", []),
                "notes": student.get("notes", "")
            }

            # Use create_student for initial seeding (student_id, profile_data)
            result = await memory.create_student(student_id, profile_data)
            success = result is not None
            
            if success:
                print("OK")
                seeded_count += 1
            else:
                print("FAILED")
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\nSeeded {seeded_count}/{len(students)} students successfully.")
    return seeded_count


async def seed_teaching_methods(dry_run: bool = False) -> int:
    """
    Seed teaching methods into Pinecone.
    
    Returns:
        Number of methods seeded
    """
    print("\n=== Seeding Teaching Methods ===")
    
    data = load_json_file(METHODS_FILE)
    categories = data.get("categories", [])
    
    if not categories:
        print("No teaching method categories found in data file.")
        return 0
    
    # Flatten methods from all categories
    all_methods = []
    for category in categories:
        category_id = category["id"]
        category_name = category["name"]
        
        for method in category.get("methods", []):
            method_entry = {
                "method_id": f"{category_id}_{method['id']}",
                "method_name": method["name"],
                "category": category_name,
                "category_id": category_id,
                "description": method["description"],
                "techniques": method.get("techniques", []),
                "when_to_use": method.get("when_to_use", ""),
                "evidence_level": method.get("evidence_level", ""),
                "applicable_disabilities": [category_id]  # Primary disability
            }
            all_methods.append(method_entry)
    
    print(f"Found {len(all_methods)} methods across {len(categories)} categories.")
    
    if dry_run:
        for method in all_methods:
            print(f"  [DRY RUN] Would seed: {method['method_name']} ({method['method_id']})")
        return len(all_methods)
    
    memory = get_memory_manager()
    seeded_count = 0
    
    for method in all_methods:
        try:
            method_id = method["method_id"]
            print(f"  Seeding: {method['method_name']}...", end=" ")
            
            success = await memory.add_teaching_method(method_id, method)
            
            if success:
                print("OK")
                seeded_count += 1
            else:
                print("FAILED")
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\nSeeded {seeded_count}/{len(all_methods)} methods successfully.")
    return seeded_count


async def seed_general_strategies(dry_run: bool = False) -> int:
    """
    Seed general strategies that apply to all students.
    
    Returns:
        Number of strategies seeded
    """
    print("\n=== Seeding General Strategies ===")
    
    data = load_json_file(METHODS_FILE)
    strategies = data.get("general_strategies", [])
    
    if not strategies:
        print("No general strategies found in data file.")
        return 0
    
    print(f"Found {len(strategies)} general strategies to seed.")
    
    if dry_run:
        for strategy in strategies:
            print(f"  [DRY RUN] Would seed: {strategy['name']} ({strategy['id']})")
        return len(strategies)
    
    memory = get_memory_manager()
    seeded_count = 0
    
    for strategy in strategies:
        try:
            strategy_id = f"general_{strategy['id']}"
            print(f"  Seeding: {strategy['name']}...", end=" ")
            
            method_data = {
                "method_id": strategy_id,
                "method_name": strategy["name"],
                "category": "General",
                "category_id": "general",
                "description": strategy["description"],
                "techniques": strategy.get("key_principles", []),
                "when_to_use": "Applicable to all students",
                "evidence_level": "Strong research support",
                "applicable_disabilities": ["all"]
            }
            
            success = await memory.add_teaching_method(strategy_id, method_data)
            
            if success:
                print("OK")
                seeded_count += 1
            else:
                print("FAILED")
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\nSeeded {seeded_count}/{len(strategies)} strategies successfully.")
    return seeded_count


async def verify_seed(dry_run: bool = False) -> None:
    """Verify that data was seeded correctly by running test queries."""
    if dry_run:
        print("\n=== Verification skipped (dry run) ===")
        return
    
    print("\n=== Verifying Seeded Data ===")
    
    memory = get_memory_manager()
    
    # Test 1: Get a specific student
    print("\nTest 1: Get student by ID...")
    profile = await memory.get_student_profile("STU001")
    if profile:
        print(f"  Found: {profile.get('name', 'Unknown')} - OK")
    else:
        print("  Student not found - FAILED")
    
    # Test 2: Search for students
    print("\nTest 2: Search students by name...")
    matches = await memory.search_student_by_name("Alex")
    if matches:
        print(f"  Found {len(matches)} match(es) - OK")
    else:
        print("  No matches found - WARNING (may need time to index)")
    
    # Test 3: Search teaching methods
    print("\nTest 3: Search teaching methods...")
    methods = await memory.search_teaching_methods(
        "visual supports for autism",
        top_k=3
    )
    if methods:
        print(f"  Found {len(methods)} method(s) - OK")
        for m in methods[:2]:
            print(f"    - {m.get('method_name', 'Unknown')}")
    else:
        print("  No methods found - WARNING (may need time to index)")
    
    print("\n=== Verification Complete ===")


async def main():
    """Main entry point for the seed script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed sample data into the Co-Teacher system")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be seeded without actually seeding"
    )
    parser.add_argument(
        "--students-only",
        action="store_true",
        help="Only seed student profiles"
    )
    parser.add_argument(
        "--methods-only",
        action="store_true",
        help="Only seed teaching methods"
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip verification after seeding"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Co-Teacher Data Seeding Script")
    print("=" * 50)
    
    if args.dry_run:
        print("\n[DRY RUN MODE - No data will be written]")
    
    total_seeded = 0
    
    # Seed students
    if not args.methods_only:
        total_seeded += await seed_students(args.dry_run)
    
    # Seed teaching methods
    if not args.students_only:
        total_seeded += await seed_teaching_methods(args.dry_run)
        total_seeded += await seed_general_strategies(args.dry_run)
    
    # Verify
    if not args.skip_verify:
        await verify_seed(args.dry_run)
    
    print("\n" + "=" * 50)
    print(f"Total items seeded: {total_seeded}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
