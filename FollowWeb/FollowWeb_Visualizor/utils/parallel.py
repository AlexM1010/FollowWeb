"""
Parallel processing utilities for FollowWeb network analysis.

This module provides centralized parallel processing configuration and management
for NetworkX operations, testing, and visualization tasks.
"""

# Standard library imports
import importlib.util
import logging
import os

# Third-party imports for parallel processing
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

try:
    # Check both availability and Python version requirement
    NX_PARALLEL_AVAILABLE = (
        sys.version_info >= (3, 11)
        and importlib.util.find_spec("nx_parallel") is not None
    )

    # Actually import if available
    if NX_PARALLEL_AVAILABLE:
        import nx_parallel  # noqa: F401

except ImportError:
    NX_PARALLEL_AVAILABLE = False

# Local imports
from ..output.formatters import EmojiFormatter


@dataclass
class ParallelConfig:
    """Configuration for parallel processing operations."""

    cores_available: int
    cores_requested: int
    cores_used: int
    strategy: str  # 'auto', 'conservative', 'aggressive', 'sequential'
    environment: str  # 'local', 'ci', 'unknown'
    nx_parallel_enabled: bool
    operation_type: str  # 'analysis', 'testing', 'visualization'


class ParallelProcessingManager:
    """
    Centralized manager for all parallel processing operations.

    Provides consistent core allocation, user notifications, and performance
    optimization across the entire FollowWeb package.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._cpu_count = self._detect_cpu_count()
        self._ci_info = self._detect_ci_environment()
        self._nx_parallel_info = self._check_nx_parallel_availability()

    def _detect_cpu_count(self) -> int:
        """Detect available CPU cores with fallback."""
        try:
            count = os.cpu_count()
            if count is None or count < 1:
                self.logger.warning(
                    "CPU count detection returned invalid value, using fallback of 2"
                )
                return 2
            return count
        except Exception as e:
            self.logger.warning(f"Failed to detect CPU count: {e}, using fallback of 2")
            return 2

    def _detect_ci_environment(self) -> Dict[str, Any]:
        """Detect CI environment and determine appropriate resource allocation."""
        ci_indicators = {
            "GITHUB_ACTIONS": "github",
            "GITLAB_CI": "gitlab",
            "AZURE_PIPELINES": "azure",
            "TRAVIS": "travis",
            "CIRCLECI": "circle",
            "JENKINS_URL": "jenkins",
            "CI": "generic",
        }

        detected_provider = None
        for env_var, provider in ci_indicators.items():
            if os.getenv(env_var):
                detected_provider = provider
                break

        is_ci = detected_provider is not None

        # Determine resource allocation strategy based on CI provider
        if detected_provider in ["github", "gitlab", "azure"]:
            strategy = "moderate"  # Can handle moderate parallelization
        elif detected_provider in ["travis", "circle"]:
            strategy = "conservative"  # More resource-constrained
        else:
            strategy = "conservative" if is_ci else "aggressive"

        return {
            "is_ci": is_ci,
            "provider": detected_provider or "local",
            "strategy": strategy,
        }

    def _check_nx_parallel_availability(self) -> Dict[str, Any]:
        """Check nx-parallel availability and working status."""
        info = {"available": NX_PARALLEL_AVAILABLE, "working": False, "backends": []}

        if NX_PARALLEL_AVAILABLE:
            try:
                # Test basic functionality
                import networkx as nx
                import nx_parallel  # noqa: F401

                test_graph = nx.path_graph(10)
                _ = nx.degree_centrality(test_graph)
                info["working"] = True

                # Check available backends
                try:
                    backends = getattr(nx.config, "backends", None)
                    if backends and hasattr(backends, "keys"):
                        info["backends"] = list(backends.keys())
                except Exception:
                    pass

            except Exception as e:
                self.logger.debug(f"nx-parallel availability check failed: {e}")

        return info

    def get_parallel_config(
        self,
        operation_type: str,
        min_size_threshold: int = 100,
        graph_size: Optional[Optional[int]] = None,
        override_cores: Optional[Optional[int]] = None,
    ) -> ParallelConfig:
        """
        Get optimized parallel configuration for a specific operation.

        Args:
            operation_type: Type of operation ('analysis', 'testing', 'visualization')
            min_size_threshold: Minimum data size to enable parallelization
            graph_size: Size of graph/data being processed (for optimization decisions)
            override_cores: Explicit core count override

        Returns:
            ParallelConfig with optimized settings and user notification info
        """
        # Import here to avoid circular imports
        from ..data.cache import get_cache_manager

        # Check cache first (except for overrides)
        if override_cores is None:
            cache_manager = get_cache_manager()
            cached_config = cache_manager.get_cached_parallel_config(
                operation_type, graph_size
            )
            if cached_config is not None:
                return cached_config

        # Handle explicit override
        if override_cores is not None:
            if override_cores < 1:
                override_cores = 1
            cores_used = min(override_cores, self._cpu_count)
            return ParallelConfig(
                cores_available=self._cpu_count,
                cores_requested=override_cores,
                cores_used=cores_used,
                strategy="override",
                environment=self._ci_info["provider"],
                nx_parallel_enabled=self._nx_parallel_info["working"],
                operation_type=operation_type,
            )

        # Check environment variable overrides
        env_overrides = {
            "analysis": "FOLLOWWEB_ANALYSIS_CORES",
            "testing": "PYTEST_WORKERS",
            "visualization": "FOLLOWWEB_VIZ_CORES",
        }

        env_var = env_overrides.get(operation_type, "FOLLOWWEB_CORES")
        env_value = os.getenv(env_var)
        if env_value and env_value.lower() != "auto":
            try:
                cores_requested = int(env_value)
                cores_used = max(1, min(cores_requested, self._cpu_count))
                return ParallelConfig(
                    cores_available=self._cpu_count,
                    cores_requested=cores_requested,
                    cores_used=cores_used,
                    strategy="env_override",
                    environment=self._ci_info["provider"],
                    nx_parallel_enabled=self._nx_parallel_info["working"],
                    operation_type=operation_type,
                )
            except ValueError:
                pass  # Fall through to auto-detection

        # Auto-detect optimal configuration
        strategy = self._ci_info["strategy"]

        # Determine if parallelization should be enabled
        enable_parallel = True
        if graph_size is not None and graph_size < min_size_threshold:
            enable_parallel = False

        if not enable_parallel:
            cores_used = 1
            strategy = "sequential"
        else:
            # Calculate optimal core count based on operation type and environment
            cores_used = self._calculate_optimal_cores(operation_type, strategy)

        config = ParallelConfig(
            cores_available=self._cpu_count,
            cores_requested=cores_used,
            cores_used=cores_used,
            strategy=strategy,
            environment=self._ci_info["provider"],
            nx_parallel_enabled=self._nx_parallel_info["working"] and enable_parallel,
            operation_type=operation_type,
        )

        # Cache the result (except for overrides)
        if override_cores is None:
            cache_manager = get_cache_manager()
            cache_manager.cache_parallel_config(operation_type, graph_size, config)

        return config

    def _calculate_optimal_cores(self, operation_type: str, strategy: str) -> int:
        """Calculate optimal core count based on operation type and strategy."""
        if strategy == "sequential":
            return 1

        base_multipliers = {
            "aggressive": 0.9,  # Use 90% of cores (leave 1 free)
            "moderate": 0.75,  # Use 75% of cores
            "conservative": 0.5,  # Use 50% of cores
        }

        # Operation-specific adjustments
        operation_adjustments = {
            "analysis": 1.0,  # Full allocation for analysis
            "testing": {
                "unit": 1.0,  # Full allocation for unit tests
                "integration": 0.5,  # Reduced for integration tests
                "performance": 0.0,  # Sequential for performance tests
            },
            "visualization": 0.8,  # Slightly reduced for visualization
        }

        base_multiplier = base_multipliers.get(strategy, 0.5)

        if operation_type == "testing":
            # For testing, we need to determine the test category
            test_category = os.getenv("PYTEST_TEST_CATEGORY", "unit")
            adjustment = operation_adjustments["testing"].get(test_category, 1.0)
        else:
            adjustment = operation_adjustments.get(operation_type, 1.0)

        if adjustment == 0.0:
            return 1  # Sequential execution

        final_multiplier = base_multiplier * adjustment
        cores_used = max(1, int(self._cpu_count * final_multiplier))

        # Ensure we don't exceed available cores
        return min(cores_used, self._cpu_count)

    def log_parallel_config(
        self, config: ParallelConfig, logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Log parallel configuration with user-friendly notifications.

        Args:
            config: ParallelConfig to log
            logger: Optional specific logger to use
        """
        if logger is None:
            logger = self.logger

        # Create user-friendly message
        if config.cores_used == 1:
            message = EmojiFormatter.format(
                "progress", f"Running {config.operation_type} sequentially (1 core)"
            )
            if config.strategy == "sequential":
                message += " - optimized for accuracy"
            elif config.cores_available > 1:
                message += f" - {config.cores_available} cores available but using sequential mode"
        else:
            efficiency = (config.cores_used / config.cores_available) * 100
            message = EmojiFormatter.format(
                "lightning",
                f"Running {config.operation_type} in parallel using {config.cores_used}/{config.cores_available} cores ({efficiency:.0f}% utilization)",
            )

            if config.nx_parallel_enabled:
                message += " with NetworkX parallel optimization"

        # Add environment context
        if config.environment != "local":
            message += f" [{config.environment} environment]"

        # Add strategy context for debugging
        if config.strategy in ["conservative", "override", "env_override"]:
            logger.debug(f"Parallel strategy: {config.strategy}")

        # Log parallel processing info with proper formatting
        logger.info(message)

        # Log additional debug information
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Parallel config details: {config}")

    def get_nx_parallel_status(self) -> str:
        """Get human-readable nx-parallel status for user notifications."""
        if not self._nx_parallel_info["available"]:
            return "nx-parallel not available - using standard NetworkX algorithms"
        elif not self._nx_parallel_info["working"]:
            return "nx-parallel installed but not working - using standard NetworkX algorithms"
        else:
            backends = self._nx_parallel_info["backends"]
            if backends:
                return f"nx-parallel active with backends: {', '.join(backends)}"
            else:
                return "nx-parallel active"

    def should_use_parallel(
        self, operation_type: str, data_size: int, threshold: int = 100
    ) -> Tuple[bool, str]:
        """
        Determine if parallel processing should be used for an operation.

        Returns:
            Tuple of (should_use_parallel, reason)
        """
        if data_size < threshold:
            return (
                False,
                f"Data size ({data_size}) below parallel threshold ({threshold})",
            )

        config = self.get_parallel_config(operation_type, threshold, data_size)

        if config.cores_used == 1:
            return False, f"Sequential execution selected (strategy: {config.strategy})"

        return (
            True,
            f"Parallel execution beneficial ({config.cores_used} cores available)",
        )


