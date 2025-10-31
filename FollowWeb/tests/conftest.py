"""
Pytest configuration and shared fixtures for FollowWeb tests.

This module provides common fixtures, test configuration, and utilities
used across the test suite.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

from FollowWeb_Visualizor.core.config import get_configuration_manager

# Add the FollowWeb_Visualizor package to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Cache for dataset summary to avoid repeated file reads
_dataset_summary_cache = None


def _load_dataset_summary() -> Dict[str, Any]:
    """Load and cache dataset summary for efficient access."""
    global _dataset_summary_cache

    if _dataset_summary_cache is not None:
        return _dataset_summary_cache

    from pathlib import Path

    summary_path = Path("tests") / "test_data" / "dataset_summary.json"
    if not summary_path.exists():
        _dataset_summary_cache = {}
        return _dataset_summary_cache

    try:
        with summary_path.open("r") as f:
            _dataset_summary_cache = json.load(f)
        return _dataset_summary_cache
    except Exception as e:
        print(f"Warning: Could not load dataset summary: {e}")
        _dataset_summary_cache = {}
        return _dataset_summary_cache


def calculate_appropriate_k_values(dataset_name: str = "small_real") -> Dict[str, Any]:
    """
    Calculate appropriate k-values based on dataset summary statistics.

    This function calculates k-values that are:
    1. Appropriate for the dataset size (not too high to result in empty graphs)
    2. Meaningful for testing (not too low to be trivial)
    3. Different for different strategies to test various scenarios
    4. Efficient (uses cached dataset summary)

    Args:
        dataset_name: Name of dataset from dataset_summary.json

    Returns:
        Dictionary with strategy_k_values and default_k_value
    """
    # Load cached dataset summary
    summary = _load_dataset_summary()

    # Get dataset stats with safe defaults
    dataset_info = summary.get("datasets", {}).get(dataset_name, {})
    stats = dataset_info.get("stats", {})
    graph_analysis = stats.get("graph_analysis", {})
    degree_dist = graph_analysis.get("degree_distribution", {})
    graph_struct = graph_analysis.get("graph_structure", {})

    # Extract key metrics with safe defaults
    max_degree = degree_dist.get("max_in_degree", 10)
    avg_degree = degree_dist.get("avg_in_degree", 5.0)
    nodes = graph_struct.get("nodes", 10)
    density = graph_struct.get("density", 0.5)
    reciprocity = graph_struct.get("reciprocity", 0.8)

    # Calculate base k-value using multiple factors for robustness
    # Factor 1: Degree-based calculation (30-50% of max degree)
    degree_based_k = max(1, int(max_degree * 0.4))

    # Factor 2: Average degree consideration (avoid too high k-values)
    avg_based_k = max(1, int(avg_degree * 1.2))

    # Factor 3: Density-based adjustment (denser graphs can handle higher k)
    density_factor = min(2.0, max(0.5, density * 2))
    density_adjusted_k = max(1, int(avg_degree * density_factor))

    # Use the minimum of these factors to ensure meaningful results
    base_k = min(degree_based_k, avg_based_k, density_adjusted_k)

    # Apply dataset size-based constraints for optimal test performance
    if nodes <= 10:  # Small dataset - conservative k-values
        k_core = max(1, min(base_k, 3))
        k_reciprocal = max(1, min(base_k - 1, 2))
        k_ego = max(1, min(base_k - 1, 2))
    elif nodes <= 25:  # Medium dataset - moderate k-values
        k_core = max(2, min(base_k, 6))
        k_reciprocal = max(1, min(base_k - 1, 4))
        k_ego = max(1, min(base_k - 1, 4))
    else:  # Large dataset - higher k-values allowed
        k_core = max(3, min(base_k, 10))
        k_reciprocal = max(2, min(base_k - 1, 7))
        k_ego = max(2, min(base_k - 1, 7))

    # Apply reciprocity-based adjustment for reciprocal strategy
    if reciprocity > 0.8:  # High reciprocity allows higher k for reciprocal strategy
        k_reciprocal = min(k_reciprocal + 1, k_core)

    return {
        "strategy_k_values": {
            "k-core": k_core,
            "reciprocal_k-core": k_reciprocal,
            "ego_alter_k-core": k_ego,
        },
        "default_k_value": k_core,
    }


def get_scalability_k_values(dataset_name: str = "full_anonymized") -> Dict[str, Any]:
    """
    Get higher k-values for testing future scalability.

    These k-values may result in small/empty graphs with current datasets
    but test the system's ability to handle larger future datasets.
    Uses intelligent scaling based on dataset characteristics.

    Args:
        dataset_name: Name of dataset from dataset_summary.json

    Returns:
        Dictionary with higher k-values for scalability testing
    """
    base_k_values = calculate_appropriate_k_values(dataset_name)

    # Load dataset info for intelligent scaling
    summary = _load_dataset_summary()
    dataset_info = summary.get("datasets", {}).get(dataset_name, {})
    stats = dataset_info.get("stats", {})
    graph_analysis = stats.get("graph_analysis", {})
    degree_dist = graph_analysis.get("degree_distribution", {})

    # Get max degree for intelligent scaling
    max_degree = degree_dist.get("max_in_degree", 10)
    nodes = graph_analysis.get("graph_structure", {}).get("nodes", 10)

    # Calculate scalability multiplier based on dataset characteristics
    # Larger datasets can handle higher multipliers
    if nodes <= 10:
        multiplier = 2  # Conservative for small datasets
    elif nodes <= 25:
        multiplier = 3  # Moderate for medium datasets
    else:
        multiplier = 4  # Aggressive for large datasets

    # Ensure scalability k-values don't exceed reasonable bounds
    # (even for future datasets, extremely high k-values are not practical)
    max_reasonable_k = min(50, max_degree)  # Cap at 50 or max_degree

    base_k_core = base_k_values["strategy_k_values"]["k-core"]
    base_k_reciprocal = base_k_values["strategy_k_values"]["reciprocal_k-core"]
    base_k_ego = base_k_values["strategy_k_values"]["ego_alter_k-core"]

    return {
        "strategy_k_values": {
            "k-core": min(base_k_core * multiplier, max_reasonable_k),
            "reciprocal_k-core": min(base_k_reciprocal * multiplier, max_reasonable_k),
            "ego_alter_k-core": min(base_k_ego * multiplier, max_reasonable_k),
        },
        "default_k_value": min(
            base_k_values["default_k_value"] * multiplier, max_reasonable_k
        ),
    }


@pytest.fixture
def sample_data_file() -> str:
    """Fixture providing path to sample data file - using tiny test dataset for fastest tests."""
    from pathlib import Path

    return str(Path("tests") / "test_data" / "tiny_real.json")


@pytest.fixture
def sample_data_exists(sample_data_file: str) -> bool:
    """Fixture checking if sample data file exists."""
    return os.path.exists(sample_data_file)


@pytest.fixture
def tiny_real_data() -> str:
    """Fixture providing tiny real test dataset for very fast testing (5% of original data)."""
    from pathlib import Path

    return str(Path("tests") / "test_data" / "tiny_real.json")


@pytest.fixture
def small_real_data() -> str:
    """Fixture providing small real test dataset for fast testing (15% of original data)."""
    from pathlib import Path

    return str(Path("tests") / "test_data" / "small_real.json")


@pytest.fixture
def medium_real_data() -> str:
    """Fixture providing medium real test dataset for integration testing (33% of original data)."""
    from pathlib import Path

    return str(Path("tests") / "test_data" / "medium_real.json")


@pytest.fixture
def large_real_data() -> str:
    """Fixture providing large real test dataset for performance testing (66% of original data)."""
    from pathlib import Path

    return str(Path("tests") / "test_data" / "large_real.json")


@pytest.fixture
def full_test_data() -> str:
    """Fixture providing full anonymized dataset for comprehensive testing (100% of original data)."""
    from pathlib import Path

    return str(Path("tests") / "test_data" / "full_anonymized.json")


@pytest.fixture
def tiny_test_data(tiny_real_data: str) -> str:
    """Fixture providing tiny test dataset (alias for tiny_real_data)."""
    return tiny_real_data


@pytest.fixture
def small_test_data(small_real_data: str) -> str:
    """Fixture providing small test dataset (alias for small_real_data)."""
    return small_real_data


@pytest.fixture
def medium_test_data(medium_real_data: str) -> str:
    """Fixture providing medium test dataset (alias for medium_real_data)."""
    return medium_real_data


@pytest.fixture
def large_test_data(large_real_data: str) -> str:
    """Fixture providing large test dataset (alias for large_real_data)."""
    return large_real_data


@pytest.fixture
def test_data_exists(small_real_data: str) -> bool:
    """Fixture checking if test data files exist."""
    return os.path.exists(small_real_data)


@pytest.fixture
def default_config() -> Dict[str, Any]:
    """Fixture providing default configuration using ConfigurationManager."""
    config_manager = get_configuration_manager()
    config = config_manager.load_configuration()
    return config_manager.serialize_configuration(config)


@pytest.fixture
def temp_output_dir(request) -> Generator[str, None, None]:
    """Fixture providing temporary output directory with worker isolation in tests/Output."""
    # Get worker ID for parallel execution isolation
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")

    # Create test output directory in tests/Output instead of system temp
    test_output_base = Path("tests") / "Output"
    test_output_base.mkdir(parents=True, exist_ok=True)

    # Create worker-specific subdirectory
    temp_dir = test_output_base / f"test_{worker_id}_{os.getpid()}"
    temp_dir.mkdir(exist_ok=True)

    try:
        yield str(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_dir_path(request) -> Generator[Path, None, None]:
    """Fixture providing temporary directory as pathlib.Path with worker isolation in tests/Output."""
    # Get worker ID for parallel execution isolation
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")

    # Create test output directory in tests/Output instead of system temp
    test_output_base = Path("tests") / "Output"
    test_output_base.mkdir(parents=True, exist_ok=True)

    # Create worker-specific subdirectory
    temp_dir = test_output_base / f"test_path_{worker_id}_{os.getpid()}"
    temp_dir.mkdir(exist_ok=True)

    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_file_factory(request):
    """Factory fixture for creating temporary files with proper cleanup."""
    created_files = []
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")

    def create_temp_file(
        suffix: str = ".tmp", content: str = "", mode: str = "w"
    ) -> Path:
        """Create a temporary file with automatic cleanup."""
        with tempfile.NamedTemporaryFile(
            mode=mode,
            suffix=suffix,
            prefix=f"followweb_test_{worker_id}_",
            delete=False,
        ) as f:
            if content:
                f.write(content)
            temp_path = Path(f.name)
            created_files.append(temp_path)
            return temp_path

    yield create_temp_file

    # Cleanup all created files
    for file_path in created_files:
        try:
            if file_path.exists():
                file_path.unlink()
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors


@pytest.fixture
def ci_environment():
    """Fixture providing CI environment detection."""
    return {
        "is_ci": os.environ.get("CI", "").lower() in ("true", "1"),
        "is_github_actions": os.environ.get("GITHUB_ACTIONS", "").lower()
        in ("true", "1"),
        "runner_os": os.environ.get("RUNNER_OS", ""),
        "is_windows_ci": os.environ.get("RUNNER_OS", "") == "Windows",
        "is_linux_ci": os.environ.get("RUNNER_OS", "") == "Linux",
        "is_macos_ci": os.environ.get("RUNNER_OS", "") == "macOS",
    }


@pytest.fixture
def ci_timeout(ci_environment):
    """Fixture providing appropriate timeout values for CI environments."""
    if not ci_environment["is_ci"]:
        # Local development - generous timeouts
        return {
            "short": 30,  # 30 seconds for quick operations
            "medium": 120,  # 2 minutes for moderate operations
            "long": 300,  # 5 minutes for complex operations
        }

    # CI environment - more conservative timeouts
    base_timeouts = {
        "short": 60,  # 1 minute for quick operations
        "medium": 180,  # 3 minutes for moderate operations
        "long": 600,  # 10 minutes for complex operations
    }

    # Platform-specific adjustments for CI
    if ci_environment["is_windows_ci"]:
        # Windows CI is generally slower
        multiplier = 1.5
    elif ci_environment["is_linux_ci"]:
        # Linux CI is generally fastest
        multiplier = 0.8
    elif ci_environment["is_macos_ci"]:
        # macOS CI has moderate performance
        multiplier = 1.0
    else:
        # Unknown CI platform - be conservative
        multiplier = 1.2

    return {key: int(value * multiplier) for key, value in base_timeouts.items()}


@pytest.fixture
def ci_optimized_config(
    default_config: Dict[str, Any], temp_output_dir: str, ci_environment: Dict[str, Any]
) -> Dict[str, Any]:
    """Fixture providing CI-optimized configuration with appropriate timeouts and resource limits."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = str(
        Path("tests") / "test_data" / "tiny_real.json"
    )  # Use smallest dataset in CI
    config["output_file_prefix"] = str(Path(temp_output_dir) / "ci_test_output")

    # CI-specific optimizations
    if ci_environment["is_ci"]:
        # Reduce timeouts and resource usage for CI
        config["visualization"]["static_image"]["generate"] = (
            False  # Skip PNG generation for speed
        )
        config["shared_metrics"]["cache_timeout_seconds"] = 60  # Shorter cache timeout

        # Use minimal k-values for CI
        config["k_values"] = {
            "strategy_k_values": {
                "k-core": 1,
                "reciprocal_k-core": 1,
                "ego_alter_k-core": 1,
            },
            "default_k_value": 1,
        }

        # Add CI-specific resource limits and timeouts
        config["ci_optimizations"] = {
            "max_execution_time": 300,  # 5 minutes max for CI tests
            "memory_limit_mb": 512,  # Limit memory usage
            "disable_progress_bars": True,  # Reduce output noise
            "minimal_logging": True,  # Reduce log verbosity
        }

        # GitHub Actions specific optimizations
        if ci_environment["is_github_actions"]:
            # Further optimizations for GitHub Actions runners
            config["visualization"]["pyvis_interactive"]["physics"] = (
                False  # Disable physics for faster rendering
            )

            # Platform-specific CI optimizations
            if ci_environment["is_windows_ci"]:
                # Windows CI runners need more conservative settings
                config["ci_optimizations"]["max_execution_time"] = (
                    600  # 10 minutes for Windows
                )
                config["ci_optimizations"]["memory_limit_mb"] = (
                    256  # Lower memory limit
                )
            elif ci_environment["is_linux_ci"]:
                # Linux CI runners are generally faster
                config["ci_optimizations"]["max_execution_time"] = (
                    180  # 3 minutes for Linux
                )
            elif ci_environment["is_macos_ci"]:
                # macOS CI runners have moderate performance
                config["ci_optimizations"]["max_execution_time"] = (
                    240  # 4 minutes for macOS
                )
    else:
        # Local development - use appropriate k-values
        k_values = calculate_appropriate_k_values("tiny_real")
        config["k_values"] = k_values

    return config


