"""
Test required and optional dependency availability.

These tests verify that required dependencies are installed and check
optional dependencies for informational purposes.
"""

import pytest


class TestDependencies:
    """Test availability of dependencies."""

    def test_pymetis_required(self):
        """
        Test that pymetis is installed (required dependency on Unix/Linux/macOS).

        pymetis is required for fast graph partitioning using the METIS algorithm.
        On Windows, pymetis is not available and graph partitioning is not supported.
        """
        import sys

        if sys.platform == "win32":
            print("\n⚠ pymetis is not available on Windows (Unix/Linux/macOS only)")
            print("  Graph partitioning features are not supported on Windows")
            pytest.skip("pymetis not available on Windows")
        else:
            try:
                import pymetis  # noqa: F401

                print("\n✓ pymetis is installed")
                print(
                    "  Using fast METIS partitioning (10-100x faster for large graphs)"
                )
                assert True
            except ImportError:
                pytest.fail(
                    "pymetis is not installed but is required on Unix/Linux/macOS.\n"
                    "Install with: pip install pymetis\n"
                    "See requirements.txt or README.md for platform-specific instructions."
                )

    def test_nx_parallel_availability(self):
        """
        Test if nx-parallel is available (informational).

        nx-parallel provides parallel processing for NetworkX operations
        and is only available on Python 3.11+.
        """
        import sys

        if sys.version_info >= (3, 11):
            try:
                import nx_parallel  # noqa: F401

                print(
                    "\n✓ nx-parallel is available - parallel NetworkX operations enabled"
                )
                assert True
            except ImportError:
                print("\n⚠ nx-parallel not available (Python 3.11+ only)")
                print("  Install with: pip install nx-parallel")
                assert True
        else:
            print(
                f"\n⚠ nx-parallel requires Python 3.11+ (current: {sys.version_info.major}.{sys.version_info.minor})"
            )
            pytest.skip("nx-parallel requires Python 3.11+")

    def test_dependencies_report(self):
        """Generate a report of all dependencies."""
        import sys

        # pymetis is only required on Unix/Linux/macOS, not on Windows
        pymetis_required = sys.platform != "win32"

        dependencies = {
            "pymetis": {
                "purpose": "Fast graph partitioning using METIS algorithm",
                "required": pymetis_required,
                "python_version": "any",
                "platform": "Unix/Linux/macOS only",
            },
            "nx_parallel": {
                "purpose": "Parallel NetworkX operations",
                "required": False,
                "python_version": "3.11+",
                "platform": "all",
            },
        }

        print("\n" + "=" * 70)
        print("Dependencies Report")
        print("=" * 70)

        all_installed = True
        for dep_name, info in dependencies.items():
            try:
                __import__(dep_name)
                status = "✓ INSTALLED"
            except ImportError:
                status = "✗ NOT INSTALLED"
                if info["required"]:
                    all_installed = False

            print(f"\n{dep_name}:")
            print(f"  Status: {status}")
            print(f"  Purpose: {info['purpose']}")
            print(f"  Required: {'Yes' if info['required'] else 'No'}")
            print(f"  Python: {info['python_version']}")
            print(f"  Platform: {info['platform']}")

        print("\n" + "=" * 70)

        if not all_installed:
            print("⚠ Some required dependencies are missing!")
            print("  Install with: pip install -r requirements.txt")
        else:
            print("✓ All required dependencies are installed")

        print("=" * 70)

        assert all_installed, "Required dependencies are missing"
