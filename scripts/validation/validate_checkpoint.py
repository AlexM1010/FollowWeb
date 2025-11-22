#!/usr/bin/env python3
"""
Checkpoint validation script for Freesound pipeline.

Architecture Notes:
    The checkpoint system uses a split architecture with type inconsistency
    by design:

    - Graph topology (.gpickle): Nodes use STRING IDs (e.g., "217542")
    - Metadata cache (.db): Uses INTEGER IDs (e.g., 217542)

    This validator handles type conversion transparently. When comparing
    or looking up data, always convert to the appropriate type using the
    provided utility functions.

Validates checkpoint integrity by checking:
- Graph topology and metadata cache consistency
- Edge counts match checkpoint metadata
- Pagination state consistency
- All nodes have corresponding metadata entries

Exit codes:
- 0: All validation checks passed
- 1: Validation failed
- 2: Checkpoint files not found or corrupted
"""

import json
import logging
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from FollowWeb.FollowWeb_Visualizor.data.storage import MetadataCache

# Constants
GRAPH_TOPOLOGY_FILENAME = "graph_topology.gpickle"
METADATA_CACHE_FILENAME = "metadata_cache.db"
CHECKPOINT_META_FILENAME = "checkpoint_metadata.json"
VALIDATION_SAMPLE_SIZE = 100  # Number of nodes to sample for metadata checks


# Type conversion utilities
def graph_id_to_cache_id(node_id: str) -> int:
    """
    Convert graph node ID (string) to metadata cache ID (integer).

    Args:
        node_id: Graph node ID as string (e.g., "217542")

    Returns:
        Metadata cache ID as integer (e.g., 217542)
    """
    return int(node_id)


def cache_id_to_graph_id(cache_id: int) -> str:
    """
    Convert metadata cache ID (integer) to graph node ID (string).

    Args:
        cache_id: Metadata cache ID as integer (e.g., 217542)

    Returns:
        Graph node ID as string (e.g., "217542")
    """
    return str(cache_id)


@dataclass
class ValidationResult:
    """Result of checkpoint validation."""

    passed: bool
    checks_run: int
    checks_passed: int
    errors: list[str]
    warnings: list[str]
    metadata: dict[str, Any]