@pytest.fixture
def worker_isolated_file(request) -> Generator[str, None, None]:
    """Fixture providing worker-isolated temporary file for integration tests."""
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix=f"test_{worker_id}_", delete=False
    ) as f:
        temp_file = f.name

    try:
        yield temp_file
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


@pytest.fixture
def performance_isolation(request, ci_environment):
    """Fixture to ensure performance test isolation and accurate timing."""
    # Check if this is a performance test
    if any(
        marker.name in ["slow", "performance"] for marker in request.node.iter_markers()
    ):
        # Ensure we're running in sequential mode for accurate timing
        import gc

        gc.collect()  # Clean up memory before performance test

        # Set environment variables to minimize interference
        original_env = {}
        performance_env = {
            "PYTHONHASHSEED": "0",  # Consistent hash seed for reproducible results
            "PYTEST_CURRENT_TEST": request.node.nodeid,  # Track current test
        }

        # CI-specific environment optimizations
        if ci_environment["is_ci"]:
            performance_env.update(
                {
                    "MPLBACKEND": "Agg",  # Use non-interactive matplotlib backend
                    "PYTHONUNBUFFERED": "1",  # Ensure immediate output
                }
            )

        for key, value in performance_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        yield

        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

        gc.collect()  # Clean up after performance test
    else:
        yield


