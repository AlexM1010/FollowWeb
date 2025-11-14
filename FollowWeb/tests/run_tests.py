#!/usr/bin/env python3
"""
Comprehensive test runner for FollowWeb - runs all CI checks locally.

This script replicates the full CI pipeline locally, including:
- Code quality checks (formatting, linting, type checking)
- Security scans (bandit, pip-audit)
- Unit tests (parallel)
- Integration tests (parallel)
- Performance tests (sequential)
- Benchmark tests (sequential)
- Package building and validation

Usage:
    python run_tests.py all                    # Run all checks (full CI pipeline)
    python run_tests.py all --autofix          # Run all checks with auto-fix
    python run_tests.py fix                    # ONLY auto-fix code issues (no checks)
    python run_tests.py unit                   # Run unit tests only
    python run_tests.py integration            # Run integration tests only
    python run_tests.py performance            # Run performance tests only
    python run_tests.py benchmark              # Run benchmark tests only
    python run_tests.py quality                # Run quality checks only
    python run_tests.py quality --autofix      # Run quality checks with auto-fix
    python run_tests.py security               # Run security scans only
    python run_tests.py build                  # Run package build only

Options:
    --autofix    Automatically fix formatting and linting issues (ruff format + ruff check --fix)
"""

import os
import subprocess
import sys
from pathlib import Path

# Global flag for autofix mode
AUTOFIX_MODE = False


def run_command(cmd, description, check=True, cwd=None):
    """Run a command and print status."""
    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"{'=' * 80}")
    result = subprocess.run(cmd, shell=True, check=False, cwd=cwd)
    if check and result.returncode != 0:
        print(f"\n[FAIL] {description}")
        return False
    print(f"\n[PASS] {description}")
    return True


def run_autofix_only():
    """Run auto-fixes without any checks."""
    print("\n" + "=" * 80)
    print("AUTO-FIX CODE ISSUES (NO CHECKS)")
    print("=" * 80)
    
    fixes = [
        ("ruff format FollowWeb_Visualizor tests", "Auto-fix formatting"),
        ("ruff check --fix FollowWeb_Visualizor tests", "Auto-fix linting"),
        ("ruff check --fix --select I FollowWeb_Visualizor tests", "Auto-fix import sorting"),
    ]
    
    all_passed = True
    for cmd, desc in fixes:
        if not run_command(cmd, desc, check=False):
            all_passed = False
    
    if all_passed:
        print("\n" + "=" * 80)
        print("[SUCCESS] All auto-fixes applied successfully!")
        print("=" * 80)
        print("\nRun 'python tests/run_tests.py quality' to verify fixes.")
    
    return all_passed


def run_quality_checks():
    """Run code quality checks (formatting, linting, type checking)."""
    print("\n" + "=" * 80)
    print("QUALITY CHECKS")
    if AUTOFIX_MODE:
        print("(AUTOFIX MODE ENABLED)")
    print("=" * 80)

    # Auto-fix formatting and linting if requested
    if AUTOFIX_MODE:
        print("\n" + "=" * 80)
        print("AUTO-FIXING CODE ISSUES")
        print("=" * 80)
        
        # Fix formatting
        run_command(
            "ruff format FollowWeb_Visualizor tests",
            "Auto-fix formatting",
            check=False,
        )
        
        # Fix linting issues
        run_command(
            "ruff check --fix FollowWeb_Visualizor tests",
            "Auto-fix linting",
            check=False,
        )
        
        # Fix import sorting
        run_command(
            "ruff check --fix --select I FollowWeb_Visualizor tests",
            "Auto-fix import sorting",
            check=False,
        )
        
        print("\n" + "=" * 80)
        print("VERIFYING FIXES")
        print("=" * 80)

    checks = [
        (
            "ruff format --check FollowWeb_Visualizor tests --diff",
            "Code formatting check",
        ),
        ("ruff check FollowWeb_Visualizor tests", "Linting check"),
        ("ruff check --select I FollowWeb_Visualizor tests", "Import sorting check"),
        ("mypy FollowWeb_Visualizor --show-error-codes", "Type checking"),
    ]

    all_passed = True
    for cmd, desc in checks:
        if not run_command(cmd, desc, check=True):
            all_passed = False
            if not AUTOFIX_MODE:
                # Only break if not in autofix mode
                break

    return all_passed


def run_security_checks():
    """Run security scans (bandit, pip-audit)."""
    print("\n" + "=" * 80)
    print("SECURITY CHECKS")
    print("=" * 80)

    checks = [
        (
            "bandit -r FollowWeb_Visualizor --severity-level medium",
            "Bandit security scan (medium/high severity)",
        ),
        ("pip-audit --desc", "pip-audit vulnerability scan"),
    ]

    all_passed = True
    for cmd, desc in checks:
        if not run_command(cmd, desc, check=True):
            all_passed = False
            break

    return all_passed