class CheckpointValidator:
    """Validates checkpoint integrity."""

    def __init__(self, checkpoint_dir: str):
        """
        Initialize validator.

        Args:
            checkpoint_dir: Path to checkpoint directory

        Raises:
            ValueError: If checkpoint_dir is empty
            FileNotFoundError: If checkpoint directory doesn't exist
        """
        if not checkpoint_dir:
            raise ValueError("checkpoint_dir cannot be empty")

        self.checkpoint_dir = Path(checkpoint_dir)

        if not self.checkpoint_dir.exists():
            raise FileNotFoundError(f"Checkpoint directory not found: {checkpoint_dir}")

        self.logger = logging.getLogger(__name__)

        # Checkpoint file paths
        self.graph_path = self.checkpoint_dir / GRAPH_TOPOLOGY_FILENAME
        self.metadata_db_path = self.checkpoint_dir / METADATA_CACHE_FILENAME
        self.checkpoint_meta_path = self.checkpoint_dir / CHECKPOINT_META_FILENAME

    def validate(self) -> ValidationResult:
        """
        Run all validation checks.

        Returns:
            ValidationResult with validation status and details
        """
        errors = []
        warnings = []
        checks_run = 0
        checks_passed = 0
        metadata = {}

        self.logger.info("Starting checkpoint validation...")

        # Check 1: Verify checkpoint files exist
        checks_run += 1
        if not self._check_files_exist():
            errors.append("Checkpoint files not found or incomplete")
            return ValidationResult(
                passed=False,
                checks_run=checks_run,
                checks_passed=checks_passed,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
            )
        checks_passed += 1
        self.logger.info("✓ Checkpoint files exist")

        # Load checkpoint components
        try:
            graph = self._load_graph()
            metadata_cache = self._load_metadata_cache()
            checkpoint_meta = self._load_checkpoint_metadata()
        except (IOError, OSError, FileNotFoundError) as e:
            errors.append(f"Failed to read checkpoint files: {e}")
            return ValidationResult(
                passed=False,
                checks_run=checks_run,
                checks_passed=checks_passed,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
            )
        except (TypeError, ValueError, pickle.UnpicklingError) as e:
            errors.append(f"Checkpoint data is corrupted or invalid: {e}")
            return ValidationResult(
                passed=False,
                checks_run=checks_run,
                checks_passed=checks_passed,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
            )
        except Exception as e:
            self.logger.exception("Unexpected error loading checkpoint")
            errors.append(f"Unexpected error: {e}")
            return ValidationResult(
                passed=False,
                checks_run=checks_run,
                checks_passed=checks_passed,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
            )

        # Store metadata for reporting
        metadata["sample_count"] = graph.number_of_nodes()
        metadata["edge_count"] = graph.number_of_edges()
        metadata["checkpoint_version"] = checkpoint_meta.get("version", "unknown")

        # Check 2: Verify graph and metadata consistency
        checks_run += 1
        consistency_result = self._check_graph_metadata_consistency(
            graph, metadata_cache
        )

        if consistency_result["errors"]:
            errors.extend(consistency_result["errors"])
            return ValidationResult(
                passed=False,
                checks_run=checks_run,
                checks_passed=checks_passed,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
            )

        if consistency_result["warnings"]:
            warnings.extend(consistency_result["warnings"])

        checks_passed += 1
        self.logger.info("✓ Graph and metadata cache are consistent")

        # Check 3: Verify node counts
        checks_run += 1
        node_check_result = self._check_node_counts(graph, checkpoint_meta)

        if node_check_result["error"]:
            errors.append(node_check_result["error"])
        else:
            checks_passed += 1
            self.logger.info(
                f"✓ Node count matches ({node_check_result['count']} nodes)"
            )

        # Check 4: Verify edge counts
        checks_run += 1
        edge_check_result = self._check_edge_counts(graph, checkpoint_meta)

        if edge_check_result["error"]:
            errors.append(edge_check_result["error"])
        else:
            checks_passed += 1
            self.logger.info(
                f"✓ Edge count matches ({edge_check_result['count']} edges)"
            )

        # Check 5: Verify all nodes have metadata
        checks_run += 1
        metadata_check_result = self._check_nodes_have_metadata(graph, metadata_cache)

        if metadata_check_result["error"]:
            errors.append(metadata_check_result["error"])
        else:
            checks_passed += 1
            self.logger.info("✓ All sampled nodes have metadata")

        # Check 6: Verify data quality (check for missing/incomplete fields)
        checks_run += 1
        data_quality_result = self._check_data_quality(metadata_cache)

        if data_quality_result["samples_with_issues"] > 0:
            # Data quality issues found - fail validation to trigger repair
            errors.append(
                f"Data quality: {data_quality_result['samples_with_issues']} samples "
                f"missing {data_quality_result['total_issues']} fields"
            )
            metadata["data_quality_issues"] = data_quality_result
            self.logger.warning(
                f"⚠️  {data_quality_result['samples_with_issues']} samples need repair"
            )
        else:
            checks_passed += 1
            self.logger.info("✓ All samples have complete data")

        # Check 7: Validate pagination state
        checks_run += 1
        pagination_result = self._check_pagination_state(checkpoint_meta)

        if pagination_result["error"]:
            errors.append(pagination_result["error"])
        elif pagination_result["warning"]:
            warnings.append(pagination_result["warning"])
            checks_passed += 1  # Not critical
        else:
            checks_passed += 1
            self.logger.info(
                f"✓ Pagination state valid (page {pagination_result['page']})"
            )
            metadata["pagination_page"] = pagination_result["page"]
            metadata["search_query"] = pagination_result["query"]

        # Determine overall result
        passed = len(errors) == 0

        return ValidationResult(
            passed=passed,
            checks_run=checks_run,
            checks_passed=checks_passed,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
        )

    def _check_files_exist(self) -> bool:
        """
        Check if all required checkpoint files exist.

        Returns:
            True if all files exist, False otherwise
        """
        return (
            self.graph_path.exists()
            and self.metadata_db_path.exists()
            and self.checkpoint_meta_path.exists()
        )

    def _load_graph(self) -> nx.DiGraph:
        """
        Load graph topology from pickle file.

        Note: Graph nodes are stored as string IDs (e.g., "217542"),
        while metadata cache uses integer IDs (e.g., 217542).
        This is by design for compatibility with NetworkX operations.

        Returns:
            NetworkX DiGraph with string node IDs

        Raises:
            IOError: If file cannot be read
            pickle.UnpicklingError: If file is corrupted
            TypeError: If loaded object is not a NetworkX graph
        """
        with open(self.graph_path, "rb") as f:
            # nosec B301 - Loading our own checkpoint data, not untrusted input
            graph = pickle.load(f)  # nosec B301

        # Validate loaded data
        if not isinstance(graph, (nx.Graph, nx.DiGraph)):
            raise TypeError(
                f"Expected NetworkX Graph or DiGraph, got {type(graph).__name__}"
            )

        return graph

    def _load_metadata_cache(self) -> MetadataCache:
        """
        Load metadata cache from SQLite database.

        Returns:
            MetadataCache instance

        Raises:
            IOError: If database cannot be opened
        """
        return MetadataCache(str(self.metadata_db_path), self.logger)

    def _load_checkpoint_metadata(self) -> dict[str, Any]:
        """
        Load checkpoint metadata from JSON file.

        Returns:
            Dictionary with checkpoint metadata

        Raises:
            IOError: If file cannot be read
            json.JSONDecodeError: If JSON is invalid
        """
        with open(self.checkpoint_meta_path, "r") as f:
            return json.load(f)

    def _check_graph_metadata_consistency(
        self, graph: nx.DiGraph, metadata_cache: MetadataCache
    ) -> dict[str, Any]:
        """
        Check consistency between graph nodes and metadata cache.

        Args:
            graph: NetworkX graph with string node IDs
            metadata_cache: Metadata cache with integer IDs

        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        result = {"errors": [], "warnings": []}

        # Convert both to strings for comparison (normalize types)
        graph_nodes = set(str(n) for n in graph.nodes())
        metadata_ids = set(
            cache_id_to_graph_id(id) for id in metadata_cache.get_all_ids()
        )

        if graph_nodes != metadata_ids:
            missing_in_metadata = graph_nodes - metadata_ids
            missing_in_graph = metadata_ids - graph_nodes

            if missing_in_metadata:
                result["errors"].append(
                    f"{len(missing_in_metadata)} nodes in graph missing from metadata cache"
                )
            if missing_in_graph:
                result["warnings"].append(
                    f"{len(missing_in_graph)} metadata entries not in graph (orphaned)"
                )

        return result

    def _check_node_counts(
        self, graph: nx.DiGraph, checkpoint_meta: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Check if node count matches checkpoint metadata.

        Args:
            graph: NetworkX graph
            checkpoint_meta: Checkpoint metadata dictionary

        Returns:
            Dictionary with 'error' (str or None) and 'count' (int)
        """
        expected_nodes = checkpoint_meta.get("nodes", 0)
        actual_nodes = graph.number_of_nodes()

        if expected_nodes != actual_nodes:
            return {
                "error": f"Node count mismatch: expected {expected_nodes}, got {actual_nodes}",
                "count": actual_nodes,
            }

        return {"error": None, "count": actual_nodes}

    def _check_edge_counts(
        self, graph: nx.DiGraph, checkpoint_meta: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Check if edge count matches checkpoint metadata.

        Args:
            graph: NetworkX graph
            checkpoint_meta: Checkpoint metadata dictionary

        Returns:
            Dictionary with 'error' (str or None) and 'count' (int)
        """
        # Support both old and new field names for backward compatibility
        expected_edges = checkpoint_meta.get("edge_count") or checkpoint_meta.get("edges", 0)
        actual_edges = graph.number_of_edges()

        if expected_edges != actual_edges:
            return {
                "error": f"Edge count mismatch: expected {expected_edges}, got {actual_edges}",
                "count": actual_edges,
            }

        return {"error": None, "count": actual_edges}

    def _check_nodes_have_metadata(
        self, graph: nx.DiGraph, metadata_cache: MetadataCache
    ) -> dict[str, Any]:
        """
        Check if sampled nodes have corresponding metadata entries.

        Args:
            graph: NetworkX graph with string node IDs
            metadata_cache: Metadata cache with integer IDs

        Returns:
            Dictionary with 'error' (str or None)
        """
        missing_metadata = []

        # Sample nodes for performance
        sample_nodes = list(graph.nodes())[:VALIDATION_SAMPLE_SIZE]

        for node_id in sample_nodes:
            # Convert string node ID to integer for metadata cache lookup
            cache_id = graph_id_to_cache_id(node_id)
            if metadata_cache.get(cache_id) is None:
                missing_metadata.append(node_id)

        if missing_metadata:
            return {
                "error": f"{len(missing_metadata)} nodes missing metadata "
                f"(sampled {VALIDATION_SAMPLE_SIZE} nodes)"
            }

        return {"error": None}

    def _check_data_quality(self, metadata_cache: MetadataCache) -> dict[str, Any]:
        """
        Check data quality by scanning for missing/incomplete fields.

        Scans ALL samples for ALL expected fields to identify data quality issues.
        Results are saved to a file that the repair script can read to avoid
        scanning twice.

        Args:
            metadata_cache: Metadata cache with sample data

        Returns:
            Dictionary with samples_with_issues, total_issues, issues_by_field,
            and samples_needing_repair (list of sample IDs)
        """
        import sqlite3

        # ALL expected fields (matches comprehensive_data_repair.py)
        expected_fields = {
            # Critical for visualization
            "uploader_id": int,
            "name": str,
            "tags": list,
            "duration": (int, float),
            "username": str,
            # Important metadata
            "license": str,
            "created": str,
            "url": str,
            "category": str,
            "type": str,
            "channels": int,
            "filesize": int,
            "samplerate": (int, float),
            # Engagement metrics
            "num_downloads": int,
            "num_ratings": int,
            "avg_rating": (int, float),
            "num_comments": int,
        }

        samples_with_issues = 0
        total_issues = 0
        issues_by_field = {}
        samples_needing_repair = []

        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT sample_id, data FROM metadata")

        for sample_id, data_json in cursor.fetchall():
            data = json.loads(data_json)

            # Skip samples already checked and marked unavailable
            if data.get("data_quality_checked") and data.get("api_data_unavailable"):
                continue

            # Get list of fields marked as missing from Freesound
            missing_from_freesound = data.get("_missing_from_freesound", [])

            sample_has_issues = False
            for field_name, expected_type in expected_fields.items():
                # Skip if field is marked as missing from Freesound (intentionally empty)
                if field_name in missing_from_freesound:
                    continue

                # Check if field exists and is not empty
                if field_name not in data or not data[field_name]:
                    # Allow None for optional fields
                    if expected_type == (str, type(None)) or expected_type == type(None):
                        continue
                    sample_has_issues = True
                    total_issues += 1
                    issues_by_field[field_name] = issues_by_field.get(field_name, 0) + 1

            if sample_has_issues:
                samples_with_issues += 1
                samples_needing_repair.append(sample_id)

        conn.close()

        # Save results to file for repair script to read (avoid double scanning)
        results_file = self.checkpoint_dir / "data_quality_scan.json"
        with open(results_file, "w") as f:
            json.dump(
                {
                    "samples_needing_repair": samples_needing_repair,
                    "samples_with_issues": samples_with_issues,
                    "total_issues": total_issues,
                    "issues_by_field": issues_by_field,
                    "scan_timestamp": json.dumps(
                        __import__("datetime").datetime.now().isoformat()
                    ),
                },
                f,
                indent=2,
            )

        return {
            "samples_with_issues": samples_with_issues,
            "total_issues": total_issues,
            "issues_by_field": issues_by_field,
            "samples_needing_repair": samples_needing_repair,
        }

    def _check_pagination_state(
        self, checkpoint_meta: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Check pagination state validity.

        Args:
            checkpoint_meta: Checkpoint metadata dictionary

        Returns:
            Dictionary with 'error', 'warning', 'page', and 'query' fields
        """
        # Support both old and new field names for backward compatibility
        pagination = checkpoint_meta.get("pagination_state") or checkpoint_meta.get(
            "pagination", {}
        )

        if not pagination:
            return {
                "error": None,
                "warning": "No pagination state found in checkpoint",
                "page": None,
                "query": None,
            }

        # Support both field name variants
        current_page = pagination.get("current_page") or pagination.get("page", 0)
        search_query = pagination.get("search_query") or pagination.get(
            "query", "unknown"
        )

        if current_page < 1:
            return {
                "error": f"Invalid pagination state: current_page={current_page}",
                "warning": None,
                "page": current_page,
                "query": search_query,
            }

        return {
            "error": None,
            "warning": None,
            "page": current_page,
            "query": search_query,
        }


def main():
    """Main entry point."""
    try:
        # Import emoji formatter for cross-platform emoji support
        from FollowWeb.FollowWeb_Visualizor.output.formatters import EmojiFormatter
    except ImportError as e:
        print(f"ERROR: Failed to import EmojiFormatter: {e}")
        print("Make sure FollowWeb package is installed: pip install -e FollowWeb/")
        sys.exit(2)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Set emoji fallback level based on environment
    # Use "text" for maximum compatibility (pure ASCII)
    import os

    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        # CI environments: use text for maximum compatibility
        EmojiFormatter.set_fallback_level("text")
    elif sys.platform == "win32" and sys.stdout.encoding not in ("utf-8", "UTF-8"):
        # Windows with non-UTF-8 console: use text
        EmojiFormatter.set_fallback_level("text")
    else:
        # Unix/Linux or UTF-8 console: use full emojis
        EmojiFormatter.set_fallback_level("full")

    # Parse command line arguments
    checkpoint_dir = "data/freesound_library"
    is_final_validation = False
    
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--final":
            is_final_validation = True
        elif not arg.startswith("--"):
            checkpoint_dir = arg

    try:
        # Run validation
        validator = CheckpointValidator(checkpoint_dir)
        result = validator.validate()
    except (ValueError, FileNotFoundError) as e:
        print(f"\nERROR: {e}\n", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}\n", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(2)

    # Print results using EmojiFormatter for cross-platform compatibility
    print("\n" + "=" * 60)
    print("CHECKPOINT VALIDATION RESULTS")
    print("=" * 60)

    if result.passed:
        print(f"Status: {EmojiFormatter.format('success', 'PASSED')}")
    else:
        print(f"Status: {EmojiFormatter.format('error', 'FAILED')}")

    print(f"Checks: {result.checks_passed}/{result.checks_run} passed")
    print()

    if result.metadata:
        print("Checkpoint Info:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")
        print()

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  {EmojiFormatter.format('error', error)}")
        print()

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  {EmojiFormatter.format('warning', warning)}")
        print()

    print("=" * 60)

    # Exit code logic:
    # - Initial validation (no --final flag): Exit 0 even if data quality issues found
    #   This allows repair to run
    # - Final validation (--final flag): Exit 1 if any errors remain
    #   This indicates repair failed to fix issues
    if result.passed:
        sys.exit(0)
    elif is_final_validation:
        # Final validation after repair - failure is fatal
        print(f"\n{EmojiFormatter.format('warning', 'FINAL VALIDATION FAILED - Repair did not resolve all issues')}")
        sys.exit(1)
    else:
        # Initial validation - data quality issues are expected and repairable
        print(f"\n{EmojiFormatter.format('info', 'Data quality issues detected - repair will attempt to fix')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