# Global instance for package-wide use
_parallel_manager = None


def get_parallel_manager() -> ParallelProcessingManager:
    """Get the global parallel processing manager instance."""
    global _parallel_manager
    if _parallel_manager is None:
        _parallel_manager = ParallelProcessingManager()
    return _parallel_manager


def get_analysis_parallel_config(
    graph_size: Optional[Optional[int]] = None,
) -> ParallelConfig:
    """Get parallel configuration optimized for network analysis operations."""
    return get_parallel_manager().get_parallel_config("analysis", graph_size=graph_size)


def get_testing_parallel_config(test_category: str = "unit") -> ParallelConfig:
    """Get parallel configuration optimized for testing operations."""
    # Set environment variable to help with test category detection
    os.environ["PYTEST_TEST_CATEGORY"] = test_category
    return get_parallel_manager().get_parallel_config("testing")


def get_visualization_parallel_config(
    data_size: Optional[Optional[int]] = None,
) -> ParallelConfig:
    """Get parallel configuration optimized for visualization operations."""
    return get_parallel_manager().get_parallel_config(
        "visualization", graph_size=data_size
    )


def log_parallel_usage(config: ParallelConfig, logger: logging.Logger) -> None:
    """Convenience function to log parallel usage with standardized formatting."""
    get_parallel_manager().log_parallel_config(config, logger)


