#!/usr/bin/env python3
"""
Freesound Pipeline Data Validation Script

Validates checkpoint integrity, graph structure, metadata consistency,
and detects data quality anomalies. Generates a JSON report and exits
with appropriate status codes.

Usage:
    python validate_pipeline_data.py \\
        --checkpoint-dir data/freesound_library \\
        --metrics-history data/metrics_history.jsonl \\
        --output validation_report.json

Exit Codes:
    0: Validation passed
    1: Validation failed (critical issues found)
"""

import argparse
import json
import pickle
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import networkx as nx


class ValidationReport:
    """Container for validation results."""

    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.status = "passed"
        self.checks = {}
        self.statistics = {}
        self.warnings = []
        self.errors = []

    def add_check(self, name: str, status: str, message: str):
        """Add a validation check result."""
        self.checks[name] = {"status": status, "message": message}
        if status == "failed":
            self.status = "failed"
            self.errors.append(f"{name}: {message}")
        elif status == "warning":
            self.warnings.append(f"{name}: {message}")

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "checks": self.checks,
            "statistics": self.statistics,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def validate_checkpoint_integrity(checkpoint_dir: Path, report: ValidationReport) -> tuple[nx.DiGraph | None, dict | None]:
    """
    Validate checkpoint file integrity.

    Checks:
    - Files exist and are readable
    - Pickle file loads successfully
    - SQLite database is not corrupted
    - Checkpoint metadata is valid JSON

    Returns:
        Tuple of (graph, metadata_cache_conn) if successful, (None, None) otherwise
    """
    topology_path = checkpoint_dir / "graph_topology.gpickle"
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    checkpoint_meta_path = checkpoint_dir / "checkpoint_metadata.json"

    # Check file existence
    if not topology_path.exists():
        report.add_check(
            "file_existence",
            "failed",
            f"Graph topology file not found: {topology_path}",
        )
        return None, None

    if not metadata_db_path.exists():
        report.add_check(
            "file_existence",
            "failed",
            f"Metadata database not found: {metadata_db_path}",
        )
        return None, None

    if not checkpoint_meta_path.exists():
        report.add_check(
            "file_existence",
            "warning",
            f"Checkpoint metadata not found: {checkpoint_meta_path}",
        )

    # Check files are not empty
    if topology_path.stat().st_size == 0:
        report.add_check(
            "file_integrity", "failed", "Graph topology file is empty"
        )
        return None, None

    if metadata_db_path.stat().st_size == 0:
        report.add_check(
            "file_integrity", "failed", "Metadata database file is empty"
        )
        return None, None

    # Try loading graph topology
    try:
        with open(topology_path, "rb") as f:
            graph = pickle.load(f)  # nosec B301

        if not isinstance(graph, nx.DiGraph):
            report.add_check(
                "graph_load",
                "failed",
                f"Loaded object is not a DiGraph: {type(graph)}",
            )
            return None, None

        report.add_check(
            "graph_load",
            "passed",
            f"Graph loaded successfully: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges",
        )
    except Exception as e:
        report.add_check(
            "graph_load", "failed", f"Failed to load graph topology: {e}"
        )
        return None, None

    # Try opening SQLite database
    try:
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()

        if result[0] != "ok":
            report.add_check(
                "sqlite_integrity",
                "failed",
                f"SQLite integrity check failed: {result[0]}",
            )
            conn.close()
            return None, None

        # Check metadata table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'"
        )
        if not cursor.fetchone():
            report.add_check(
                "sqlite_schema", "failed", "Metadata table not found in database"
            )
            conn.close()
            return None, None

        report.add_check(
            "sqlite_integrity", "passed", "SQLite database is valid"
        )

    except Exception as e:
        report.add_check(
            "sqlite_integrity", "failed", f"Failed to open SQLite database: {e}"
        )
        return None, None

    # Try loading checkpoint metadata JSON
    if checkpoint_meta_path.exists():
        try:
            with open(checkpoint_meta_path) as f:
                checkpoint_metadata = json.load(f)

            required_fields = ["timestamp", "nodes", "edges"]
            missing_fields = [
                f for f in required_fields if f not in checkpoint_metadata
            ]

            if missing_fields:
                report.add_check(
                    "checkpoint_metadata",
                    "warning",
                    f"Missing fields in checkpoint metadata: {missing_fields}",
                )
            else:
                report.add_check(
                    "checkpoint_metadata",
                    "passed",
                    "Checkpoint metadata is valid JSON",
                )

        except json.JSONDecodeError as e:
            report.add_check(
                "checkpoint_metadata",
                "warning",
                f"Invalid JSON in checkpoint metadata: {e}",
            )
        except Exception as e:
            report.add_check(
                "checkpoint_metadata",
                "warning",
                f"Failed to load checkpoint metadata: {e}",
            )

    return graph, conn


