#!/usr/bin/env python3
"""
Cache Investigation Script

Investigates why validation workflows can't find checkpoint files in cache.
Checks cache key matching, file presence, permissions, and sizes.

Requirements: 2.5, 3.2, 3.3
"""

import os
import sys
from pathlib import Path
from typing import Dict, List


def check_checkpoint_files(checkpoint_dir: Path) -> Dict[str, any]:
    """
    Check if all required checkpoint files exist and are valid.

    Returns:
        Dictionary with file status information
    """
    required_files = [
        "graph_topology.gpickle",
        "metadata_cache.db",
        "checkpoint_metadata.json",
    ]

    results = {
        "directory_exists": checkpoint_dir.exists(),
        "directory_path": str(checkpoint_dir),
        "files": {},
        "all_present": False,
        "total_size": 0,
    }

    if not checkpoint_dir.exists():
        return results

    all_present = True
    total_size = 0

    for filename in required_files:
        file_path = checkpoint_dir / filename
        file_info = {
            "exists": file_path.exists(),
            "path": str(file_path),
            "size": 0,
            "readable": False,
            "writable": False,
        }

        if file_path.exists():
            try:
                stat_info = file_path.stat()
                file_info["size"] = stat_info.st_size
                file_info["readable"] = os.access(file_path, os.R_OK)
                file_info["writable"] = os.access(file_path, os.W_OK)
                file_info["mode"] = oct(stat_info.st_mode)
                total_size += stat_info.st_size

                # Check if file is empty
                if stat_info.st_size == 0:
                    file_info["warning"] = "File is empty"
                    all_present = False
            except Exception as e:
                file_info["error"] = str(e)
                all_present = False
        else:
            all_present = False

        results["files"][filename] = file_info

    results["all_present"] = all_present
    results["total_size"] = total_size

    return results