def is_nx_parallel_available() -> bool:
    """Check if nx-parallel is available and working."""
    return get_parallel_manager()._nx_parallel_info["working"]


def get_nx_parallel_status_message() -> str:
    """Get user-friendly nx-parallel status message."""
    return get_parallel_manager().get_nx_parallel_status()


def detect_ci_environment() -> Dict[str, Any]:
    """
    Detects if running in a CI environment and identifies the CI provider.

    Returns:
        dict: Dictionary containing CI detection information:
            - 'is_ci': bool indicating if running in CI
            - 'provider': str name of CI provider (or 'unknown' if detected but unidentified)
            - 'build_id': Optional build/job identifier
            - 'worker_recommendation': str recommended worker count strategy

    Examples:
        >>> ci_info = detect_ci_environment()
        >>> if ci_info['is_ci']:
        ...     progress_msg = EmojiFormatter.format("progress", f"Running in {ci_info['provider']} CI")
        ...     logger.info(progress_msg)
    """
    # Common CI environment variables and their providers
    ci_indicators = {
        "GITHUB_ACTIONS": "GitHub Actions",
        "GITLAB_CI": "GitLab CI",
        "JENKINS_URL": "Jenkins",
        "BUILDKITE": "Buildkite",
        "CIRCLECI": "CircleCI",
        "TRAVIS": "Travis CI",
        "APPVEYOR": "AppVeyor",
        "AZURE_HTTP_USER_AGENT": "Azure Pipelines",
        "TEAMCITY_VERSION": "TeamCity",
        "BAMBOO_BUILD_NUMBER": "Bamboo",
        "TF_BUILD": "Azure DevOps",
        "CODEBUILD_BUILD_ID": "AWS CodeBuild",
        "DRONE": "Drone CI",
        "SEMAPHORE": "Semaphore CI",
        "BITBUCKET_BUILD_NUMBER": "Bitbucket Pipelines",
    }

    # Check for specific CI providers
    detected_provider = None
    build_id = None

    for env_var, provider_name in ci_indicators.items():
        if os.getenv(env_var):
            detected_provider = provider_name
            break

    # Generic CI detection fallback
    is_ci = detected_provider is not None or os.getenv("CI", "").lower() in (
        "true",
        "1",
        "yes",
    )

    if is_ci and not detected_provider:
        detected_provider = "unknown"

    # Extract build/job identifiers for common providers
    if detected_provider == "GitHub Actions":
        build_id = os.getenv("GITHUB_RUN_ID")
    elif detected_provider == "GitLab CI":
        build_id = os.getenv("CI_JOB_ID")
    elif detected_provider == "Jenkins":
        build_id = os.getenv("BUILD_NUMBER")
    elif detected_provider == "CircleCI":
        build_id = os.getenv("CIRCLE_BUILD_NUM")
    elif detected_provider == "Travis CI":
        build_id = os.getenv("TRAVIS_BUILD_NUMBER")
    elif detected_provider == "Azure Pipelines" or detected_provider == "Azure DevOps":
        build_id = os.getenv("BUILD_BUILDNUMBER")
    elif detected_provider == "AWS CodeBuild":
        build_id = os.getenv("CODEBUILD_BUILD_ID")

    # Determine worker count recommendation based on CI provider
    worker_recommendation = "conservative"  # Default for CI
    if detected_provider in [
        "GitHub Actions",
        "GitLab CI",
        "Azure Pipelines",
        "Azure DevOps",
    ]:
        worker_recommendation = (
            "moderate"  # These typically have better resource allocation
        )
    elif not is_ci:
        worker_recommendation = "auto"  # Local development

    return {
        "is_ci": is_ci,
        "provider": detected_provider,
        "build_id": build_id,
        "worker_recommendation": worker_recommendation,
    }


def get_optimal_worker_count(
    test_category: str = "all", override: Optional[Optional[int]] = None
) -> int:
    """
    Determines optimal worker count for parallel test execution based on environment and test category.

    This function is now a wrapper around the centralized parallel processing system.

    Args:
        test_category: Type of tests ('unit', 'integration', 'performance', 'all')
        override: Optional explicit worker count override

    Returns:
        int: Recommended number of workers (1 for sequential, >1 for parallel)

    Raises:
        ValueError: If test_category is not recognized
    """
    # Use the consolidated parallel processing functions from this module
    valid_categories = ["unit", "integration", "performance", "all"]
    if test_category not in valid_categories:
        raise ValueError(
            f"Invalid test category '{test_category}'. Must be one of: {valid_categories}"
        )

    # Check for explicit override first
    if override is not None:
        if not isinstance(override, int) or override < 1:
            raise ValueError("Worker count override must be a positive integer")
        return override

    # Get configuration from centralized parallel processing system
    config = get_parallel_manager().get_parallel_config("testing")
    return config.cores_used