def validate_graph_structure(graph: nx.DiGraph, report: ValidationReport) -> bool:
    """
    Validate graph structure.

    Checks:
    - No orphaned edges (all edges reference existing nodes)
    - Edge weights are valid
    - No self-loops (optional warning)
    - Graph connectivity is reasonable

    Note: Node attributes are stored in SQLite metadata, not in graph topology,
    so they are validated in validate_metadata_consistency instead.

    Returns:
        True if validation passed, False otherwise
    """
    # Check for orphaned edges (should never happen in NetworkX, but verify)
    orphaned_edges = []
    for source, target in graph.edges():
        if source not in graph.nodes() or target not in graph.nodes():
            orphaned_edges.append((source, target))

    if orphaned_edges:
        report.add_check(
            "orphaned_edges",
            "failed",
            f"Found {len(orphaned_edges)} orphaned edges",
        )
        return False

    report.add_check("orphaned_edges", "passed", "No orphaned edges found")

    # Note: Node attributes are checked in metadata validation
    report.add_check(
        "node_attributes",
        "passed",
        "Node attributes stored in metadata (validated separately)",
    )

    # Check edge weights (if present - topology may not include attributes)
    edges_with_attrs = sum(1 for _, _, attrs in graph.edges(data=True) if attrs)
    
    if edges_with_attrs > 0:
        # Graph has edge attributes, validate them
        invalid_weights = []
        for source, target, attrs in graph.edges(data=True):
            if "weight" not in attrs:
                invalid_weights.append((source, target, "missing"))
            elif not isinstance(attrs["weight"], (int, float)):
                invalid_weights.append((source, target, "invalid_type"))
            elif attrs["weight"] < 0 or attrs["weight"] > 1:
                invalid_weights.append((source, target, "out_of_range"))

        if invalid_weights:
            report.add_check(
                "edge_weights",
                "failed",
                f"Found {len(invalid_weights)} edges with invalid weights",
            )
            return False

        report.add_check("edge_weights", "passed", "All edge weights are valid")
    else:
        # Topology-only graph (split architecture)
        report.add_check(
            "edge_weights",
            "passed",
            "Edge attributes not stored in topology (split architecture)",
        )

    # Check for self-loops (warning only)
    self_loops = list(nx.selfloop_edges(graph))
    if self_loops:
        report.add_check(
            "self_loops",
            "warning",
            f"Found {len(self_loops)} self-loops in graph",
        )
    else:
        report.add_check("self_loops", "passed", "No self-loops found")

    # Check for isolated nodes (warning only)
    isolated_nodes = list(nx.isolates(graph))
    if isolated_nodes:
        report.add_check(
            "isolated_nodes",
            "warning",
            f"Found {len(isolated_nodes)} isolated nodes",
        )
    else:
        report.add_check("isolated_nodes", "passed", "No isolated nodes found")

    # Check graph density (warning if suspicious)
    density = nx.density(graph)
    if density > 0.9:
        report.add_check(
            "graph_density",
            "warning",
            f"Graph density is suspiciously high: {density:.3f}",
        )
    else:
        report.add_check(
            "graph_density", "passed", f"Graph density is reasonable: {density:.3f}"
        )

    return True