def format_size(size_bytes: int) -> str:
    """Format size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def analyze_cache_keys() -> Dict[str, any]:
    """
    Analyze cache key patterns used in workflows.

    Returns:
        Dictionary with cache key analysis
    """
    workflow_dir = Path(".github/workflows")
    cache_patterns = {"nightly_collection": [], "repair": [], "validation": []}

    # Nightly collection workflow
    nightly_file = workflow_dir / "freesound-nightly-pipeline.yml"
    if nightly_file.exists():
        content = nightly_file.read_text(encoding="utf-8")
        if "checkpoint-${{ github.run_id }}" in content:
            cache_patterns["nightly_collection"].append(
                "checkpoint-${{ github.run_id }}"
            )

    # Repair workflow
    repair_file = workflow_dir / "freesound-data-repair.yml"
    if repair_file.exists():
        content = repair_file.read_text(encoding="utf-8")
        if "checkpoint-${{ github.event.workflow_run.id || github.run_id }}" in content:
            cache_patterns["repair"].append(
                "checkpoint-${{ github.event.workflow_run.id || github.run_id }}"
            )
        if "checkpoint-repaired-${{ github.run_id }}" in content:
            cache_patterns["repair"].append("checkpoint-repaired-${{ github.run_id }}")

    # Validation workflow
    validation_file = workflow_dir / "freesound-validation-visualization.yml"
    if validation_file.exists():
        content = validation_file.read_text(encoding="utf-8")
        if "checkpoint-repaired-${{ github.event.workflow_run.id }}" in content:
            cache_patterns["validation"].append(
                "checkpoint-repaired-${{ github.event.workflow_run.id }}"
            )

    return cache_patterns


def check_cache_key_compatibility() -> List[Dict[str, str]]:
    """
    Check if cache keys are compatible between workflows.

    Returns:
        List of potential issues
    """
    issues = []

    # Issue 1: Nightly collection saves with run_id, but repair tries to restore with workflow_run.id
    issues.append(
        {
            "severity": "CRITICAL",
            "workflow": "nightly → repair",
            "issue": "Cache key mismatch",
            "details": (
                "Nightly collection saves: checkpoint-${{ github.run_id }}\n"
                "Repair tries to restore: checkpoint-${{ github.event.workflow_run.id }}\n"
                "These should match! workflow_run.id should equal the nightly run_id"
            ),
            "fix": "Verify github.event.workflow_run.id matches the triggering workflow run_id",
        }
    )

    # Issue 2: Repair saves with different key than it restores
    issues.append(
        {
            "severity": "HIGH",
            "workflow": "repair → validation",
            "issue": "Repair saves with new key",
            "details": (
                "Repair restores: checkpoint-${{ github.event.workflow_run.id }}\n"
                "Repair saves: checkpoint-repaired-${{ github.run_id }}\n"
                "Validation expects: checkpoint-repaired-${{ github.event.workflow_run.id }}\n"
                "The repair run_id is different from the nightly run_id!"
            ),
            "fix": "Validation should use repair workflow run_id, not nightly run_id",
        }
    )

    # Issue 3: Cache restore keys may not match
    issues.append(
        {
            "severity": "MEDIUM",
            "workflow": "all workflows",
            "issue": "Restore keys may be too broad",
            "details": (
                'Using restore-keys with prefixes like "checkpoint-" may restore wrong cache\n'
                "This could lead to using stale or incorrect checkpoints"
            ),
            "fix": "Use more specific restore keys or verify cache timestamp",
        }
    )

    return issues


def print_report(checkpoint_dir: Path):
    """Print comprehensive investigation report."""
    print("=" * 80)
    print("CACHE INVESTIGATION REPORT")
    print("=" * 80)
    print()

    # Section 1: Checkpoint Files
    print("1. CHECKPOINT FILES STATUS")
    print("-" * 80)
    file_status = check_checkpoint_files(checkpoint_dir)

    print(f"Directory: {file_status['directory_path']}")
    print(f"Exists: {'✅ Yes' if file_status['directory_exists'] else '❌ No'}")
    print()

    if file_status["directory_exists"]:
        print("Required Files:")
        for filename, info in file_status["files"].items():
            status = "✅" if info["exists"] and info["size"] > 0 else "❌"
            print(f"  {status} {filename}")
            if info["exists"]:
                print(f"     Size: {format_size(info['size'])}")
                print(f"     Readable: {'✅' if info['readable'] else '❌'}")
                print(f"     Writable: {'✅' if info['writable'] else '❌'}")
                if "warning" in info:
                    print(f"     ⚠️  WARNING: {info['warning']}")
                if "error" in info:
                    print(f"     ❌ ERROR: {info['error']}")
            else:
                print("     ❌ File not found")
            print()

        print(
            f"All Files Present: {'✅ Yes' if file_status['all_present'] else '❌ No'}"
        )
        print(f"Total Size: {format_size(file_status['total_size'])}")
    else:
        print("❌ Checkpoint directory does not exist!")

    print()

    # Section 2: Cache Key Analysis
    print("2. CACHE KEY PATTERNS")
    print("-" * 80)
    cache_patterns = analyze_cache_keys()

    for workflow, patterns in cache_patterns.items():
        print(f"{workflow}:")
        if patterns:
            for pattern in patterns:
                print(f"  - {pattern}")
        else:
            print("  - No cache patterns found")
        print()

    # Section 3: Cache Key Compatibility
    print("3. CACHE KEY COMPATIBILITY ISSUES")
    print("-" * 80)
    issues = check_cache_key_compatibility()

    for i, issue in enumerate(issues, 1):
        severity_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
        emoji = severity_emoji.get(issue["severity"], "⚪")

        print(f"{emoji} Issue #{i}: {issue['issue']}")
        print(f"   Severity: {issue['severity']}")
        print(f"   Workflow: {issue['workflow']}")
        print("   Details:")
        for line in issue["details"].split("\n"):
            print(f"     {line}")
        print(f"   Fix: {issue['fix']}")
        print()

    # Section 4: Recommendations
    print("4. RECOMMENDATIONS")
    print("-" * 80)

    recommendations = []

    if not file_status["directory_exists"]:
        recommendations.append(
            "❌ CRITICAL: Checkpoint directory missing\n"
            "   → Run nightly collection workflow to create checkpoint"
        )
    elif not file_status["all_present"]:
        recommendations.append(
            "❌ CRITICAL: Some checkpoint files missing or empty\n"
            "   → Verify checkpoint save logic in nightly collection\n"
            "   → Check for errors during checkpoint creation"
        )
    else:
        recommendations.append("✅ All checkpoint files present and valid")

    recommendations.append(
        "🔧 FIX: Update validation workflow cache key\n"
        "   → Change from: checkpoint-repaired-${{ github.event.workflow_run.id }}\n"
        "   → Change to: checkpoint-repaired-${{ github.event.workflow_run.id }}\n"
        "   → But use the REPAIR workflow run_id, not the nightly run_id"
    )

    recommendations.append(
        "🔧 FIX: Add cache verification after save\n"
        "   → Verify all three files present after cache save\n"
        "   → Add checksums or file size verification\n"
        "   → Fail workflow if cache save incomplete"
    )

    recommendations.append(
        "🔧 FIX: Prioritize permanent storage over cache\n"
        "   → Always upload to permanent storage first\n"
        "   → Use cache only as secondary backup\n"
        "   → Warn if only cache save succeeds (7-day retention risk)"
    )

    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
        print()

    print("=" * 80)
    print("END OF REPORT")
    print("=" * 80)


def main():
    """Main entry point."""
    # Default checkpoint directory
    checkpoint_dir = Path("data/freesound_library")

    # Allow override from command line
    if len(sys.argv) > 1:
        checkpoint_dir = Path(sys.argv[1])

    print_report(checkpoint_dir)

    # Exit with error if critical issues found
    file_status = check_checkpoint_files(checkpoint_dir)
    if not file_status["directory_exists"] or not file_status["all_present"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
