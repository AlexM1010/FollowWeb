#!/usr/bin/env python3
"""
Clear failure flags after successful workflow execution.

This script clears failure flags after a workflow completes successfully,
allowing downstream workflows to resume execution.

Usage:
    python clear_failure_flags.py [--checkpoint-dir DIR]

Exit codes:
    0 - Success
    1 - Error clearing flag
"""

import argparse
import sys
from pathlib import Path


def clear_failure_flag(checkpoint_dir: Path) -> tuple[bool, str]:
    """
    Clear the failure flag.
    
    Args:
        checkpoint_dir: Directory containing failure flags
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    flag_file = checkpoint_dir / "failure_flags.json"
    
    if not flag_file.exists():
        return True, "No failure flag to clear"
    
    try:
        flag_file.unlink()
        return True, "Failure flag cleared successfully"
    except Exception as e:
        return False, f"Failed to clear failure flag: {e}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clear failure flags after successful workflow execution"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("data/freesound_library"),
        help="Directory containing failure flags (default: data/freesound_library)"
    )
    
    args = parser.parse_args()
    
    # Clear failure flag
    success, message = clear_failure_flag(args.checkpoint_dir)
    
    if success:
        print(f"✅ {message}")
        
        # Write to GitHub Actions step summary if available
        import os
        summary_file = Path(os.environ.get("GITHUB_STEP_SUMMARY", ""))
        if summary_file:
            try:
                with open(summary_file, "a") as f:
                    f.write("## ✅ Failure Flag Cleared\n\n")
                    f.write("Downstream workflows can now resume execution.\n")
            except Exception:
                pass
        
        sys.exit(0)
    else:
        print(f"❌ {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