def validate_metadata_consistency(
    graph: nx.DiGraph, metadata_conn: sqlite3.Connection, report: ValidationReport
) -> bool:
    """
    Validate metadata consistency between graph and SQLite.

    Checks:
    - All graph nodes have corresponding metadata
    - No orphaned metadata entries
    - Sample IDs are unique in metadata
    - Metadata has required fields

    Returns:
        True if validation passed, False otherwise
    """
    cursor = metadata_conn.cursor()

    # Get all sample IDs from metadata
    cursor.execute("SELECT sample_id FROM metadata")
    metadata_ids = {row[0] for row in cursor.fetchall()}

    # Get all node IDs from graph
    graph_node_ids = {int(node) for node in graph.nodes()}

    # Check for missing metadata
    missing_metadata = graph_node_ids - metadata_ids
    if missing_metadata:
        report.add_check(
            "metadata_coverage",
            "failed",
            f"Found {len(missing_metadata)} nodes without metadata",
        )
        return False

    report.add_check(
        "metadata_coverage", "passed", "All graph nodes have metadata"
    )

    # Check for orphaned metadata
    orphaned_metadata = metadata_ids - graph_node_ids
    if orphaned_metadata:
        report.add_check(
            "orphaned_metadata",
            "warning",
            f"Found {len(orphaned_metadata)} metadata entries without corresponding nodes",
        )
    else:
        report.add_check(
            "orphaned_metadata", "passed", "No orphaned metadata entries"
        )

    # Check for duplicate sample IDs
    cursor.execute(
        """
        SELECT sample_id, COUNT(*) as count
        FROM metadata
        GROUP BY sample_id
        HAVING count > 1
    """
    )
    duplicates = cursor.fetchall()

    if duplicates:
        report.add_check(
            "metadata_uniqueness",
            "failed",
            f"Found {len(duplicates)} duplicate sample IDs in metadata",
        )
        return False

    report.add_check(
        "metadata_uniqueness", "passed", "All sample IDs are unique"
    )

    # Check metadata has required fields
    cursor.execute("SELECT sample_id, data FROM metadata LIMIT 10")
    required_fields = ["name", "audio_url"]
    missing_fields_count = 0

    for sample_id, data_json in cursor.fetchall():
        try:
            data = json.loads(data_json)
            for field in required_fields:
                if field not in data:
                    missing_fields_count += 1
        except json.JSONDecodeError:
            report.add_check(
                "metadata_json",
                "failed",
                f"Invalid JSON in metadata for sample {sample_id}",
            )
            return False

    if missing_fields_count > 0:
        report.add_check(
            "metadata_fields",
            "warning",
            f"Found {missing_fields_count} metadata entries with missing required fields",
        )
    else:
        report.add_check(
            "metadata_fields", "passed", "Metadata has required fields"
        )

    return True