def run_unit_tests():
    """Run unit tests in parallel."""
    print("\n" + "=" * 80)
    print("UNIT TESTS")
    print("=" * 80)

    cpu_count = os.cpu_count() or 1
    cmd = f"{sys.executable} -m pytest -p no:benchmark -m unit -n {cpu_count} -v"
    return run_command(cmd, f"Unit tests (parallel with {cpu_count} workers)")


def run_integration_tests():
    """Run integration tests in parallel."""
    print("\n" + "=" * 80)
    print("INTEGRATION TESTS")
    print("=" * 80)

    cpu_count = os.cpu_count() or 1
    cmd = f"{sys.executable} -m pytest -p no:benchmark -m integration -n {cpu_count} -v"
    return run_command(cmd, f"Integration tests (parallel with {cpu_count} workers)")


def run_performance_tests():
    """Run performance tests sequentially."""
    print("\n" + "=" * 80)
    print("PERFORMANCE TESTS")
    print("=" * 80)

    cmd = f"{sys.executable} -m pytest -m 'slow or performance' -n 0 -v"
    return run_command(cmd, "Performance tests (sequential)")


def run_benchmark_tests():
    """Run benchmark tests sequentially."""
    print("\n" + "=" * 80)
    print("BENCHMARK TESTS")
    print("=" * 80)

    # Create benchmarks directory
    Path(".benchmarks").mkdir(exist_ok=True)

    cmd = f"{sys.executable} -m pytest -m benchmark -n 0 -v --benchmark-save=local_run --benchmark-save-data --benchmark-storage=.benchmarks"
    return run_command(cmd, "Benchmark tests (sequential)")


def run_package_build():
    """Run package build and validation."""
    print("\n" + "=" * 80)
    print("PACKAGE BUILD")
    print("=" * 80)

    # Clean build artifacts
    print("\nCleaning build artifacts...")
    for path in ["build", "dist", "*.egg-info"]:
        subprocess.run(f"rm -rf {path}", shell=True, check=False)

    checks = [
        ("check-manifest --verbose", "Package manifest check"),
        (f"{sys.executable} -m build --sdist --wheel --outdir dist/", "Package build"),
        ("twine check dist/*", "Package integrity check"),
    ]

    all_passed = True
    for cmd, desc in checks:
        if not run_command(cmd, desc, check=True):
            all_passed = False
            break

    return all_passed


def run_all_checks():
    """Run all CI checks in order."""
    print("\n" + "=" * 80)
    print("RUNNING FULL CI PIPELINE LOCALLY")
    print("=" * 80)

    checks = [
        ("Quality Checks", run_quality_checks),
        ("Security Checks", run_security_checks),
        ("Unit Tests", run_unit_tests),
        ("Integration Tests", run_integration_tests),
        ("Performance Tests", run_performance_tests),
        ("Benchmark Tests", run_benchmark_tests),
        ("Package Build", run_package_build),
    ]

    results = {}
    for name, func in checks:
        results[name] = func()
        if not results[name]:
            print(f"\n[FAIL] {name}")
            print("\nStopping pipeline due to failure.")
            break

    # Print summary
    print("\n" + "=" * 80)
    print("CI PIPELINE SUMMARY")
    print("=" * 80)
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {name}")

    all_passed = all(results.values())
    if all_passed:
        print("\n[SUCCESS] ALL CHECKS PASSED!")
        return 0
    else:
        print("\n[FAILURE] SOME CHECKS FAILED")
        return 1


def main():
    """Run tests based on command line arguments."""
    global AUTOFIX_MODE
    
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    # Check for --autofix flag
    if "--autofix" in sys.argv:
        AUTOFIX_MODE = True
        sys.argv.remove("--autofix")

    command = sys.argv[1].lower()

    # Set environment variables
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)

    if command == "fix":
        return 0 if run_autofix_only() else 1
    elif command == "all":
        return run_all_checks()
    elif command == "unit":
        return 0 if run_unit_tests() else 1
    elif command == "integration":
        return 0 if run_integration_tests() else 1
    elif command == "performance":
        return 0 if run_performance_tests() else 1
    elif command == "benchmark":
        return 0 if run_benchmark_tests() else 1
    elif command == "quality":
        return 0 if run_quality_checks() else 1
    elif command == "security":
        return 0 if run_security_checks() else 1
    elif command == "build":
        return 0 if run_package_build() else 1
    else:
        # Pass through to pytest for custom commands
        has_benchmark = any(
            arg in ["-m", "benchmark"] or "benchmark" in arg for arg in sys.argv[1:]
        )

        if has_benchmark:
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