@pytest.fixture
def ci_resource_manager(ci_environment):
    """Fixture providing CI-aware resource management."""

    class CIResourceManager:
        def __init__(self, ci_env):
            self.ci_env = ci_env
            self.is_ci = ci_env["is_ci"]

        def get_max_workers(self, test_type="unit"):
            """Get appropriate number of workers for parallel execution."""
            if not self.is_ci:
                # Local development - use more workers
                return {"unit": 4, "integration": 2, "performance": 1}.get(test_type, 2)

            # CI environment - be more conservative
            if self.ci_env["is_windows_ci"]:
                return {"unit": 2, "integration": 1, "performance": 1}.get(test_type, 1)
            elif self.ci_env["is_linux_ci"]:
                return {"unit": 3, "integration": 2, "performance": 1}.get(test_type, 2)
            elif self.ci_env["is_macos_ci"]:
                return {"unit": 2, "integration": 1, "performance": 1}.get(test_type, 1)
            else:
                # Unknown CI - be very conservative
                return 1

        def should_skip_resource_intensive(self):
            """Check if resource-intensive tests should be skipped."""
            return (
                self.is_ci
                and self.ci_env["is_windows_ci"]
                and os.environ.get("SKIP_RESOURCE_INTENSIVE", "").lower()
                in ("true", "1")
            )

        def get_memory_limit_mb(self):
            """Get appropriate memory limit for tests."""
            if not self.is_ci:
                return 1024  # 1GB for local development

            if self.ci_env["is_windows_ci"]:
                return 256  # 256MB for Windows CI
            elif self.ci_env["is_linux_ci"]:
                return 512  # 512MB for Linux CI
            elif self.ci_env["is_macos_ci"]:
                return 384  # 384MB for macOS CI
            else:
                return 256  # Conservative default

    return CIResourceManager(ci_environment)


