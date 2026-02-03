#!/usr/bin/env python3
"""
Generate architecture.png from architecture.mmd using Mermaid CLI.

Prerequisites:
    npm install -g @mermaid-js/mermaid-cli

Usage:
    python scripts/generate_architecture.py

This script:
1. Reads static/architecture.mmd (Mermaid source)
2. Generates static/architecture.png using mmdc (Mermaid CLI)
3. Validates that module names match step_tracker.VALID_MODULES
"""
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Module names must match these (from step_tracker.py)
VALID_MODULES = ["ORCHESTRATOR", "STUDENT_AGENT", "RAG_AGENT", "ADMIN_AGENT", "PREDICT_AGENT"]


def check_mmdc_installed() -> bool:
    """Check if mermaid-cli is installed."""
    try:
        result = subprocess.run(
            ["mmdc", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def validate_module_names(mmd_content: str) -> list:
    """
    Validate that module names in the diagram match VALID_MODULES.
    Returns list of issues found.
    """
    issues = []

    # Check that all VALID_MODULES appear in the diagram
    for module in VALID_MODULES:
        if module not in mmd_content:
            issues.append(f"Missing module: {module}")

    return issues


def generate_diagram():
    """Generate PNG from Mermaid source."""
    static_dir = PROJECT_ROOT / "static"
    mmd_file = static_dir / "architecture.mmd"
    png_file = static_dir / "architecture.png"

    # Check source exists
    if not mmd_file.exists():
        print(f"Error: Source file not found: {mmd_file}")
        sys.exit(1)

    # Validate module names
    mmd_content = mmd_file.read_text()
    issues = validate_module_names(mmd_content)
    if issues:
        print("Warning: Module name consistency issues:")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\nExpected modules (from step_tracker): {VALID_MODULES}")

    # Check mmdc is installed
    if not check_mmdc_installed():
        print("Error: mermaid-cli (mmdc) is not installed.")
        print("\nInstall it with:")
        print("  npm install -g @mermaid-js/mermaid-cli")
        print("\nOr use npx:")
        print(f"  npx -p @mermaid-js/mermaid-cli mmdc -i {mmd_file} -o {png_file} -b white")
        sys.exit(1)

    # Generate PNG
    print(f"Generating {png_file} from {mmd_file}...")

    result = subprocess.run(
        [
            "mmdc",
            "-i", str(mmd_file),
            "-o", str(png_file),
            "-b", "white",
            "-w", "1600",
            "-H", "1200",
            "-s", "2"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error generating diagram:")
        print(result.stderr)
        sys.exit(1)

    print(f"Successfully generated: {png_file}")
    print(f"\nModule names in diagram match step tracking:")
    for module in VALID_MODULES:
        status = "✓" if module in mmd_content else "✗"
        print(f"  {status} {module}")


def print_mermaid_live_url():
    """Print URL to view diagram in Mermaid Live Editor."""
    import base64
    import json

    static_dir = PROJECT_ROOT / "static"
    mmd_file = static_dir / "architecture.mmd"

    if not mmd_file.exists():
        return

    mmd_content = mmd_file.read_text()

    # Create Mermaid Live Editor state
    state = {
        "code": mmd_content,
        "mermaid": {"theme": "default"},
        "autoSync": True,
        "updateDiagram": True
    }

    # Encode for URL
    state_json = json.dumps(state)
    state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

    print(f"\nView/edit in Mermaid Live Editor:")
    print(f"  https://mermaid.live/edit#pako:{state_b64[:50]}...")
    print(f"\n(Copy the full content of architecture.mmd to https://mermaid.live)")


if __name__ == "__main__":
    print("=" * 60)
    print("Co-Teacher Architecture Diagram Generator")
    print("=" * 60)
    print()

    generate_diagram()
    print_mermaid_live_url()
