#!/usr/bin/env python3
"""
Minimal test runner for FollowWeb - handles benchmark isolation only.

Use pytest directly for most cases. This script only exists to handle the
pytest-benchmark + pytest-xdist incompatibility.
"""

import os
import subprocess
import sys


def main():
    """Run tests with benchmark isolation if needed."""

    # Check if we're running benchmarks
    has_benchmark = any(
        arg in ["-m", "benchmark"] or "benchmark" in arg for arg in sys.argv[1:]
    )

    # Check if running "all" tests
    run_all = len(sys.argv) > 1 and sys.argv[1] == "all"

    if run_all:
        # Run non-benchmark tests in parallel, then benchmarks sequentially
        print("Running non-benchmark tests in parallel...")
        result1 = subprocess.run(
            [sys.executable, "-m", "pytest", "-m", "not benchmark"] + sys.argv[2:],
            check=False,
        )

        print("\nRunning benchmark tests sequentially...")
        result2 = subprocess.run(
            [sys.executable, "-m", "pytest", "-m", "benchmark", "-n", "0"]
            + sys.argv[2:],
            check=False,
        )

        return result1.returncode or result2.returncode

    elif has_benchmark:
        # Force sequential execution for benchmarks
        args = [arg for arg in sys.argv[1:] if not arg.startswith("-n")]
        return subprocess.run(
            [sys.executable, "-m", "pytest"] + args + ["-n", "0"], check=False
        ).returncode

    else:
        # Pass through to pytest directly
        return subprocess.run(
            [sys.executable, "-m", "pytest"] + sys.argv[1:], check=False
        ).returncode


if __name__ == "__main__":
    sys.exit(main())