@pytest.fixture
def fast_config(
    default_config: Dict[str, Any], temp_output_dir: str, sample_data_file: str
) -> Dict[str, Any]:
    """Fixture providing configuration optimized for fast testing using tiny test dataset."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = sample_data_file  # Use tiny test dataset
    config["output_file_prefix"] = str(Path(temp_output_dir) / "test_output")
    config["visualization"]["static_image"]["generate"] = False  # Skip PNG for speed

    # Calculate appropriate k-values based on tiny dataset statistics
    k_values = calculate_appropriate_k_values("tiny_real")
    config["k_values"] = k_values

    return config


@pytest.fixture
def invalid_json_file() -> Generator[str, None, None]:
    """Fixture providing temporary invalid JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"invalid": json content}')
        temp_file = f.name

    try:
        yield temp_file
    finally:
        os.unlink(temp_file)


@pytest.fixture
def empty_json_file() -> Generator[str, None, None]:
    """Fixture providing temporary empty JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump([], f)
        temp_file = f.name

    try:
        yield temp_file
    finally:
        os.unlink(temp_file)


def pytest_configure(config):
    """Configure pytest with custom markers and parallel execution strategies."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")

    # Configure category-specific parallel execution
    _configure_parallel_execution(config)


def _configure_parallel_execution(config):
    """Configure category-specific parallel execution strategies with CI environment detection."""
    from FollowWeb_Visualizor.utils import (
        detect_ci_environment,
        get_optimal_worker_count,
    )

    # Check for environment variable override to disable parallel execution
    env_disable = os.environ.get("PYTEST_PARALLEL_DISABLE", "").lower() in (
        "1",
        "true",
        "yes",
    )

    if env_disable:
        config.option.numprocesses = 1
        config.option.dist = "no"
        return

    # Detect CI environment for optimized configuration
    ci_info = detect_ci_environment()

    # Determine test category from markers
    markers = config.getoption("-m", default="")
    test_category = "all"  # Default

    if "benchmark" in markers:
        test_category = "benchmark"
    elif "unit" in markers and "integration" not in markers and "slow" not in markers:
        test_category = "unit"
    elif "integration" in markers and "unit" not in markers and "slow" not in markers:
        test_category = "integration"
    elif "slow" in markers or "performance" in markers:
        test_category = "performance"

    # Handle benchmark tests - always sequential
    if test_category == "benchmark":
        config.option.numprocesses = 1
        config.option.dist = "no"
        return

    # CI-specific optimizations
    if ci_info["is_ci"]:
        # Reduce worker count in CI to avoid resource contention
        if test_category == "performance":
            # Force sequential execution for performance tests in CI
            config.option.numprocesses = 1
            config.option.dist = "no"
            return
        elif ci_info["provider"] == "github_actions":
            # GitHub Actions specific optimizations
            if os.environ.get("RUNNER_OS") == "Windows":
                # Windows runners are slower, use ~50% of cores
                max_workers = max(1, int((os.cpu_count() or 2) * 0.5))
            else:
                # Linux/macOS runners can handle more, use ~75% of cores
                max_workers = max(1, int((os.cpu_count() or 2) * 0.75))
        else:
            # Other CI providers - conservative approach, use ~50% of cores
            max_workers = max(1, int((os.cpu_count() or 2) * 0.5))
    else:
        max_workers = None  # No limit for local development

    # Get optimal worker count using CI-aware detection
    worker_count = get_optimal_worker_count(test_category)

    # Apply CI limits if applicable
    if max_workers and worker_count > max_workers:
        worker_count = max_workers

    # Configure pytest-xdist based on test category and environment
    config.option.numprocesses = worker_count

    if test_category == "unit":
        # Use worksteal distribution for better load balancing with fast unit tests
        config.option.dist = "worksteal"
    elif test_category == "integration":
        # Use loadgroup distribution to handle resource conflicts better
        config.option.dist = "loadgroup"
    elif test_category == "performance" or test_category == "benchmark":
        # Sequential execution for timing accuracy
        config.option.dist = "no"
        # Disable coverage for performance tests to avoid measurement interference
        if hasattr(config.option, "cov"):
            config.option.cov = None
    else:
        # Mixed workload - use loadscope for balanced distribution
        config.option.dist = "loadscope"


