#!/usr/bin/env python3
"""
Consolidated test runner for FollowWeb with safe resource management and benchmark support.

This script provides a unified interface for running all types of tests with proper
resource management, preventing pytest-benchmark + xdist conflicts, and supporting
both local development and CI environments.
"""

import os
import platform
import subprocess
import sys
from typing import List, Optional

import psutil


def get_system_info() -> dict:
    """Get system resource information."""
    try:
        memory_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_physical = psutil.cpu_count(logical=False)

        # Get available memory (more conservative)
        available_memory_gb = psutil.virtual_memory().available / (1024**3)

        return {
            "platform": platform.system(),
            "cpu_count": cpu_count,
            "cpu_physical": cpu_physical,
            "memory_gb": memory_gb,
            "available_memory_gb": available_memory_gb,
            "is_windows": platform.system() == "Windows",
            "is_ci": os.getenv("CI", "").lower() in ("true", "1", "yes"),
        }
    except Exception:
        # Fallback to conservative defaults if psutil fails
        return {
            "platform": platform.system(),
            "cpu_count": 4,
            "cpu_physical": 2,
            "memory_gb": 8,
            "available_memory_gb": 4,
            "is_windows": platform.system() == "Windows",
            "is_ci": os.getenv("CI", "").lower() in ("true", "1", "yes"),
        }


def get_safe_worker_count(test_type: str = "default") -> int:
    """
    Calculate optimal number of workers based on system resources and test type.

    Args:
        test_type: Type of tests ('unit', 'integration', 'performance', 'default')

    Returns:
        Optimal number of workers
    """
    info = get_system_info()

    # Performance tests should match GitHub CI environment (ubuntu-latest = 2 cores)
    if test_type == "performance":
        if info["is_ci"]:
            return 2  # Match GitHub Actions ubuntu-latest
        else:
            return 2  # Keep consistent with CI for performance tests

    # For all other tests: use cores - 1 (leave one core for system)
    cpu_workers = max(1, info["cpu_count"] - 1)
    memory_workers = max(1, int(info["available_memory_gb"] / 0.5))  # 500MB per worker

    # For unit tests, prioritize CPU cores (they're lightweight)
    if test_type == "unit":
        optimal_workers = cpu_workers  # Use cores-1 directly for unit tests
    else:
        # For integration and mixed tests, consider memory constraints
        type_multipliers = {
            "integration": 0.75,  # Integration tests need more resources per test
            "default": 0.85,  # Mixed tests
        }

        multiplier = type_multipliers.get(test_type, 0.85)

        # Calculate final worker count (memory or CPU constrained)
        base_workers = min(cpu_workers, memory_workers)
        optimal_workers = max(1, int(base_workers * multiplier))

    return optimal_workers


def cleanup_processes():
    """Clean up any stuck pytest processes."""
    # Disabled cleanup to prevent killing the current process
    # This was causing the test runner to exit prematurely on Windows
    pass


def run_benchmarks() -> int:
    """Run benchmark tests with proper configuration."""

    # Build command that runs benchmarks sequentially
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "benchmark",
        "-v",
        "--tb=short",
        "--benchmark-sort=mean",
        "--benchmark-columns=min,max,mean,stddev,rounds,iterations",
        "-n",
        "0",  # Force sequential execution
        "-rw",  # Show warnings summary
    ]

    print("Running benchmark tests (sequential execution, no parallelization)")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nBenchmark execution interrupted by user")
        return 130
    except Exception as e:
        print(f"Error running benchmarks: {e}")
        return 1


def run_all_tests_optimally(extra_args: List[str]) -> int:
    """Run all tests with optimal execution: parallel tests first, then sequential benchmarks."""

    print("Running all tests with optimal execution strategy...")
    print("=" * 60)

    total_failures = 0

    try:
        # Phase 1: Run all non-benchmark tests in parallel
        print("Phase 1: Running regular tests in parallel...")
        print("-" * 40)

        regular_args = ["-m", "not benchmark"] + extra_args
        regular_result = run_tests_safely(regular_args, "default")

        if regular_result != 0:
            total_failures += regular_result
            print(f"[FAIL] Regular tests failed with exit code: {regular_result}")
        else:
            print("[PASS] Regular tests passed!")

        print("\n" + "=" * 60)

        # Phase 2: Run benchmark tests sequentially
        print("Phase 2: Running benchmark tests sequentially...")
        print("-" * 40)

        benchmark_result = run_benchmarks()

        if benchmark_result != 0:
            total_failures += benchmark_result
            print(f"[FAIL] Benchmark tests failed with exit code: {benchmark_result}")
        else:
            print("[PASS] Benchmark tests passed!")

        print("\n" + "=" * 60)

        # Final summary
        if total_failures == 0:
            print(
                "[SUCCESS] All tests passed! (Regular tests: parallel, Benchmark tests: sequential)"
            )
        else:
            print(f"[FAIL] Some tests failed (Total failure codes: {total_failures})")

        return total_failures

    except KeyboardInterrupt:
        print("\n[WARN] Tests interrupted by user")

        return 130
    except Exception as e:
        print(f"[ERROR] Error running tests: {e}")

        return 1