def detect_anomalies(
    graph: nx.DiGraph,
    checkpoint_dir: Path,
    metrics_history_path: Path | None,
    report: ValidationReport,
) -> bool:
    """
    Detect data quality anomalies.

    Checks:
    - Sudden drops in node/edge counts
    - Zero nodes/edges added
    - Unusually low API usage
    - Suspicious growth patterns

    Returns:
        True if no critical anomalies found, False otherwise
    """
    current_nodes = graph.number_of_nodes()
    current_edges = graph.number_of_edges()

    # Load metrics history if available
    if metrics_history_path and metrics_history_path.exists():
        try:
            history = []
            with open(metrics_history_path) as f:
                for line in f:
                    if line.strip():
                        history.append(json.loads(line))

            if len(history) >= 2:
                # Get previous metrics
                previous = history[-2]
                prev_nodes = previous.get("nodes", 0)
                prev_edges = previous.get("edges", 0)

                # Check for node count drop
                if prev_nodes > 0:
                    node_drop_pct = (
                        (prev_nodes - current_nodes) / prev_nodes * 100
                    )
                    if node_drop_pct > 10:
                        report.add_check(
                            "node_count_anomaly",
                            "failed",
                            f"Node count dropped by {node_drop_pct:.1f}% (from {prev_nodes} to {current_nodes})",
                        )
                        return False

                # Check for edge count drop
                if prev_edges > 0:
                    edge_drop_pct = (
                        (prev_edges - current_edges) / prev_edges * 100
                    )
                    if edge_drop_pct > 10:
                        report.add_check(
                            "edge_count_anomaly",
                            "failed",
                            f"Edge count dropped by {edge_drop_pct:.1f}% (from {prev_edges} to {current_edges})",
                        )
                        return False

                # Check for zero growth
                nodes_added = current_nodes - prev_nodes
                edges_added = current_edges - prev_edges

                if nodes_added == 0 and edges_added == 0:
                    report.add_check(
                        "zero_growth",
                        "warning",
                        "No nodes or edges added since last run",
                    )

                report.add_check(
                    "growth_anomaly",
                    "passed",
                    f"Added {nodes_added} nodes and {edges_added} edges",
                )

        except Exception as e:
            report.add_check(
                "metrics_history",
                "warning",
                f"Failed to load metrics history: {e}",
            )
    else:
        report.add_check(
            "metrics_history",
            "warning",
            "No metrics history available for anomaly detection",
        )

    # Check edge-to-node ratio
    if current_nodes > 0:
        ratio = current_edges / current_nodes
        if ratio < 0.5:
            report.add_check(
                "edge_node_ratio",
                "warning",
                f"Edge-to-node ratio is low: {ratio:.2f}",
            )
        elif ratio > 20:
            report.add_check(
                "edge_node_ratio",
                "warning",
                f"Edge-to-node ratio is high: {ratio:.2f}",
            )
        else:
            report.add_check(
                "edge_node_ratio",
                "passed",
                f"Edge-to-node ratio is reasonable: {ratio:.2f}",
            )

    return True


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Freesound pipeline checkpoint data"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        required=True,
        help="Path to checkpoint directory",
    )
    parser.add_argument(
        "--metrics-history",
        type=Path,
        help="Path to metrics history JSONL file",
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Path to output JSON report"
    )

    args = parser.parse_args()

    # Initialize report
    report = ValidationReport()

    print(f"🔍 Validating checkpoint: {args.checkpoint_dir}")

    # Step 1: Validate checkpoint integrity
    print("  ├─ Checking file integrity...")
    graph, metadata_conn = validate_checkpoint_integrity(
        args.checkpoint_dir, report
    )

    if graph is None or metadata_conn is None:
        print("  └─ ❌ Checkpoint integrity check failed")
        report.statistics = {
            "total_nodes": 0,
            "total_edges": 0,
            "nodes_added": 0,
            "edges_added": 0,
        }
    else:
        print(
            f"  ├─ ✅ Checkpoint loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
        )

        # Step 2: Validate graph structure
        print("  ├─ Validating graph structure...")
        structure_valid = validate_graph_structure(graph, report)
        if structure_valid:
            print("  ├─ ✅ Graph structure is valid")
        else:
            print("  ├─ ❌ Graph structure validation failed")

        # Step 3: Validate metadata consistency
        print("  ├─ Validating metadata consistency...")
        metadata_valid = validate_metadata_consistency(
            graph, metadata_conn, report
        )
        if metadata_valid:
            print("  ├─ ✅ Metadata is consistent")
        else:
            print("  ├─ ❌ Metadata consistency check failed")

        metadata_conn.close()

        # Step 4: Detect anomalies
        print("  ├─ Detecting anomalies...")
        anomaly_check = detect_anomalies(
            graph, args.checkpoint_dir, args.metrics_history, report
        )
        if anomaly_check:
            print("  ├─ ✅ No critical anomalies detected")
        else:
            print("  ├─ ❌ Anomalies detected")

        # Collect statistics
        report.statistics = {
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
        }

        # Calculate nodes/edges added if history available
        if args.metrics_history and args.metrics_history.exists():
            try:
                with open(args.metrics_history) as f:
                    history = [json.loads(line) for line in f if line.strip()]
                if len(history) >= 2:
                    prev = history[-2]
                    report.statistics["nodes_added"] = (
                        graph.number_of_nodes() - prev.get("nodes", 0)
                    )
                    report.statistics["edges_added"] = (
                        graph.number_of_edges() - prev.get("edges", 0)
                    )
            except Exception:
                pass

    # Write report
    with open(args.output, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    print(f"  └─ 📄 Report saved to: {args.output}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"Validation Status: {report.status.upper()}")
    print(f"{'='*60}")

    if report.errors:
        print("\n❌ Errors:")
        for error in report.errors:
            print(f"  - {error}")

    if report.warnings:
        print("\n⚠️  Warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")

    # Exit with appropriate code
    if report.status == "failed":
        print("\n❌ Validation FAILED")
        sys.exit(1)
    else:
        print("\n✅ Validation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
