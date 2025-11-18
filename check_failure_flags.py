#!/usr/bin/env python3
"""
Check for failure flags before workflow execution.

This script checks if an upstream workflow has set a failure flag,
and if so, skips execution and logs the reason.

Usage:
    python check_failure_flags.py [--checkpoint-dir DIR]

Exit codes:
    0 - No failure flag, proceed with execution
    1 - Failure flag found, skip execution
    2 - Error checking failure flag
"""

import argparse
import json
import sys
from pathlib import Path


def check_failure_flag(checkpoint_dir: Path) -> tuple[bool, str]:
    """
    Check if a failure flag exists.
    
    Args:
        checkpoint_dir: Directory containing failure flags
        
    Returns:
        Tuple of (flag_exists: bool, skip_reason: str)
    """
    flag_file = checkpoint_dir / "failure_flags.json"
    
    if not flag_file.exists():
        return False, ""
    
    try:
        with open(flag_file) as f:
            flag_data = json.load(f)
        
        workflow_name = flag_data.get("workflow_name", "unknown")
        error_message = flag_data.get("error_message", "unknown error")
        timestamp = flag_data.get("timestamp", "unknown time")
        data_preserved = flag_data.get("data_preserved", False)
        
        skip_reason = (
            f"Skipping execution due to upstream failure in {workflow_name}\n"
            f"Error: {error_message}\n"
            f"Time: {timestamp}\n"
            f"Data preserved: {data_preserved}"
        )
        
        return True, skip_reason
        
    except Exception as e:
        return False, f"Error reading failure flag: {e}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for failure flags before workflow execution"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("data/freesound_library"),
        help="Directory containing failure flags (default: data/freesound_library)"
    )
    
    args = parser.parse_args()
    
    # Check for failure flag
    flag_exists, skip_reason = check_failure_flag(args.checkpoint_dir)
    
    if flag_exists:
        print("❌ FAILURE FLAG DETECTED")
        print("")
        print(skip_reason)
        print("")
        print("To clear the flag and resume execution:")
        print(f"  rm {args.checkpoint_dir / 'failure_flags.json'}")
        
        # Write to GitHub Actions step summary if available
        summary_file = Path(os.environ.get("GITHUB_STEP_SUMMARY", ""))
        if summary_file:
            try:
                with open(summary_file, "a") as f:
                    f.write("## ❌ Workflow Skipped\n\n")
                    f.write(f"```\n{skip_reason}\n```\n\n")
                    f.write("### To Resume\n\n")
                    f.write(f"Clear the failure flag: `rm {args.checkpoint_dir / 'failure_flags.json'}`\n")
            except Exception:
                pass
        
        sys.exit(1)
    else:
        print("✅ No failure flag detected, proceeding with execution")
        sys.exit(0)


if __name__ == "__main__":
    import os
    main()