def run_tests_safely(test_args: List[str], test_type: Optional[str] = None) -> int:
    """Run tests with safe resource management."""

    # Detect test type from arguments if not specified
    if test_type is None:
        if any(
            "-m" in test_args and "benchmark" in test_args[i + 1]
            for i, arg in enumerate(test_args[:-1])
            if arg == "-m"
        ):
            test_type = "benchmark"
        elif any(
            "-m" in test_args and "unit" in test_args[i + 1]
            for i, arg in enumerate(test_args[:-1])
            if arg == "-m"
        ):
            test_type = "unit"
        elif any(
            "-m" in test_args and "integration" in test_args[i + 1]
            for i, arg in enumerate(test_args[:-1])
            if arg == "-m"
        ):
            test_type = "integration"
        elif any(
            "-m" in test_args
            and ("slow" in test_args[i + 1] or "performance" in test_args[i + 1])
            for i, arg in enumerate(test_args[:-1])
            if arg == "-m"
        ):
            test_type = "performance"
        else:
            test_type = "default"

    # Handle benchmark tests specially
    if test_type == "benchmark":
        return run_benchmarks()

    # Check if parallel execution is already specified
    has_xdist = any(arg.startswith("-n") for arg in test_args)

    # Add appropriate worker count if not specified
    if not has_xdist:
        worker_count = get_safe_worker_count(test_type)
        if test_type == "performance":
            # Force sequential execution for performance tests
            test_args.extend(["-n", "0"])
        else:
            test_args.extend(["-n", str(worker_count)])
            print(f"Using {worker_count} workers for {test_type} tests")

    # Build command with safety options
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--maxfail=5",  # Stop after 5 failures
        "--tb=short",  # Short traceback format
        "-v",  # Verbose output
        "-rw",  # Show warnings summary
    ] + test_args

    print(f"Running: {' '.join(cmd)}")

    # Run the tests
    try:
        result = subprocess.run(cmd, check=False, capture_output=False, text=True)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")

        return 130
    except Exception as e:
        print(f"Error running tests: {e}")

        return 1


def main():
    """Main entry point with command parsing."""
    if len(sys.argv) < 2:
        print("FollowWeb Test Runner")
        print("Usage: python run_tests.py <command> [pytest arguments]")
        print()
        print("Commands:")
        print("  all                      - Run all tests with optimal parallelization")
        print("  unit                     - Run unit tests only")
        print("  integration              - Run integration tests only")
        print("  performance              - Run performance tests only (sequential)")
        print("  benchmark                - Run benchmark tests (sequential)")
        print("  sequential               - Run all tests sequentially")
        print("  debug                    - Run tests with debug output")
        print("  system-info              - Show system resources and worker counts")
        print()
        print("Examples:")
        print("  python run_tests.py unit")
        print("  python run_tests.py benchmark")
        print("  python run_tests.py all --collect-only")
        print("  python run_tests.py integration -k test_pipeline")
        return 0

    command = sys.argv[1]
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else []

    if command == "system-info":
        info = get_system_info()
        print("System Resource Information:")
        print(f"  Platform: {info['platform']}")
        print(f"  CPU Count: {info['cpu_count']} ({info['cpu_physical']} physical)")
        print(
            f"  Memory: {info['memory_gb']:.1f} GB total, {info['available_memory_gb']:.1f} GB available"
        )
        print(f"  Windows: {info['is_windows']}")
        print(f"  CI Environment: {info['is_ci']}")
        print()
        print("Recommended worker counts:")
        for test_type in ["unit", "integration", "performance", "default"]:
            workers = get_safe_worker_count(test_type)
            print(f"  {test_type}: {workers} workers")
        return 0

    elif command == "all":
        return run_all_tests_optimally(extra_args)

    elif command == "unit":
        test_args = ["-m", "unit"] + extra_args
        return run_tests_safely(test_args, "unit")

    elif command == "integration":
        test_args = ["-m", "integration"] + extra_args
        return run_tests_safely(test_args, "integration")

    elif command == "performance":
        test_args = ["-m", "slow"] + extra_args
        return run_tests_safely(test_args, "performance")

    elif command == "benchmark":
        return run_benchmarks()

    elif command == "sequential":
        test_args = ["-n", "0"] + extra_args
        return run_tests_safely(test_args, "sequential")

    elif command == "debug":
        test_args = ["--tb=long", "-s"] + extra_args
        return run_tests_safely(test_args, "default")

    else:
        print(f"Unknown command: {command}")
        print("Use 'python run_tests.py' without arguments to see available commands.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
