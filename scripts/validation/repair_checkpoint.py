#!/usr/bin/env python3
"""
Checkpoint repair script for Freesound pipeline.

Architecture Notes:
    The checkpoint system uses a split architecture with type inconsistency
    by design:
    
    - Graph topology (.gpickle): Nodes use STRING IDs (e.g., "217542")
    - Metadata cache (.db): Uses INTEGER IDs (e.g., 217542)
    
    This repair script handles type conversion transparently when rebuilding
    nodes from metadata cache.

Repairs common checkpoint issues:
- Rebuilds graph topology from orphaned metadata entries
- Adds missing pagination_state to checkpoint metadata
- Fixes edge count mismatches
- Repairs corrupted checkpoint metadata

Exit codes:
- 0: All repairs successful
- 1: One or more repairs failed
"""

import json
import logging
import pickle
import shutil
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
class RepairResult:
    """Result of a repair operation."""
    
    success: bool
    message: str
    items_repaired: int = 0


class CheckpointRepairer:
    """Repairs checkpoint inconsistencies."""

    def __init__(self, checkpoint_dir: str):
        """
        Initialize repairer.

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
            raise FileNotFoundError(
                f"Checkpoint directory not found: {checkpoint_dir}"
            )
            
        self.logger = logging.getLogger(__name__)

        # Checkpoint file paths
        self.graph_path = self.checkpoint_dir / GRAPH_TOPOLOGY_FILENAME
        self.metadata_db_path = self.checkpoint_dir / METADATA_CACHE_FILENAME
        self.checkpoint_meta_path = self.checkpoint_dir / CHECKPOINT_META_FILENAME

    def repair_orphaned_metadata(self) -> RepairResult:
        """
        Repair orphaned metadata by rebuilding graph from metadata cache.
        
        This operation:
        1. Loads graph topology and metadata cache
        2. Identifies metadata entries not in graph
        3. Rebuilds graph nodes from orphaned metadata
        4. Updates checkpoint metadata with corrected counts

        Returns:
            RepairResult with success status, message, and count of repaired items
        """
        try:
            # Load graph and metadata
            graph = self._load_graph()
            
            # Use context manager to ensure proper cleanup
            with MetadataCache(str(self.metadata_db_path), self.logger) as metadata_cache:
                # Normalize IDs to strings for comparison
                graph_nodes = set(str(n) for n in graph.nodes())
                metadata_ids = set(
                    cache_id_to_graph_id(id) for id in metadata_cache.get_all_ids()
                )

                missing_in_graph = metadata_ids - graph_nodes

                if not missing_in_graph:
                    return RepairResult(
                        success=True,
                        message="No orphaned metadata found",
                        items_repaired=0
                    )

                self.logger.info(
                    f"Found {len(missing_in_graph)} orphaned metadata entries"
                )

                # Rebuild graph nodes from metadata
                all_metadata = metadata_cache.get_all_metadata()
                repaired_count = 0
                total = len(missing_in_graph)
                
                for i, sample_id_str in enumerate(missing_in_graph, 1):
                    # Metadata cache uses integer IDs
                    sample_id_int = graph_id_to_cache_id(sample_id_str)
                    metadata = all_metadata.get(sample_id_int)
                    
                    if metadata:
                        # Graph uses string IDs
                        graph.add_node(sample_id_str, **metadata)
                        repaired_count += 1
                        self.logger.debug(f"Added node {sample_id_str} from metadata")
                    else:
                        self.logger.warning(
                            f"Metadata entry {sample_id_int} exists in cache but "
                            f"returned None when retrieved"
                        )
                    
                    # Progress logging every 100 items
                    if i % 100 == 0:
                        self.logger.info(f"Progress: {i}/{total} nodes processed")

            # Save repaired graph
            self._save_graph(graph)

            self.logger.info(
                f"✓ Repaired graph: added {repaired_count} nodes from metadata"
            )

            # Update checkpoint metadata
            self._update_checkpoint_counts(graph)

            return RepairResult(
                success=True,
                message=f"Successfully added {repaired_count} nodes from metadata",
                items_repaired=repaired_count
            )

        except (IOError, OSError, FileNotFoundError) as e:
            self.logger.error(f"Failed to read/write checkpoint files: {e}")
            return RepairResult(
                success=False,
                message=f"File operation failed: {e}",
                items_repaired=0
            )
        except (TypeError, ValueError, pickle.UnpicklingError) as e:
            self.logger.error(f"Invalid checkpoint data: {e}")
            return RepairResult(
                success=False,
                message=f"Data validation failed: {e}",
                items_repaired=0
            )
        except Exception as e:
            self.logger.exception("Unexpected error during orphaned metadata repair")
            return RepairResult(
                success=False,
                message=f"Unexpected error: {e}",
                items_repaired=0
            )

    def repair_pagination_state(self) -> RepairResult:
        """
        Add missing pagination_state to checkpoint metadata.
        
        This operation:
        1. Loads checkpoint metadata
        2. Checks if pagination_state exists
        3. Adds default pagination_state if missing

        Returns:
            RepairResult with success status and message
        """
        try:
            checkpoint_meta = self._load_checkpoint_metadata()

            # Check if pagination_state already exists
            if "pagination_state" in checkpoint_meta:
                return RepairResult(
                    success=True,
                    message="pagination_state already exists",
                    items_repaired=0
                )

            # Add default pagination_state
            checkpoint_meta["pagination_state"] = {
                "page": 1,
                "query": "",
                "sort": "downloads_desc",
            }

            self._save_checkpoint_metadata(checkpoint_meta)

            self.logger.info("✓ Added pagination_state to checkpoint metadata")
            return RepairResult(
                success=True,
                message="Successfully added pagination_state",
                items_repaired=1
            )

        except (IOError, OSError, FileNotFoundError) as e:
            self.logger.error(f"Failed to read/write checkpoint metadata: {e}")
            return RepairResult(
                success=False,
                message=f"File operation failed: {e}",
                items_repaired=0
            )
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Invalid checkpoint metadata: {e}")
            return RepairResult(
                success=False,
                message=f"JSON parsing failed: {e}",
                items_repaired=0
            )
        except Exception as e:
            self.logger.exception("Unexpected error during pagination state repair")
            return RepairResult(
                success=False,
                message=f"Unexpected error: {e}",
                items_repaired=0
            )

    def repair_edge_counts(self) -> RepairResult:
        """
        Fix edge count mismatch in checkpoint metadata.
        
        This operation:
        1. Loads graph topology and checkpoint metadata
        2. Compares actual edge count with metadata
        3. Updates metadata if mismatch found

        Returns:
            RepairResult with success status and message
        """
        try:
            graph = self._load_graph()
            checkpoint_meta = self._load_checkpoint_metadata()

            expected_edges = checkpoint_meta.get("edge_count", 0)
            actual_edges = graph.number_of_edges()

            if expected_edges == actual_edges:
                return RepairResult(
                    success=True,
                    message=f"Edge count is correct ({actual_edges} edges)",
                    items_repaired=0
                )

            # Update edge count
            checkpoint_meta["edge_count"] = actual_edges
            self._save_checkpoint_metadata(checkpoint_meta)

            self.logger.info(
                f"✓ Updated edge count: {expected_edges} → {actual_edges}"
            )
            
            return RepairResult(
                success=True,
                message=f"Updated edge count from {expected_edges} to {actual_edges}",
                items_repaired=1
            )

        except (IOError, OSError, FileNotFoundError) as e:
            self.logger.error(f"Failed to read/write checkpoint files: {e}")
            return RepairResult(
                success=False,
                message=f"File operation failed: {e}",
                items_repaired=0
            )
        except (TypeError, ValueError, pickle.UnpicklingError, json.JSONDecodeError) as e:
            self.logger.error(f"Invalid checkpoint data: {e}")
            return RepairResult(
                success=False,
                message=f"Data validation failed: {e}",
                items_repaired=0
            )
        except Exception as e:
            self.logger.exception("Unexpected error during edge count repair")
            return RepairResult(
                success=False,
                message=f"Unexpected error: {e}",
                items_repaired=0
            )

    def repair_missing_metadata(self) -> RepairResult:
        """
        Repair missing metadata entries for nodes in graph.
        
        This operation:
        1. Loads graph topology and metadata cache
        2. Identifies nodes in graph without metadata
        3. Removes orphaned nodes (cannot recover metadata)
        4. Updates checkpoint metadata with corrected counts

        Returns:
            RepairResult with success status, message, and count of repaired items
        """
        try:
            # Load graph and metadata
            graph = self._load_graph()
            
            # Use context manager to ensure proper cleanup
            with MetadataCache(str(self.metadata_db_path), self.logger) as metadata_cache:
                # Normalize IDs to strings for comparison
                graph_nodes = set(str(n) for n in graph.nodes())
                metadata_ids = set(
                    cache_id_to_graph_id(id) for id in metadata_cache.get_all_ids()
                )

                missing_metadata = graph_nodes - metadata_ids

                if not missing_metadata:
                    return RepairResult(
                        success=True,
                        message="All nodes have metadata",
                        items_repaired=0
                    )

                self.logger.info(
                    f"Found {len(missing_metadata)} nodes without metadata"
                )

            # Create backup before destructive operation
            backup_path = self.checkpoint_dir / "graph_topology_backup.gpickle"
            shutil.copy2(self.graph_path, backup_path)
            
            try:
                # Remove nodes without metadata (cannot recover)
                total = len(missing_metadata)
                for i, node_id in enumerate(missing_metadata, 1):
                    graph.remove_node(node_id)
                    self.logger.debug(f"Removed node {node_id} (no metadata)")
                    
                    # Progress logging every 100 items
                    if i % 100 == 0:
                        self.logger.info(f"Progress: {i}/{total} nodes removed")

                # Save repaired graph
                self._save_graph(graph)
                
                # Remove backup on success
                backup_path.unlink()

                self.logger.info(
                    f"✓ Removed {len(missing_metadata)} nodes without metadata"
                )

                # Update checkpoint metadata
                self._update_checkpoint_counts(graph)

                return RepairResult(
                    success=True,
                    message=f"Removed {len(missing_metadata)} nodes without metadata",
                    items_repaired=len(missing_metadata)
                )
                
            except Exception as e:
                # Restore from backup on failure
                if backup_path.exists():
                    self.logger.error(f"Repair failed, restoring from backup: {e}")
                    shutil.copy2(backup_path, self.graph_path)
                    backup_path.unlink()
                raise

        except (IOError, OSError, FileNotFoundError) as e:
            self.logger.error(f"Failed to read/write checkpoint files: {e}")
            return RepairResult(
                success=False,
                message=f"File operation failed: {e}",
                items_repaired=0
            )
        except (TypeError, ValueError, pickle.UnpicklingError) as e:
            self.logger.error(f"Invalid checkpoint data: {e}")
            return RepairResult(
                success=False,
                message=f"Data validation failed: {e}",
                items_repaired=0
            )
        except Exception as e:
            self.logger.exception("Unexpected error during missing metadata repair")
            return RepairResult(
                success=False,
                message=f"Unexpected error: {e}",
                items_repaired=0
            )

    def repair_corrupted_checkpoint(self) -> RepairResult:
        """
        Attempt to repair corrupted checkpoint files.
        
        This operation:
        1. Validates checkpoint file integrity
        2. Attempts to recover from corruption
        3. Rebuilds checkpoint metadata if corrupted

        Returns:
            RepairResult with success status and message
        """
        try:
            # Check if checkpoint metadata is corrupted
            try:
                checkpoint_meta = self._load_checkpoint_metadata()
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Checkpoint metadata corrupted: {e}")
                
                # Attempt to rebuild from graph and metadata cache
                try:
                    graph = self._load_graph()
                    
                    # Use context manager to ensure proper cleanup
                    with MetadataCache(str(self.metadata_db_path), self.logger) as metadata_cache:
                        # Create minimal checkpoint metadata
                        checkpoint_meta = {
                            "version": "2.0",
                            "total_nodes": graph.number_of_nodes(),
                            "total_edges": graph.number_of_edges(),
                            "edge_count": graph.number_of_edges(),  # Backward compatibility
                            "pagination_state": {
                                "page": 1,
                                "query": "",
                                "sort": "downloads_desc"
                            }
                        }
                    
                    self._save_checkpoint_metadata(checkpoint_meta)
                    
                    self.logger.info("✓ Rebuilt checkpoint metadata from graph")
                    return RepairResult(
                        success=True,
                        message="Rebuilt corrupted checkpoint metadata",
                        items_repaired=1
                    )
                    
                except Exception as rebuild_error:
                    self.logger.error(f"Failed to rebuild metadata: {rebuild_error}")
                    return RepairResult(
                        success=False,
                        message=f"Cannot rebuild metadata: {rebuild_error}",
                        items_repaired=0
                    )

            # Check if graph is corrupted
            try:
                graph = self._load_graph()
                # Validate graph structure
                if not isinstance(graph, (nx.Graph, nx.DiGraph)):
                    raise TypeError("Invalid graph type")
            except (pickle.UnpicklingError, TypeError) as e:
                self.logger.error(f"Graph topology corrupted: {e}")
                return RepairResult(
                    success=False,
                    message=f"Graph topology corrupted and cannot be recovered: {e}",
                    items_repaired=0
                )

            # If we get here, checkpoint is not corrupted
            return RepairResult(
                success=True,
                message="Checkpoint files are not corrupted",
                items_repaired=0
            )

        except Exception as e:
            self.logger.exception("Unexpected error during corruption repair")
            return RepairResult(
                success=False,
                message=f"Unexpected error: {e}",
                items_repaired=0
            )

    def repair_all(self) -> dict[str, Any]:
        """
        Run all repair operations with detailed before/after statistics.
        
        Executes repairs in order:
        1. Corrupted checkpoint files (validates/rebuilds)
        2. Orphaned metadata (rebuilds missing nodes)
        3. Missing metadata entries (removes orphaned nodes)
        4. Edge counts (fixes metadata mismatch)
        5. Pagination state (adds if missing)

        Returns:
            Dictionary with:
            - 'results': mapping repair name to RepairResult
            - 'statistics': before/after statistics
            - 'summary': overall summary
        """
        self.logger.info("Starting comprehensive checkpoint repair...")

        # Collect before statistics
        before_stats = self._collect_statistics()

        # Run all repair operations
        results = {}

        # 1. Check for corrupted files first
        results["corrupted_checkpoint"] = self.repair_corrupted_checkpoint()

        # 2. Repair orphaned metadata (adds missing nodes)
        results["orphaned_metadata"] = self.repair_orphaned_metadata()

        # 3. Repair missing metadata entries (removes orphaned nodes)
        results["missing_metadata"] = self.repair_missing_metadata()

        # 4. Repair edge counts (updates metadata)
        results["edge_counts"] = self.repair_edge_counts()

        # 5. Repair pagination state (adds if missing)
        results["pagination_state"] = self.repair_pagination_state()

        # Collect after statistics
        after_stats = self._collect_statistics()

        # Generate summary
        total_repairs = sum(r.items_repaired for r in results.values())
        all_success = all(r.success for r in results.values())

        summary = {
            "total_operations": len(results),
            "successful_operations": sum(1 for r in results.values() if r.success),
            "failed_operations": sum(1 for r in results.values() if not r.success),
            "total_items_repaired": total_repairs,
            "overall_success": all_success
        }

        self.logger.info(
            f"Repair complete: {summary['successful_operations']}/{summary['total_operations']} "
            f"operations successful, {total_repairs} items repaired"
        )

        return {
            "results": results,
            "statistics": {
                "before": before_stats,
                "after": after_stats
            },
            "summary": summary
        }

    def _collect_statistics(self) -> dict[str, Any]:
        """
        Collect current checkpoint statistics.
        
        Returns:
            Dictionary with checkpoint statistics
        """
        stats = {
            "graph_exists": False,
            "metadata_exists": False,
            "checkpoint_meta_exists": False,
            "node_count": 0,
            "edge_count": 0,
            "metadata_count": 0
        }

        try:
            if self.graph_path.exists():
                stats["graph_exists"] = True
                graph = self._load_graph()
                stats["node_count"] = graph.number_of_nodes()
                stats["edge_count"] = graph.number_of_edges()
        except Exception as e:
            self.logger.debug(f"Could not load graph for statistics: {e}")

        try:
            if self.metadata_db_path.exists():
                stats["metadata_exists"] = True
                # Use context manager to ensure proper cleanup
                with MetadataCache(str(self.metadata_db_path), self.logger) as metadata_cache:
                    stats["metadata_count"] = len(metadata_cache.get_all_ids())
        except Exception as e:
            self.logger.debug(f"Could not load metadata for statistics: {e}")

        try:
            if self.checkpoint_meta_path.exists():
                stats["checkpoint_meta_exists"] = True
        except Exception as e:
            self.logger.debug(f"Could not check checkpoint metadata: {e}")

        return stats

    def _load_graph(self) -> nx.DiGraph:
        """
        Load graph topology from pickle file.
        
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
            
        # Validate loaded graph
        if not isinstance(graph, (nx.Graph, nx.DiGraph)):
            raise TypeError(
                f"Expected NetworkX Graph or DiGraph, got {type(graph).__name__}"
            )
            
        return graph

    def _save_graph(self, graph: nx.DiGraph) -> None:
        """
        Save graph topology to pickle file.
        
        Args:
            graph: NetworkX graph to save
            
        Raises:
            IOError: If file cannot be written
        """
        with open(self.graph_path, "wb") as f:
            pickle.dump(graph, f, pickle.HIGHEST_PROTOCOL)

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

    def _save_checkpoint_metadata(self, metadata: dict[str, Any]) -> None:
        """
        Save checkpoint metadata to JSON file.
        
        Args:
            metadata: Checkpoint metadata dictionary
            
        Raises:
            IOError: If file cannot be written
        """
        with open(self.checkpoint_meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _update_checkpoint_counts(self, graph: nx.DiGraph) -> None:
        """
        Update node and edge counts in checkpoint metadata.
        
        Args:
            graph: NetworkX graph with current state
            
        Raises:
            IOError: If file cannot be read/written
        """
        checkpoint_meta = self._load_checkpoint_metadata()
        # Use consistent field names with validation script
        checkpoint_meta["total_nodes"] = graph.number_of_nodes()
        checkpoint_meta["total_edges"] = graph.number_of_edges()
        # Also update edge_count for backward compatibility
        checkpoint_meta["edge_count"] = graph.number_of_edges()
        self._save_checkpoint_metadata(checkpoint_meta)


def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get checkpoint directory from command line or use default
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        checkpoint_dir = sys.argv[1]
    else:
        checkpoint_dir = "data/freesound_library"

    try:
        # Run repairs
        repairer = CheckpointRepairer(checkpoint_dir)
        repair_data = repairer.repair_all()
    except (ValueError, FileNotFoundError) as e:
        print(f"\nError: {e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}\n", file=sys.stderr)
        logging.exception("Unexpected error during repair")
        sys.exit(1)

    # Extract components
    results = repair_data["results"]
    statistics = repair_data["statistics"]
    summary = repair_data["summary"]

    # Print results
    print("\n" + "=" * 60)
    print("CHECKPOINT REPAIR RESULTS")
    print("=" * 60)

    # Print before/after statistics
    print("\nBefore Repair:")
    before = statistics["before"]
    print(f"  Nodes: {before['node_count']}")
    print(f"  Edges: {before['edge_count']}")
    print(f"  Metadata entries: {before['metadata_count']}")
    print(f"  Graph exists: {'YES' if before['graph_exists'] else 'NO'}")
    print(f"  Metadata exists: {'YES' if before['metadata_exists'] else 'NO'}")
    print(f"  Checkpoint metadata exists: {'YES' if before['checkpoint_meta_exists'] else 'NO'}")

    print("\nAfter Repair:")
    after = statistics["after"]
    print(f"  Nodes: {after['node_count']}")
    print(f"  Edges: {after['edge_count']}")
    print(f"  Metadata entries: {after['metadata_count']}")
    print(f"  Graph exists: {'YES' if after['graph_exists'] else 'NO'}")
    print(f"  Metadata exists: {'YES' if after['metadata_exists'] else 'NO'}")
    print(f"  Checkpoint metadata exists: {'YES' if after['checkpoint_meta_exists'] else 'NO'}")

    # Print repair operations
    print("\nRepair Operations:")
    for repair_name, result in results.items():
        status = "SUCCESS" if result.success else "FAILED"
        print(f"\n  {repair_name}: {status}")
        print(f"    {result.message}")
        
        if result.items_repaired > 0:
            print(f"    Items repaired: {result.items_repaired}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total operations: {summary['total_operations']}")
    print(f"Successful: {summary['successful_operations']}")
    print(f"Failed: {summary['failed_operations']}")
    print(f"Total items repaired: {summary['total_items_repaired']}")
    print(f"Overall status: {'SUCCESS' if summary['overall_success'] else 'FAILED'}")
    print("=" * 60)

    # Exit with appropriate code
    sys.exit(0 if summary['overall_success'] else 1)


if __name__ == "__main__":
    main()