def pytest_sessionstart(session):
    """Log parallel execution configuration at session start."""
    from FollowWeb_Visualizor.utils import detect_ci_environment

    config = session.config
    markers = config.getoption("-m", default="")
    ci_info = detect_ci_environment()

    # Log CI environment information
    if ci_info["is_ci"]:
        ci_msg = f"[CI Environment] Detected {ci_info['provider']}"
        if ci_info["build_id"]:
            ci_msg += f" (Build: {ci_info['build_id']})"
        print(f"\n{ci_msg}")

    if hasattr(config.option, "numprocesses") and config.option.numprocesses:
        worker_count = config.option.numprocesses
        dist_mode = getattr(config.option, "dist", "loadscope")

        if worker_count == 1:
            if "benchmark" in markers:
                print(
                    "[Parallel Execution] Sequential mode for benchmark tests (pytest-benchmark compatibility)"
                )
            elif "slow" in markers or "performance" in markers:
                print(
                    "[Parallel Execution] Sequential mode for performance tests (timing accuracy)"
                )
            else:
                print("[Parallel Execution] Sequential mode")
        else:
            test_type = (
                "unit"
                if "unit" in markers
                else "integration"
                if "integration" in markers
                else "mixed"
            )
            env_context = "CI-optimized" if ci_info["is_ci"] else "local development"
            print(
                f"[Parallel Execution] Using {worker_count} workers for {test_type} tests ('{dist_mode}' distribution, {env_context})"
            )
    else:
        print("[Parallel Execution] Running in sequential mode")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid or "pipeline" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Mark slow tests
        if any(keyword in item.nodeid for keyword in ["performance", "timing", "slow"]):
            item.add_marker(pytest.mark.slow)

        # Mark unit tests (default for most tests)
        if not any(
            marker.name in ["integration", "slow"] for marker in item.iter_markers()
        ):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def tiny_config(default_config: Dict[str, Any], temp_output_dir: str) -> Dict[str, Any]:
    """Fixture providing configuration for very fast testing using tiny test dataset."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = str(
        Path("tests") / "test_data" / "tiny_real.json"
    )  # Use tiny test dataset
    config["output_file_prefix"] = str(Path(temp_output_dir) / "test_output")
    config["visualization"]["static_image"]["generate"] = False  # Skip PNG for speed

    # Calculate appropriate k-values based on tiny dataset statistics
    k_values = calculate_appropriate_k_values("tiny_real")
    config["k_values"] = k_values

    return config


@pytest.fixture
def small_config(
    default_config: Dict[str, Any], temp_output_dir: str
) -> Dict[str, Any]:
    """Fixture providing configuration for fast testing using small test dataset."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = str(
        Path("tests") / "test_data" / "small_real.json"
    )  # Use small test dataset
    config["output_file_prefix"] = str(Path(temp_output_dir) / "test_output")
    config["visualization"]["static_image"]["generate"] = False  # Skip PNG for speed

    # Calculate appropriate k-values based on small dataset statistics
    k_values = calculate_appropriate_k_values("small_real")
    config["k_values"] = k_values

    return config


@pytest.fixture
def medium_config(
    default_config: Dict[str, Any], temp_output_dir: str
) -> Dict[str, Any]:
    """Fixture providing configuration for medium-scale testing using medium test dataset."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = str(
        Path("tests") / "test_data" / "medium_real.json"
    )  # Use medium test dataset
    config["output_file_prefix"] = str(Path(temp_output_dir) / "test_output")
    config["visualization"]["static_image"]["generate"] = False  # Skip PNG for speed

    # Calculate appropriate k-values based on medium dataset statistics
    k_values = calculate_appropriate_k_values("medium_real")
    config["k_values"] = k_values

    return config


@pytest.fixture
def large_config(
    default_config: Dict[str, Any], temp_output_dir: str
) -> Dict[str, Any]:
    """Fixture providing configuration for large-scale testing using large test dataset."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = str(
        Path("tests") / "test_data" / "large_real.json"
    )  # Use large test dataset
    config["output_file_prefix"] = str(Path(temp_output_dir) / "test_output")
    config["visualization"]["static_image"]["generate"] = False  # Skip PNG for speed

    # Calculate appropriate k-values based on large dataset statistics
    k_values = calculate_appropriate_k_values("large_real")
    config["k_values"] = k_values

    return config


@pytest.fixture
def comprehensive_config(
    default_config: Dict[str, Any], temp_output_dir: str
) -> Dict[str, Any]:
    """Fixture providing configuration for comprehensive testing using full test dataset."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = str(
        Path("tests") / "test_data" / "full_anonymized.json"  # Use full test dataset
    )
    config["output_file_prefix"] = str(Path(temp_output_dir) / "test_output")
    config["visualization"]["static_image"]["generate"] = False  # Skip PNG for speed

    # Calculate appropriate k-values based on full dataset statistics
    k_values = calculate_appropriate_k_values("full_anonymized")
    config["k_values"] = k_values

    return config


@pytest.fixture
def scalability_config(
    default_config: Dict[str, Any], temp_output_dir: str
) -> Dict[str, Any]:
    """Fixture providing configuration for testing future scalability with higher k-values."""
    from pathlib import Path

    config = default_config.copy()
    config["input_file"] = str(
        Path("tests") / "test_data" / "full_anonymized.json"  # Use full test dataset
    )
    config["output_file_prefix"] = str(Path(temp_output_dir) / "test_output")
    config["visualization"]["static_image"]["generate"] = False  # Skip PNG for speed

    # Use higher k-values to test scalability with larger future datasets
    k_values = get_scalability_k_values("full_anonymized")
    config["k_values"] = k_values

    return config
