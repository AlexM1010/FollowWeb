"""
Incremental Freesound data loader with checkpoint support and queue-based recursive fetching.

This module extends FreesoundLoader with incremental graph building capabilities,
checkpoint management, and time-limited execution for long-running operations.

Key Features:
    - Queue-based breadth-first search (BFS) for recursive similar sounds discovery
    - Two-pass processing strategy for correct edge preservation
    - Checkpoint support for crash recovery and resumable operations
    - Time-limited execution with graceful stopping
    - Progress tracking and statistics

Queue-Based BFS:
    Uses a FIFO queue (collections.deque) to process samples breadth-first during
    recursive discovery. Each queue item contains a (sample, depth) tuple, ensuring
    all samples at depth N are processed before moving to depth N+1.

Two-Pass Processing:
    Pass 1: Discovers nodes and stores relationships in a pending_edges dictionary
    Pass 2: Adds edges between discovered nodes using stored relationships

    This approach ensures edges are not lost when target nodes haven't been
    discovered yet during the first pass.
"""

import heapq
import time
from datetime import datetime, timezone
from typing import Any, Optional, Union, cast

import networkx as nx

from ...core.exceptions import DataProcessingError
from ...output.formatters import EmojiFormatter
from ...utils import ProgressTracker
from ...utils.math import format_time_duration
from ...utils.validation import validate_choice
from ..backup_manager import BackupManager
from ..checkpoint import GraphCheckpoint
from .freesound import FreesoundLoader


class IncrementalFreesoundLoader(FreesoundLoader):
    """
    Incremental Freesound loader with checkpoint support and queue-based recursive fetching.

    Extends FreesoundLoader to support:
    - Checkpoint loading and saving for crash recovery
    - Incremental processing (skip already-processed samples)
    - Time-limited execution with graceful stopping
    - Progress tracking and statistics
    - Deleted sample cleanup
    - adaptable metadata updates
    - Queue-based BFS for recursive similar sounds discovery
    - Two-pass processing for correct edge preservation

    The loader maintains a checkpoint file that tracks:
    - Current graph state
    - Set of processed sample IDs
    - Processing metadata (timestamp, progress, etc.)

    Two-Pass Processing Strategy:
        When using recursive fetching (depth > 0), the loader uses a two-pass approach
        to ensure all edges are preserved correctly:

        Pass 1 (Node Discovery):
            - Uses a FIFO queue to process samples breadth-first
            - Adds nodes to the graph as they are discovered
            - Stores similarity relationships in a pending_edges dictionary
            - Does NOT add edges during this pass (target nodes may not exist yet)
            - Continues until depth limit or max_total_samples is reached

        Pass 2 (Edge Creation):
            - Iterates through stored relationships from Pass 1
            - Adds edges only between nodes that both exist in the graph
            - Makes NO additional API calls (uses stored relationships)
            - Filters out self-loops and duplicate edges

        This approach solves the edge preservation problem where edges were lost
        because target nodes hadn't been discovered yet when the source node was
        processed.

    Attributes:
        checkpoint: GraphCheckpoint instance for state management
        processed_ids: Set of already-processed sample IDs
        graph: Current graph state (loaded from checkpoint or new)
        start_time: Processing start time for time limit tracking
        checkpoint_interval: Number of samples between checkpoint saves
        max_runtime_hours: Maximum runtime before graceful stop
        verify_existing_sounds: Whether to verify existing samples via API

    Example:
        # Basic usage with recursive fetching
        loader = IncrementalFreesoundLoader(
            config={
                'api_key': 'your_key',
                'checkpoint_dir': 'checkpoints',
                'checkpoint_interval': 50,
                'max_runtime_hours': 2.0
            }
        )

        # Fetch with 2 levels of recursion
        data = loader.fetch_data(
            query='drum',
            max_samples=100,
            recursive_depth=2,
            max_total_samples=100
        )

        # Build the final graph
        graph = loader.build_graph(data)
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize incremental loader with checkpoint support.

        Args:
            config: Configuration dictionary with optional keys:
                   - checkpoint_dir: Directory for checkpoint files (default: 'checkpoints')
                   - checkpoint_interval: Samples between saves (default: 50)
                   - max_runtime_hours: Max runtime before stop (default: None)
                   - verify_existing_sounds: Verify samples via API (default: False)
                   - max_samples_mode: Collection mode - 'limit' or 'queue-empty' (default: 'limit')
                   - max_requests: Maximum API requests per session (default: 1950)
                   Plus all FreesoundLoader config options
        """
        super().__init__(config)

        # Checkpoint configuration
        checkpoint_dir = self.config.get("checkpoint_dir", "data/freesound_library")
        self.checkpoint_interval = self.config.get("checkpoint_interval", 50)
        self.max_runtime_hours = self.config.get("max_runtime_hours")
        self.verify_existing_sounds = self.config.get("verify_existing_sounds", False)
        self.max_samples_mode = self.config.get("max_samples_mode", "limit")

        # API quota circuit breaker
        self.session_request_count = 0
        self.max_requests = self.config.get("max_requests", 1950)

        # Statistics tracking
        self.stats: dict[str, Union[int, list[int]]] = {
            "api_requests_saved": 0,
            "samples_skipped": 0,
            "new_samples_per_expansion": [],
            "dormant_nodes_identified": 0,
            "throttle_retries": 0,
            "failed_requests": 0,
            "user_edges_created": 0,
            "pack_edges_created": 0,
        }

        # Validate max_samples_mode
        validate_choice(
            self.max_samples_mode, "max_samples_mode", ["limit", "queue-empty"]
        )

        # Use persistent library file (committed to Git for crash recovery)
        # This file grows over time and persists across runs
        checkpoint_filename = "freesound_library.pkl"
        checkpoint_path = f"{checkpoint_dir}/{checkpoint_filename}"
        self.checkpoint = GraphCheckpoint(checkpoint_path)

        # Initialize backup manager with configurable intervals
        self.backup_manager = BackupManager(
            backup_dir=checkpoint_dir,
            config={
                "backup_interval_nodes": self.config.get("backup_interval_nodes", 25),
                "backup_retention_count": self.config.get("backup_retention_count", 10),
                "enable_compression": self.config.get("backup_compression", True),
                "enable_tiered_backups": self.config.get("tiered_backups", True),
                "compression_age_days": self.config.get("compression_age_days", 7),
            },
            logger=self.logger,
        )

        # Backup path for safety
        self.backup_dir = checkpoint_dir

        # State tracking
        self.processed_ids: set[str] = set()
        self.graph: nx.DiGraph = nx.DiGraph()
        self.start_time: Optional[float] = None

        # Try to load existing checkpoint
        self._load_checkpoint()

        self.logger.info(
            f"IncrementalFreesoundLoader initialized: "
            f"checkpoint_interval={self.checkpoint_interval}, "
            f"max_runtime_hours={self.max_runtime_hours}, "
            f"max_requests={self.max_requests}"
        )

    def _load_checkpoint(self) -> None:
        """Load checkpoint using split architecture (graph topology + SQLite metadata)."""
        import json
        from pathlib import Path

        from ..storage import MetadataCache

        checkpoint_dir = Path(
            self.config.get("checkpoint_dir", "data/freesound_library")
        )

        # Check for split checkpoint files
        topology_path = checkpoint_dir / "graph_topology.gpickle"
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        checkpoint_meta_path = checkpoint_dir / "checkpoint_metadata.json"

        # Try loading split checkpoint first (new architecture)
        if topology_path.exists() and metadata_db_path.exists():
            try:
                # Load graph topology (edges only, no attributes)
                import pickle

                with open(topology_path, "rb") as f:
                    # nosec B301 - Loading our own checkpoint data, not untrusted input
                    self.graph = pickle.load(f)  # nosec

                # Connect to metadata cache
                self.metadata_cache = MetadataCache(str(metadata_db_path), self.logger)

                # Load checkpoint metadata
                if checkpoint_meta_path.exists():
                    with open(checkpoint_meta_path) as f:
                        checkpoint_metadata = json.load(f)

                    self.processed_ids = set(
                        checkpoint_metadata.get("processed_ids", [])
                    )
                    last_update = checkpoint_metadata.get("timestamp", "unknown")

                    self.logger.info(
                        f"Resumed from split checkpoint: {self.graph.number_of_nodes()} nodes, "
                        f"{len(self.processed_ids)} processed samples, "
                        f"last update: {last_update}"
                    )
                else:
                    # No metadata file, reconstruct from graph
                    self.processed_ids = {str(node) for node in self.graph.nodes()}
                    self.logger.warning(
                        "No checkpoint metadata found, reconstructed from graph"
                    )

                return

            except Exception as e:
                self.logger.error(f"Failed to load split checkpoint: {e}")
                # Fall through to try legacy checkpoint

        # Fall back to legacy checkpoint (old architecture)
        checkpoint_data = self.checkpoint.load()

        if checkpoint_data:
            self.graph = checkpoint_data["graph"]
            self.processed_ids = checkpoint_data["processed_ids"]

            # Load sound cache for efficiency (avoids re-fetching known samples)
            self._sound_cache = checkpoint_data.get("sound_cache", {})
            if self._sound_cache:
                self.logger.info(
                    f"Loaded sound cache with {len(self._sound_cache)} samples"
                )

            metadata = checkpoint_data.get("metadata", {})
            last_update = metadata.get("timestamp", "unknown")

            self.logger.info(
                f"Resumed from legacy checkpoint: {self.graph.number_of_nodes()} nodes, "
                f"{len(self.processed_ids)} processed samples, "
                f"last update: {last_update}"
            )

            # Migrate to split architecture
            self.logger.info("Migrating legacy checkpoint to split architecture...")
            self._migrate_to_split_checkpoint()
        else:
            # No checkpoint exists, initialize metadata cache
            from ..storage import MetadataCache

            checkpoint_dir = Path(
                self.config.get("checkpoint_dir", "data/freesound_library")
            )
            metadata_db_path = checkpoint_dir / "metadata_cache.db"
            self.metadata_cache = MetadataCache(str(metadata_db_path), self.logger)

    def _migrate_to_split_checkpoint(self) -> None:
        """Migrate legacy checkpoint to split architecture."""
        from pathlib import Path

        from ..storage import MetadataCache

        checkpoint_dir = Path(
            self.config.get("checkpoint_dir", "data/freesound_library")
        )
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata cache
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        self.metadata_cache = MetadataCache(str(metadata_db_path), self.logger)

        # Extract metadata from graph nodes and store in SQLite
        metadata_dict = {}
        for node_id in self.graph.nodes():
            node_data = dict(self.graph.nodes[node_id])
            metadata_dict[int(node_id)] = node_data

        # Bulk insert metadata
        if metadata_dict:
            self.metadata_cache.bulk_insert(metadata_dict)
            self.logger.info(
                f"Migrated {len(metadata_dict)} node metadata entries to SQLite"
            )

        # Save split checkpoint
        self._save_checkpoint({"migration": "completed"})

        self.logger.info("Migration to split checkpoint architecture completed")

    def _save_checkpoint(self, metadata: Optional[dict[str, Any]] = None) -> None:
        """
        Save current state using split checkpoint architecture.

        Saves:
        1. Graph topology (edges only, no attributes) to .gpickle
        2. Sample metadata to SQLite database
        3. Checkpoint metadata to JSON

        Creates backups every 100 nodes to prevent data loss.

        Args:
            metadata: Optional metadata to include in checkpoint
        """
        import json
        from pathlib import Path

        checkpoint_dir = Path(
            self.config.get("checkpoint_dir", "data/freesound_library")
        )
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Define checkpoint file paths
        topology_path = checkpoint_dir / "graph_topology.gpickle"
        metadata_db_path = checkpoint_dir / "metadata_cache.db"

        # Prepare checkpoint metadata
        checkpoint_metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "processed_ids": list(self.processed_ids),
        }

        # Add validation history to metadata if not already present
        if "validation_history" not in checkpoint_metadata:
            # Try to get existing validation history from previous checkpoint
            checkpoint_meta_path = checkpoint_dir / "checkpoint_metadata.json"
            if checkpoint_meta_path.exists():
                try:
                    with open(checkpoint_meta_path) as f:
                        existing_metadata = json.load(f)
                    existing_validation_history = existing_metadata.get(
                        "validation_history", {}
                    )
                    checkpoint_metadata["validation_history"] = (
                        existing_validation_history
                    )
                except Exception:
                    checkpoint_metadata["validation_history"] = {
                        "last_full_existence_check": None,
                        "last_partial_existence_check": None,
                        "last_metadata_refresh": None,
                    }
            else:
                checkpoint_metadata["validation_history"] = {
                    "last_full_existence_check": None,
                    "last_partial_existence_check": None,
                    "last_metadata_refresh": None,
                }

        if metadata:
            # Preserve validation_history if it exists in metadata
            if "validation_history" in metadata:
                checkpoint_metadata["validation_history"] = metadata[
                    "validation_history"
                ]
            checkpoint_metadata.update(metadata)

        # 1. Save graph topology (clean graph without attributes)
        # Create a new graph with only edges (more memory fast than copy + clear)
        import networkx as nx

        graph_clean: nx.DiGraph = nx.DiGraph()
        graph_clean.add_edges_from(self.graph.edges())

        import pickle

        with open(topology_path, "wb") as f:
            pickle.dump(graph_clean, f, pickle.HIGHEST_PROTOCOL)

        # Explicitly delete to free memory immediately
        del graph_clean

        # 2. Save metadata to SQLite (only new/updated samples)
        if hasattr(self, "metadata_cache"):
            # Extract metadata from graph nodes
            metadata_dict = {}
            for node_id in self.graph.nodes():
                node_data = dict(self.graph.nodes[node_id])
                # Only save if metadata exists
                if node_data:
                    metadata_dict[int(node_id)] = node_data

            # Bulk insert/update metadata
            if metadata_dict:
                self.metadata_cache.bulk_insert(metadata_dict)
                self.logger.debug(
                    f"Saved {len(metadata_dict)} metadata entries to SQLite"
                )

        # 3. Save checkpoint metadata JSON
        checkpoint_meta_path = checkpoint_dir / "checkpoint_metadata.json"
        with open(checkpoint_meta_path, "w") as f:
            json.dump(checkpoint_metadata, f, indent=2)

        # 4. Also call the GraphCheckpoint.save() method for compatibility with tests
        # and to maintain the abstraction layer
        try:
            self.checkpoint.save(
                graph=self.graph,
                processed_ids=self.processed_ids,
                metadata=checkpoint_metadata,
                sound_cache=getattr(self, "_sound_cache", {}),
            )
        except Exception as e:
            self.logger.warning(f"GraphCheckpoint.save() failed: {e}")

        self.logger.debug(
            f"Checkpoint saved: {checkpoint_metadata['nodes']} nodes, "
            f"{checkpoint_metadata['edges']} edges"
        )

        # Use BackupManager for intelligent tiered backups
        if self.backup_manager.should_create_backup(self.graph.number_of_nodes()):
            metadata_db_path = checkpoint_dir / "metadata_cache.db"
            self.backup_manager.create_backup(
                topology_path=topology_path,
                metadata_db_path=metadata_db_path,
                checkpoint_metadata=checkpoint_metadata,
            )

    def _create_backup(self) -> None:
        """
        Create timestamped backups of split checkpoint files.

        Backs up both graph topology and metadata database.
        """
        try:
            import shutil
            from pathlib import Path

            checkpoint_dir = Path(
                self.config.get("checkpoint_dir", "data/freesound_library")
            )

            # Create backup filenames with timestamp and node count
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nodes = self.graph.number_of_nodes()

            # Backup graph topology
            topology_path = checkpoint_dir / "graph_topology.gpickle"
            if topology_path.exists():
                topology_backup = (
                    checkpoint_dir
                    / f"graph_topology_backup_{nodes}nodes_{timestamp}.gpickle"
                )
                shutil.copy2(topology_path, topology_backup)
                self.logger.info(f"📦 Topology backup created: {topology_backup.name}")

            # Backup metadata database
            metadata_db_path = checkpoint_dir / "metadata_cache.db"
            if metadata_db_path.exists():
                metadata_backup = (
                    checkpoint_dir
                    / f"metadata_cache_backup_{nodes}nodes_{timestamp}.db"
                )
                shutil.copy2(metadata_db_path, metadata_backup)
                self.logger.info(f"📦 Metadata backup created: {metadata_backup.name}")

        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")

    def _check_time_limit(self) -> bool:
        """
        Check if time limit has been reached.

        Returns:
            True if time limit reached, False otherwise
        """
        if not self.max_runtime_hours or not self.start_time:
            return False

        elapsed_hours = (time.time() - self.start_time) / 3600
        return elapsed_hours >= self.max_runtime_hours

    def _calculate_progress_stats(
        self, current: int, total: int, elapsed_seconds: float
    ) -> dict[str, Any]:
        """
        Calculate progress statistics.

        Args:
            current: Current sample count
            total: Total sample count
            elapsed_seconds: Elapsed time in seconds

        Returns:
            Dictionary with progress statistics
        """
        percentage = (current / total * 100) if total > 0 else 0
        remaining = total - current

        # Estimate time remaining
        if current > 0 and elapsed_seconds > 0:
            rate = current / elapsed_seconds
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_minutes = eta_seconds / 60
        else:
            eta_minutes = 0

        return {
            "percentage": percentage,
            "current": current,
            "total": total,
            "remaining": remaining,
            "elapsed_minutes": elapsed_seconds / 60,
            "eta_minutes": eta_minutes,
        }

    def fetch_data(  # type: ignore[override]
        self,
        query: Optional[str] = None,
        tags: Optional[list[str]] = None,
        max_samples: int = 1000,
        discovery_mode: str = "search",
        relationship_priority: float = 0.7,
        include_user_edges: bool = True,
        include_pack_edges: bool = True,
        include_tag_edges: bool = True,
        tag_similarity_threshold: float = 0.3,
    ) -> dict[str, Any]:
        """
        Fetch sample data incrementally with checkpoint support and edge generation.

        Overrides parent method to support incremental processing:
        - Skips already-processed samples
        - Saves checkpoints periodically
        - Respects time limits
        - Tracks progress statistics
        - Generates edges based on user, pack, and tag relationships

        Args:
            query: Text search query
            tags: List of tags to filter by
            max_samples: Maximum number of samples to fetch
            discovery_mode: Sample discovery strategy - "search", "relationships", or "mixed"
            relationship_priority: For mixed mode, ratio of pending vs search (0.0-1.0)
            include_user_edges: Create edges for same-user samples
            include_pack_edges: Create edges for same-pack samples
            include_tag_edges: Create edges for tag similarity
            tag_similarity_threshold: Minimum Jaccard similarity for tag edges

        Returns:
            Dictionary with 'samples' and edge statistics
        """
        # Note: Empty query string is valid per Freesound API docs (returns all sounds)
        if query is None and not tags:
            raise DataProcessingError(
                "Must provide either query or tags for Freesound search"
            )

        self.start_time = time.time()

        # Search for samples
        self.logger.info(
            f"Searching Freesound (incremental): query='{query}', tags={tags}, "
            f"max_samples={max_samples}, already_processed={len(self.processed_ids)}"
        )

        all_samples = self._search_samples(query, tags, max_samples)

        # Filter out already-processed samples
        new_samples = [s for s in all_samples if str(s["id"]) not in self.processed_ids]

        self.logger.info(
            f"Found {len(all_samples)} total samples, "
            f"{len(new_samples)} new samples to process"
        )

        if not new_samples:
            self.logger.info("No new samples to process")
            return {"samples": [], "relationships": {"similar": {}}}

        # Process samples incrementally with progress tracking
        processed_samples = []

        # Simplified processing - add all samples as nodes
        with ProgressTracker(
            total=len(new_samples),
            title="Processing new samples incrementally",
            logger=self.logger,
        ) as tracker:
            for i, sample in enumerate(new_samples):
                # Check time limit
                if self._check_time_limit():
                    elapsed = time.time() - self.start_time
                    stats = self._calculate_progress_stats(i, len(new_samples), elapsed)

                    self.logger.warning(
                        f"Time limit reached ({self.max_runtime_hours}h). "
                        f"Processed {stats['current']}/{stats['total']} samples "
                        f"({stats['percentage']:.1f}%). Saving checkpoint..."
                    )

                    self._save_checkpoint(
                        {"stopped_reason": "time_limit", "progress": stats}
                    )
                    break

                # Add sample to graph (simplified - no similar sounds)
                self._add_sample_to_graph(sample, include_similar=False)
                processed_samples.append(sample)

                # Mark as processed
                self.processed_ids.add(str(sample["id"]))

                # Periodic checkpoint save
                if (i + 1) % self.checkpoint_interval == 0:
                    elapsed = time.time() - self.start_time
                    stats = self._calculate_progress_stats(
                        i + 1, len(new_samples), elapsed
                    )

                    self.logger.info(
                        f"Progress: {stats['percentage']:.1f}% "
                        f"({stats['current']}/{stats['total']}), "
                        f"ETA: {stats['eta_minutes']:.1f} min"
                    )

                    self._save_checkpoint({"progress": stats})

                tracker.update(i + 1)

        # Generate edges if requested
        edge_stats = {}
        if processed_samples and (
            include_user_edges or include_pack_edges or include_tag_edges
        ):
            self.logger.info("Generating edges...")
            # Note: Edge generation methods should be implemented in earlier tasks
            # For now, we'll call the existing batch edge generation if available
            try:
                if hasattr(self, "_generate_all_edges"):
                    edge_stats = self._generate_all_edges(
                        include_user=include_user_edges,
                        include_pack=include_pack_edges,
                        include_tag=include_tag_edges,
                        tag_threshold=tag_similarity_threshold,
                    )
                else:
                    # Fallback to existing methods
                    if include_user_edges or include_pack_edges:
                        # Use existing batch edge generation
                        usernames = set()
                        pack_names = set()

                        for node_id in self.graph.nodes():
                            node_data = self.graph.nodes[node_id]
                            if include_user_edges:
                                username = node_data.get("user") or node_data.get(
                                    "username"
                                )
                                if username:
                                    usernames.add(username)
                            if include_pack_edges:
                                pack = node_data.get("pack")
                                if pack:
                                    pack_names.add(pack)

                        if include_user_edges and usernames:
                            user_edges = self._add_user_edges_batch(usernames)
                            edge_stats["user_edges_added"] = user_edges

                        if include_pack_edges and pack_names:
                            pack_edges = self._add_pack_edges_batch(pack_names)
                            edge_stats["pack_edges_added"] = pack_edges
            except Exception as e:
                self.logger.warning(f"Edge generation failed: {e}")

        # Final checkpoint save
        elapsed = time.time() - self.start_time
        final_stats = self._calculate_progress_stats(
            len(processed_samples), len(new_samples), elapsed
        )

        self._save_checkpoint(
            {"completed": True, "final_stats": final_stats, "edge_stats": edge_stats}
        )

        success_msg = EmojiFormatter.format(
            "success",
            f"Processed {len(processed_samples)} new samples in "
            f"{final_stats['elapsed_minutes']:.1f} minutes",
        )
        self.logger.info(success_msg)

        return {"samples": processed_samples, "edge_stats": edge_stats}

    def _process_samples_recursive(
        self,
        seed_samples: list[dict[str, Any]],
        depth: int,
        max_total_samples: int,
        include_similar: bool,
    ) -> None:
        """
        Process samples recursively using queue-based BFS with two-pass processing.

        This method implements a two-pass strategy to ensure all edges are preserved
        correctly during recursive discovery:

        Pass 1 (Node Discovery):
            Uses a FIFO queue to process samples breadth-first. Each queue item is a
            (sample, depth) tuple. As samples are processed:
            - Nodes are added to the graph immediately
            - Similar sounds are fetched via API
            - Relationships are stored in pending_edges dict (NOT added as edges yet)
            - Unprocessed similar samples are enqueued at depth+1
            - Processing continues until queue is empty or limits are reached

        Pass 2 (Edge Creation):
            After all nodes are discovered, iterates through pending_edges to add edges:
            - Only adds edges where both source and target nodes exist
            - Makes NO additional API calls (uses stored relationships)
            - Filters out self-loops and duplicate edges
            - Logs the number of edges added

        This approach solves the problem where edges were lost because target nodes
        didn't exist yet when the source node was processed.

        Args:
            seed_samples: Initial samples to start recursive discovery from
            depth: Maximum depth to recurse (0 = no recursion, 1 = one level, etc.)
            max_total_samples: Maximum total samples to discover across all depths
            include_similar: Whether to fetch similar sounds relationships

        Example:
            # Fetch drum samples with 2 levels of recursion
            seed_samples = [{'id': 12345, 'name': 'kick.wav', ...}]
            loader._process_samples_recursive(
                seed_samples=seed_samples,
                depth=2,
                max_total_samples=100,
                include_similar=True
            )
            # Result: Graph with up to 100 nodes connected by similarity edges
        """
        # Quality thresholds for expansion
        fetch_similar_threshold_downloads = self.config.get(
            "fetch_similar_threshold_downloads", 100
        )
        fetch_similar_threshold_rating = self.config.get(
            "fetch_similar_threshold_rating", 3.5
        )

        # Initialize priority queue with (priority, counter, sample, depth) tuples
        # Priority queue processes highest priority samples first (lower value = higher priority)
        # Counter ensures stable ordering for samples with same priority
        # Priority = negative of calculated score (for max-heap behavior)
        # Tuple format: (priority, counter, sample_dict, depth)
        priority_queue: list[tuple[float, int, dict[str, Any], int]] = []
        counter = 0
        for sample in seed_samples:
            # Calculate intelligent priority score
            priority_score = self.calculate_node_priority(sample)
            priority = -priority_score  # Negative for max-heap behavior
            heapq.heappush(priority_queue, (priority, counter, sample, 0))
            counter += 1

        # Dictionary to store relationships discovered during Pass 1
        # Maps source_id -> [(target_id, similarity_score), ...]
        pending_edges: dict[str, list[tuple[str, float]]] = {}

        # Dormant node tracking
        # Track number of NEW samples discovered during each node expansion
        self.config.get("dormant_penalty_multiplier", 0.01)
        dormant_nodes_count = 0

        # Counter for periodic checkpoint saves
        checkpoint_counter = 0
        start_time = time.time()

        self.logger.info(
            f"Starting recursive processing: depth={depth}, max_total={max_total_samples}, mode={self.max_samples_mode}"
        )
        self.logger.info(
            "Using priority-based processing: most popular samples (by downloads) first"
        )

        # Log mode-specific behavior
        if self.max_samples_mode == "limit":
            self.logger.info(
                EmojiFormatter.format(
                    "progress", f"Limit mode: Will stop at {max_total_samples} samples"
                )
            )
        else:
            self.logger.info(
                EmojiFormatter.format(
                    "progress",
                    "Queue-empty mode: Will continue until priority queue is empty (safety limit: 10000)",
                )
            )

        # ============================================================================
        # PASS 1: NODE DISCOVERY WITH PRIORITY QUEUE
        # ============================================================================
        # Process samples in priority order (most popular first). Each iteration:
        # 1. Dequeues highest priority (sample, depth) tuple
        # 2. Adds the sample as a node to the graph
        # 3. Fetches its similar sounds via API
        # 4. Stores relationships in pending_edges (does NOT add edges yet)
        # 5. Enqueues unprocessed similar samples with their priority
        # This ensures we build a connected graph starting from most useful samples
        # ============================================================================

        while priority_queue:
            # Dequeue next sample to process (highest priority = most popular)
            priority, _, sample, current_depth = heapq.heappop(priority_queue)
            sample_id = str(sample["id"])

            # Skip if already processed (handles duplicate queue entries)
            if sample_id in self.processed_ids:
                continue

            # Check circuit breaker BEFORE making any API calls
            if self._check_circuit_breaker():
                elapsed = time.time() - start_time
                self.logger.info(
                    f"Gracefully stopping after {format_time_duration(elapsed)}, "
                    f"saving checkpoint..."
                )
                self._save_checkpoint(
                    {
                        "stopped_reason": "circuit_breaker",
                        "api_requests_used": self.session_request_count,
                    }
                )
                return

            # Check if time limit has been reached
            if self._check_time_limit():
                elapsed = time.time() - start_time
                self.logger.warning(
                    f"Time limit reached after {format_time_duration(elapsed)}, "
                    f"saving checkpoint..."
                )
                self._save_checkpoint({"stopped_reason": "time_limit"})
                return

            # Check if we've reached the maximum number of samples (mode-dependent)
            if self.max_samples_mode == "limit":
                # Limit mode: Stop at max_total_samples
                if self.graph.number_of_nodes() >= max_total_samples:
                    elapsed = time.time() - start_time
                    self.logger.info(
                        EmojiFormatter.format(
                            "success",
                            f"Reached max_total_samples limit ({max_total_samples}) "
                            f"after {format_time_duration(elapsed)}",
                        )
                    )
                    break
            else:
                # Queue-empty mode: Continue until queue is empty, but enforce safety limit
                safety_limit = 10000
                if self.graph.number_of_nodes() >= safety_limit:
                    elapsed = time.time() - start_time
                    self.logger.warning(
                        EmojiFormatter.format(
                            "warning",
                            f"Reached safety limit ({safety_limit}) in queue-empty mode "
                            f"after {format_time_duration(elapsed)}",
                        )
                    )
                    break

            # Add node to graph (without edges - edges come in Pass 2)
            self._add_node_to_graph(sample)
            self.processed_ids.add(sample_id)
            checkpoint_counter += 1

            # Fetch similar sounds if we haven't reached the depth limit
            # Note: current_depth < depth (not <=) because we want to fetch
            # similar sounds for samples at depth N to discover samples at depth N+1
            if current_depth < depth and include_similar:
                # Apply quality thresholds - only expand from high-quality nodes
                downloads = sample.get("num_downloads", 0)
                avg_rating = sample.get("avg_rating", 0.0)

                # Skip expansion if sample doesn't meet minimum quality thresholds
                if (
                    downloads < fetch_similar_threshold_downloads
                    or avg_rating < fetch_similar_threshold_rating
                ):
                    self.stats["samples_skipped"] = (
                        cast(int, self.stats["samples_skipped"]) + 1
                    )
                    self.logger.debug(
                        f"Skipping expansion for {sample_id}: "
                        f"downloads={downloads} (threshold={fetch_similar_threshold_downloads}), "
                        f"rating={avg_rating:.1f} (threshold={fetch_similar_threshold_rating})"
                    )
                    continue

                self.logger.debug(
                    f"Fetching similar sounds for {sample_id} at depth {current_depth}"
                )
                try:
                    # Track new samples discovered before expansion
                    len(self.processed_ids)

                    # Fetch similar sounds via API
                    similar_list = self._fetch_similar_sounds_for_sample(int(sample_id))

                    # Store relationships for Pass 2 (edge creation)
                    # This is critical: we do NOT add edges here because target
                    # nodes may not exist yet. We'll add edges in Pass 2 after
                    # all nodes have been discovered.
                    if similar_list:
                        pending_edges[sample_id] = similar_list
                        self.logger.debug(
                            f"Stored {len(similar_list)} relationships for {sample_id}"
                        )
                    else:
                        self.logger.debug(f"No similar sounds found for {sample_id}")

                    # Track new samples discovered during expansion
                    new_samples_discovered = 0

                    # Enqueue unprocessed similar samples for next depth level
                    # Each similar sample will be processed at depth = current_depth + 1
                    # Priority by downloads ensures we explore most popular samples first
                    for similar_id, _score in similar_list:
                        similar_id_str = str(similar_id)

                        # Only enqueue if:
                        # 1. Not already processed (avoid duplicate work)
                        # 2. Within sample limit (respect max_total_samples)
                        if (
                            similar_id_str not in self.processed_ids
                            and self.graph.number_of_nodes() < max_total_samples
                        ):
                            try:
                                # Fetch metadata for the similar sample (return_sound=False by default)
                                similar_sample = cast(
                                    dict[str, Any],
                                    self._fetch_sample_metadata(similar_id),
                                )

                                # Count as new sample discovered
                                new_samples_discovered += 1

                                # Calculate intelligent priority score
                                similar_priority_score = self.calculate_node_priority(
                                    similar_sample
                                )
                                similar_priority = (
                                    -similar_priority_score
                                )  # Negative for max-heap

                                # Enqueue at next depth level with priority
                                heapq.heappush(
                                    priority_queue,
                                    (
                                        similar_priority,
                                        counter,
                                        similar_sample,
                                        current_depth + 1,
                                    ),
                                )
                                counter += 1
                            except Exception as e:
                                # Log but don't fail - continue with other samples
                                self.logger.debug(
                                    f"Could not fetch metadata for {similar_id}: {e}"
                                )

                    # Track expansion statistics
                    cast(list, self.stats["new_samples_per_expansion"]).append(
                        new_samples_discovered
                    )

                    # Dormant node detection: mark node as dormant if it yielded 0 new samples
                    if new_samples_discovered == 0:
                        # Mark node as dormant in graph
                        if sample_id in self.graph:
                            now = datetime.now(timezone.utc).isoformat()
                            self.graph.nodes[sample_id]["is_dormant"] = True
                            self.graph.nodes[sample_id]["dormant_since"] = now

                            # Recalculate priority score with dormant penalty
                            # This will apply the dormant_penalty_multiplier (default: 0.01)
                            updated_priority = self.calculate_node_priority(sample)
                            self.graph.nodes[sample_id]["priority_score"] = (
                                updated_priority
                            )

                            dormant_nodes_count += 1
                            self.stats["dormant_nodes_identified"] = (
                                cast(int, self.stats["dormant_nodes_identified"]) + 1
                            )

                            self.logger.debug(
                                f"Node {sample_id} marked as dormant (0 new samples discovered), "
                                f"priority score updated to {updated_priority:.2f}"
                            )

                except Exception as e:
                    # Log warning but continue processing other samples
                    self.logger.warning(
                        f"Failed to fetch similar sounds for {sample_id}: {e}"
                    )

            # Save checkpoint periodically to enable recovery from interruptions
            if checkpoint_counter >= self.checkpoint_interval:
                elapsed = time.time() - start_time
                self._save_checkpoint(
                    {
                        "depth": current_depth,
                        "pending_edges_count": len(pending_edges),
                        "elapsed": format_time_duration(elapsed),
                    }
                )
                checkpoint_counter = 0

        # ============================================================================
        # PASS 2: EDGE CREATION FROM STORED RELATIONSHIPS
        # ============================================================================
        # Now that all nodes have been discovered, we can safely add edges between
        # them. This pass:
        # 1. Iterates through pending_edges dictionary (from Pass 1)
        # 2. Adds edges only where both source and target nodes exist
        # 3. Makes NO additional API calls (uses stored relationships)
        # 4. Filters out self-loops and duplicate edges
        #
        # This solves the edge preservation problem: in Pass 1, when we discovered
        # that sample A is similar to sample B, sample B might not have been
        # discovered yet. Now that all nodes exist, we can add all the edges.
        # ============================================================================

        elapsed = time.time() - start_time
        self.logger.info(
            f"Node discovery complete in {format_time_duration(elapsed)}. "
            f"Adding edges between {len(self.graph.nodes())} discovered nodes..."
        )
        self.logger.info(f"Pending edges dictionary has {len(pending_edges)} entries")

        edge_count = 0
        edge_checkpoint_counter = 0
        edge_checkpoint_interval = max(
            10, len(pending_edges) // 10
        )  # Save every 10% or every 10 sources

        self.logger.info(
            f"Pass 2: Will save checkpoints every {edge_checkpoint_interval} sources "
            f"(~{100 / max(1, len(pending_edges) // edge_checkpoint_interval):.0f}% intervals)"
        )

        # Skip Pass 2 if no pending edges
        if len(pending_edges) == 0:
            self.logger.info("No pending edges to process, skipping Pass 2")
            return

        # Use progress tracker for Pass 2
        with ProgressTracker(
            total=len(pending_edges),
            title="Pass 2: Adding edges from stored relationships",
            logger=self.logger,
        ) as tracker:
            # Iterate through all stored relationships from Pass 1
            for idx, (source_id, similar_list) in enumerate(pending_edges.items()):
                # Verify source node exists (defensive programming)
                # It should always exist, but we check to be safe
                if source_id not in self.graph:
                    continue

                # Add edges to all similar samples
                for target_id, score in similar_list:
                    target_id_str = str(target_id)

                    # Add edge only if:
                    # 1. Target node exists in graph (may not if it was outside limits)
                    # 2. Edge doesn't already exist (avoid duplicates)
                    # 3. Not a self-loop (source != target)
                    if (
                        target_id_str in self.graph
                        and not self.graph.has_edge(source_id, target_id_str)
                        and source_id != target_id_str
                    ):
                        self.graph.add_edge(
                            source_id, target_id_str, type="similar", weight=score
                        )
                        edge_count += 1

                # Periodic checkpoint during Pass 2 to preserve edge data
                edge_checkpoint_counter += 1
                if edge_checkpoint_counter >= edge_checkpoint_interval:
                    progress_pct = ((idx + 1) / len(pending_edges)) * 100
                    self.logger.info(
                        f"Pass 2 checkpoint: {edge_count} edges added so far "
                        f"({progress_pct:.1f}% complete)"
                    )
                    self._save_checkpoint(
                        {
                            "pass2_progress": progress_pct,
                            "edges_added_so_far": edge_count,
                            "sources_processed": idx + 1,
                            "total_sources": len(pending_edges),
                        }
                    )
                    edge_checkpoint_counter = 0

                # Update progress tracker
                tracker.update(idx + 1)

        total_elapsed = time.time() - start_time
        self.logger.info(
            f"Added {edge_count} edges to graph in {format_time_duration(total_elapsed)}"
        )

        # Log dormant node statistics
        if dormant_nodes_count > 0:
            dormant_msg = EmojiFormatter.format(
                "info",
                f"Dormant nodes detected: {dormant_nodes_count} nodes yielded 0 new samples",
            )
            self.logger.info(dormant_msg)

        # Log complete API efficiency statistics
        self.log_api_efficiency_stats()

        # Final checkpoint with completion metadata
        self._save_checkpoint(
            {
                "completed": True,
                "edges_added": edge_count,
                "dormant_nodes_count": dormant_nodes_count,
                "total_elapsed": format_time_duration(total_elapsed),
                "api_stats": self.stats,
            }
        )

    def calculate_node_priority(self, sample: dict[str, Any]) -> float:
        """
        Calculate expansion priority for a node using weighted formula.

        Priority = (w1 * Downloads) + (w2 * Degree) - (w3 * Age_in_days)

        Dormant nodes receive a heavy penalty multiplier (default: 0.01)

        Higher priority = more valuable to expand from

        Args:
            sample: Sample dictionary with metadata

        Returns:
            Priority score (higher = better)
        """
        # Configurable weights
        w1 = self.config.get("priority_weight_downloads", 1.0)
        w2 = self.config.get("priority_weight_degree", 0.5)
        w3 = self.config.get("priority_weight_age", 0.1)
        dormant_penalty = self.config.get("dormant_penalty_multiplier", 0.01)

        # Extract metrics
        downloads = sample.get("num_downloads", 0)

        # Calculate degree (number of connections in graph)
        sample_id = str(sample["id"])
        degree: int = 0
        is_dormant = False

        if sample_id in self.graph:
            degree = self.graph.degree(sample_id)  # type: ignore[operator]
            is_dormant = self.graph.nodes[sample_id].get("is_dormant", False)

        # Calculate age in days since collection
        age_days = 0
        collected_at = sample.get("collected_at")
        if collected_at:
            try:
                collected_time = datetime.fromisoformat(
                    collected_at.replace("Z", "+00:00")
                )
                age_days = (datetime.now(timezone.utc) - collected_time).days
            except (ValueError, AttributeError):
                age_days = 0

        # Calculate base priority score
        priority = (w1 * downloads) + (w2 * degree) - (w3 * age_days)

        # Apply dormant penalty (heavily deprioritize dormant nodes)
        if is_dormant:
            priority *= dormant_penalty

        return priority

    def _increment_request_count(self) -> None:
        """Increment API request counter for circuit breaker."""
        self.session_request_count += 1

        # Log progress at milestones
        if self.session_request_count % 100 == 0:
            remaining = self.max_requests - self.session_request_count
            self.logger.info(
                f"API requests: {self.session_request_count}/{self.max_requests} "
                f"({remaining} remaining)"
            )

    def _check_circuit_breaker(self) -> bool:
        """
        Check if API quota circuit breaker should trigger.

        Returns:
            True if circuit breaker triggered (limit reached), False otherwise
        """
        if self.session_request_count >= self.max_requests:
            warning_msg = EmojiFormatter.format(
                "warning",
                f"Circuit breaker triggered: {self.session_request_count} requests "
                f"reached limit of {self.max_requests}",
            )
            self.logger.warning(warning_msg)
            return True
        return False

    def handle_throttling(self, attempt: int = 0, max_attempts: int = 3) -> bool:
        """
        Handle 429 throttling responses with exponential backoff and jitter.

        Uses exponential backoff with random jitter to prevent thundering herd
        problem when multiple clients retry simultaneously.

        Jitter formula: delay = base_delay + random.uniform(0, 0.5 * base_delay)
        This adds 0-50% random variation to prevent synchronized retries.

        Args:
            attempt: Current attempt number (0-indexed)
            max_attempts: Maximum number of retry attempts

        Returns:
            True if should retry, False if max attempts reached
        """
        import random

        if attempt >= max_attempts:
            error_msg = EmojiFormatter.format(
                "error", f"Max throttling retries ({max_attempts}) reached"
            )
            self.logger.error(error_msg)
            self.stats["failed_requests"] = cast(int, self.stats["failed_requests"]) + 1
            return False

        # Exponential backoff: 2s, 4s, 8s
        base_delay = 2 ** (attempt + 1)

        # Add random jitter (0 to 50% of base delay) to prevent thundering herd
        jitter = random.uniform(0, 0.5 * base_delay)
        actual_delay = base_delay + jitter

        warning_msg = EmojiFormatter.format(
            "warning",
            f"Throttled (429) - attempt {attempt + 1}/{max_attempts}, "
            f"waiting {actual_delay:.2f}s (base: {base_delay}s + jitter: {jitter:.2f}s)...",
        )
        self.logger.warning(warning_msg)

        self.stats["throttle_retries"] = cast(int, self.stats["throttle_retries"]) + 1
        time.sleep(actual_delay)
        return True

    def log_api_efficiency_stats(self) -> None:
        """
        Log complete API efficiency statistics.

        Logs:
        - API requests saved (cache hits)
        - Samples skipped (quality thresholds)
        - Total requests used vs limit
        - Frontier expansion stats
        - Batch expansion stats
        - Error statistics
        """
        # Calculate cache efficiency
        total_cache_ops = self._cache_hits + self._cache_misses
        cache_hit_ratio = (
            (self._cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
        )

        # Log API efficiency
        efficiency_msg = EmojiFormatter.format("success", "API Efficiency Statistics:")
        self.logger.info(efficiency_msg)
        self.logger.info(
            f"  Total API requests: {self.session_request_count}/{self.max_requests}"
        )
        self.logger.info(f"  Requests saved (cache): {self._cache_hits}")
        self.logger.info(f"  Cache hit ratio: {cache_hit_ratio:.1f}%")
        self.logger.info(
            f"  Samples skipped (quality): {self.stats['samples_skipped']}"
        )

        # Log frontier expansion stats
        expansion_list = cast(list, self.stats["new_samples_per_expansion"])
        if expansion_list:
            avg_new_samples = sum(expansion_list) / len(expansion_list)
            self.logger.info(f"  Avg new samples per expansion: {avg_new_samples:.1f}")

        self.logger.info(
            f"  Dormant nodes identified: {self.stats['dormant_nodes_identified']}"
        )

        # Log batch expansion stats
        if (
            cast(int, self.stats["user_edges_created"]) > 0
            or cast(int, self.stats["pack_edges_created"]) > 0
        ):
            batch_msg = EmojiFormatter.format("info", "Batch Expansion Statistics:")
            self.logger.info(batch_msg)
            self.logger.info(
                f"  User edges created: {self.stats['user_edges_created']}"
            )
            self.logger.info(
                f"  Pack edges created: {self.stats['pack_edges_created']}"
            )

        # Log error statistics
        if (
            cast(int, self.stats["throttle_retries"]) > 0
            or cast(int, self.stats["failed_requests"]) > 0
        ):
            error_msg = EmojiFormatter.format("warning", "Error Statistics:")
            self.logger.info(error_msg)
            self.logger.info(
                f"  Throttle retries (429): {self.stats['throttle_retries']}"
            )
            self.logger.info(f"  Failed requests: {self.stats['failed_requests']}")

    def handle_api_error(self, error: Exception, context: str) -> str:
        """
        Handle specific API error codes with appropriate actions.

        Error handling strategy:
        - 400: Log and skip (bad request)
        - 401: Fatal error (invalid credentials)
        - 403: Fatal error (forbidden)
        - 404: Mark as deleted, continue
        - 429: Retry with exponential backoff
        - 5xx: Retry with exponential backoff

        Args:
            error: Exception from API call
            context: Context string describing what was being attempted

        Returns:
            Action to take: 'skip', 'fatal', 'deleted', 'retry'
        """
        error_str = str(error).lower()

        # Check for specific error codes
        if "400" in error_str or "bad request" in error_str:
            error_msg = EmojiFormatter.format(
                "error", f"Bad request (400) in {context}: {error}"
            )
            self.logger.error(error_msg)
            return "skip"

        elif "401" in error_str or "unauthorized" in error_str:
            error_msg = EmojiFormatter.format(
                "error", f"FATAL: Invalid credentials (401) in {context}"
            )
            self.logger.error(error_msg)
            return "fatal"

        elif "403" in error_str or "forbidden" in error_str:
            error_msg = EmojiFormatter.format(
                "error", f"FATAL: Forbidden (403) in {context}"
            )
            self.logger.error(error_msg)
            return "fatal"

        elif "404" in error_str or "not found" in error_str:
            info_msg = EmojiFormatter.format(
                "info", f"Resource not found (404) in {context} - marking as deleted"
            )
            self.logger.info(info_msg)
            return "deleted"

        elif "429" in error_str or "throttl" in error_str or "rate limit" in error_str:
            warning_msg = EmojiFormatter.format(
                "warning", f"Rate limited (429) in {context} - will retry"
            )
            self.logger.warning(warning_msg)
            return "retry"

        elif "5" in error_str[:3]:  # 5xx errors
            warning_msg = EmojiFormatter.format(
                "warning", f"Server error (5xx) in {context} - will retry"
            )
            self.logger.warning(warning_msg)
            return "retry"

        else:
            # Unknown error - log and skip
            error_msg = EmojiFormatter.format(
                "error", f"Unknown error in {context}: {error}"
            )
            self.logger.error(error_msg)
            return "skip"

    def _add_batch_user_pack_edges(self) -> dict[str, int]:
        """
        Add user and pack relationship edges using batch filtering.

        This method aggregates unique usernames and pack names from collected samples,
        then uses batch text search filtering to discover relationships efficiently.

        Returns:
            Dictionary with statistics: user_edges_added, pack_edges_added
        """
        # Check if user/pack edges are enabled
        include_user_edges = self.config.get("include_user_edges", True)
        include_pack_edges = self.config.get("include_pack_edges", True)

        if not include_user_edges and not include_pack_edges:
            return {"user_edges_added": 0, "pack_edges_added": 0}

        stats = {"user_edges_added": 0, "pack_edges_added": 0}

        # Aggregate unique usernames and pack names from graph
        usernames = set()
        pack_names = set()

        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]

            if include_user_edges:
                username = node_data.get("user") or node_data.get("username")
                if username:
                    usernames.add(username)

            if include_pack_edges:
                pack = node_data.get("pack")
                if pack:
                    # Extract pack name from URI if needed
                    if isinstance(pack, str) and "/" in pack:
                        pack_name = pack.split("/")[-2]  # Extract from URI
                    else:
                        pack_name = pack
                    if pack_name:
                        pack_names.add(pack_name)

        self.logger.info(
            f"Batch edge creation: {len(usernames)} unique users, "
            f"{len(pack_names)} unique packs"
        )

        # Add user relationship edges
        if include_user_edges and usernames:
            user_edges = self._add_user_edges_batch(usernames)
            stats["user_edges_added"] = user_edges
            self.stats["user_edges_created"] = user_edges

        # Add pack relationship edges
        if include_pack_edges and pack_names:
            pack_edges = self._add_pack_edges_batch(pack_names)
            stats["pack_edges_added"] = pack_edges
            self.stats["pack_edges_created"] = pack_edges

        return stats

    def _add_user_edges_batch(self, usernames: set[str]) -> int:
        """
        Add edges between samples by the same user using batch filtering.

        Args:
            usernames: Set of unique usernames

        Returns:
            Number of edges added
        """
        edge_count = 0

        # Process usernames in batches (avoid overly long filter strings)
        batch_size = 50
        username_list = list(usernames)

        for i in range(0, len(username_list), batch_size):
            batch = username_list[i : i + batch_size]

            # Check circuit breaker
            if self._check_circuit_breaker():
                self.logger.warning(
                    "Circuit breaker triggered during user edge creation"
                )
                break

            try:
                # Build batch filter: username:("user1" OR "user2" OR ...)
                user_filter = "username:(" + " OR ".join(f'"{u}"' for u in batch) + ")"

                # Rate limit and increment counter
                self.rate_limiter.acquire()
                self._increment_request_count()

                # Search with batch filter
                results = self._retry_with_backoff(
                    self.client.text_search,
                    query="",
                    filter=user_filter,
                    page_size=150,
                    fields="id,username",
                )

                # Group samples by username
                samples_by_user: dict[str, list[Any]] = {}
                for sound in results:
                    username = sound.username if hasattr(sound, "username") else None
                    if username:
                        if username not in samples_by_user:
                            samples_by_user[username] = []
                        samples_by_user[username].append(str(sound.id))

                # Paginate if needed
                while results.next:
                    if self._check_circuit_breaker():
                        break

                    self.rate_limiter.acquire()
                    self._increment_request_count()
                    results = self._retry_with_backoff(results.next_page)

                    for sound in results:
                        username = (
                            sound.username if hasattr(sound, "username") else None
                        )
                        if username:
                            if username not in samples_by_user:
                                samples_by_user[username] = []
                            samples_by_user[username].append(str(sound.id))

                # Add edges between samples by same user
                for _username, sample_ids in samples_by_user.items():
                    # Only add edges for samples in our graph
                    graph_samples = [sid for sid in sample_ids if sid in self.graph]

                    # Add edges between all pairs
                    for j in range(len(graph_samples)):
                        for k in range(j + 1, len(graph_samples)):
                            source = graph_samples[j]
                            target = graph_samples[k]

                            # Add bidirectional edges
                            if not self.graph.has_edge(source, target):
                                self.graph.add_edge(
                                    source, target, type="by_same_user", weight=1.0
                                )
                                edge_count += 1
                            if not self.graph.has_edge(target, source):
                                self.graph.add_edge(
                                    target, source, type="by_same_user", weight=1.0
                                )
                                edge_count += 1

            except Exception as e:
                self.logger.warning(f"Failed to add user edges for batch: {e}")

        if edge_count > 0:
            self.logger.info(f"Added {edge_count} user relationship edges")

        return edge_count

    def _add_pack_edges_batch(self, pack_names: set[str]) -> int:
        """
        Add edges between samples in the same pack using batch filtering.

        Args:
            pack_names: Set of unique pack names

        Returns:
            Number of edges added
        """
        edge_count = 0

        # Process pack names in batches
        batch_size = 50
        pack_list = list(pack_names)

        for i in range(0, len(pack_list), batch_size):
            batch = pack_list[i : i + batch_size]

            # Check circuit breaker
            if self._check_circuit_breaker():
                self.logger.warning(
                    "Circuit breaker triggered during pack edge creation"
                )
                break

            try:
                # Build batch filter: pack_name:("pack1" OR "pack2" OR ...)
                pack_filter = (
                    "pack_tokenized:(" + " OR ".join(f'"{p}"' for p in batch) + ")"
                )

                # Rate limit and increment counter
                self.rate_limiter.acquire()
                self._increment_request_count()

                # Search with batch filter
                results = self._retry_with_backoff(
                    self.client.text_search,
                    query="",
                    filter=pack_filter,
                    page_size=150,
                    fields="id,pack",
                )

                # Group samples by pack
                samples_by_pack: dict[str, list[Any]] = {}
                for sound in results:
                    pack = sound.pack if hasattr(sound, "pack") else None
                    if pack:
                        # Extract pack name from URI if needed
                        if isinstance(pack, str) and "/" in pack:
                            pack_name = pack.split("/")[-2]
                        else:
                            pack_name = pack

                        if pack_name:
                            if pack_name not in samples_by_pack:
                                samples_by_pack[pack_name] = []
                            samples_by_pack[pack_name].append(str(sound.id))

                # Paginate if needed
                while results.next:
                    if self._check_circuit_breaker():
                        break

                    self.rate_limiter.acquire()
                    self._increment_request_count()
                    results = self._retry_with_backoff(results.next_page)

                    for sound in results:
                        pack = sound.pack if hasattr(sound, "pack") else None
                        if pack:
                            if isinstance(pack, str) and "/" in pack:
                                pack_name = pack.split("/")[-2]
                            else:
                                pack_name = pack

                            if pack_name:
                                if pack_name not in samples_by_pack:
                                    samples_by_pack[pack_name] = []
                                samples_by_pack[pack_name].append(str(sound.id))

                # Add edges between samples in same pack
                for _pack_name, sample_ids in samples_by_pack.items():
                    # Only add edges for samples in our graph
                    graph_samples = [sid for sid in sample_ids if sid in self.graph]

                    # Add edges between all pairs
                    for j in range(len(graph_samples)):
                        for k in range(j + 1, len(graph_samples)):
                            source = graph_samples[j]
                            target = graph_samples[k]

                            # Add bidirectional edges
                            if not self.graph.has_edge(source, target):
                                self.graph.add_edge(
                                    source, target, type="in_same_pack", weight=1.0
                                )
                                edge_count += 1
                            if not self.graph.has_edge(target, source):
                                self.graph.add_edge(
                                    target, source, type="in_same_pack", weight=1.0
                                )
                                edge_count += 1

            except Exception as e:
                self.logger.warning(f"Failed to add pack edges for batch: {e}")

        if edge_count > 0:
            self.logger.info(f"Added {edge_count} pack relationship edges")

        return edge_count

    def _add_node_to_graph(self, sample: dict[str, Any]) -> None:
        """
        Add a single sample node to the graph without edges.

        Calculates and stores priority_score for SQL-based seed selection.

        Args:
            sample: Sample dictionary with metadata
        """
        sample_id = str(sample["id"])

        # Add node if not already in graph
        if sample_id not in self.graph:
            now = datetime.now(timezone.utc).isoformat()

            # Calculate priority score for this node
            priority_score = self.calculate_node_priority(sample)

            self.graph.add_node(
                sample_id,
                name=sample["name"],
                tags=sample.get("tags", []),
                duration=sample.get("duration", 0),
                user=sample.get("username", ""),
                audio_url=sample.get("audio_url", ""),
                type="sample",
                collected_at=now,
                # Validation history timestamps (ISO format)
                last_existence_check_at=None,  # When we last verified sample exists
                last_metadata_update_at=now,  # When we last refreshed metadata
                # Priority scoring for SQL-based seed selection
                priority_score=priority_score,
                is_dormant=False,
            )

    def _add_sample_to_graph(
        self, sample: dict[str, Any], include_similar: bool = True
    ) -> None:
        """
        Add a single sample to the graph with relationships.

        Calculates and stores priority_score for SQL-based seed selection.

        Args:
            sample: Sample dictionary with metadata
            include_similar: Whether to fetch and add similar sounds
        """
        sample_id = str(sample["id"])

        # Add node if not already in graph
        if sample_id not in self.graph:
            now = datetime.now(timezone.utc).isoformat()

            # Calculate priority score for this node
            priority_score = self.calculate_node_priority(sample)

            self.graph.add_node(
                sample_id,
                name=sample["name"],
                tags=sample.get("tags", []),
                duration=sample.get("duration", 0),
                user=sample.get("username", ""),
                audio_url=sample.get("audio_url", ""),
                type="sample",
                collected_at=now,
                # Validation history timestamps (ISO format)
                last_existence_check_at=None,  # When we last verified sample exists
                last_metadata_update_at=now,  # When we last refreshed metadata
                # Priority scoring for SQL-based seed selection
                priority_score=priority_score,
                is_dormant=False,
            )

        # Fetch and add similar sounds relationships
        if include_similar:
            try:
                similar_list = self._fetch_similar_sounds_for_sample(int(sample["id"]))

                for target_id, similarity_score in similar_list:
                    target_node = str(target_id)

                    # Only add edge if target exists in graph
                    if target_node in self.graph:
                        self.graph.add_edge(
                            sample_id,
                            target_node,
                            type="similar",
                            weight=similarity_score,
                        )

            except Exception as e:
                self.logger.warning(
                    f"Failed to add similar sounds for {sample_id}: {e}"
                )

    def build_graph(self, data: dict[str, Any]) -> nx.DiGraph:
        """
        Return the incrementally-built graph.

        Overrides parent method to return the graph that has been built
        incrementally during fetch_data().

        Args:
            data: Dictionary from fetch_data() (not used in incremental mode)

        Returns:
            The incrementally-built NetworkX DiGraph
        """
        success_msg = EmojiFormatter.format(
            "success",
            f"Incremental graph complete: {self.graph.number_of_nodes():,} nodes, "
            f"{self.graph.number_of_edges():,} edges",
        )
        self.logger.info(success_msg)

        return self.graph

    def cleanup_deleted_samples(self) -> int:
        """
        Remove nodes for samples that no longer exist on Freesound.

        Queries the Freesound API to verify sample existence and removes
        nodes for samples that return 404. Uses rate limiting to avoid
        exceeding API limits.

        Returns:
            Number of deleted samples removed

        Raises:
            DataProcessingError: If verification is not enabled in config
        """
        if not self.verify_existing_sounds:
            raise DataProcessingError(
                "Sample verification not enabled. Set verify_existing_sounds=True"
            )

        self.logger.info(
            f"Verifying {self.graph.number_of_nodes()} samples for deletion..."
        )

        deleted_nodes = []

        with ProgressTracker(
            total=self.graph.number_of_nodes(),
            title="Verifying sample existence",
            logger=self.logger,
        ) as tracker:
            for i, node_id in enumerate(list(self.graph.nodes())):
                try:
                    # Rate limit the request
                    self.rate_limiter.acquire()

                    # Try to fetch the sound
                    self.client.get_sound(int(node_id))

                except Exception as e:
                    # Check if it's a 404 error
                    error_str = str(e).lower()
                    if "404" in error_str or "not found" in error_str:
                        deleted_nodes.append(node_id)
                        self.logger.debug(f"Sample {node_id} no longer exists")

                tracker.update(i + 1)

        # Remove deleted nodes from graph
        for node_id in deleted_nodes:
            self.graph.remove_node(node_id)
            self.processed_ids.discard(node_id)

        if deleted_nodes:
            self.logger.info(f"Removed {len(deleted_nodes)} deleted samples")
            self._save_checkpoint({"cleanup_performed": True})

        return len(deleted_nodes)

    def update_metadata(
        self, mode: str = "merge", sample_ids: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Update metadata for existing nodes.

        Fetches fresh metadata from Freesound API and updates node attributes.
        Supports both merge (add new fields, update existing) and replace
        (completely replace metadata) modes.

        Args:
            mode: Update mode - 'merge' or 'replace' (default: 'merge')
            sample_ids: Optional list of specific sample IDs to update.
                       If None, updates all nodes.

        Returns:
            Dictionary with update statistics:
            - nodes_updated: Number of nodes successfully updated
            - nodes_failed: Number of nodes that failed to update
            - fields_added: Set of new fields added
            - fields_updated: Set of existing fields updated

        Raises:
            ValueError: If mode is not 'merge' or 'replace'
        """
        if mode not in ("merge", "replace"):
            raise ValueError(f"Invalid mode '{mode}'. Must be 'merge' or 'replace'")

        # Determine which nodes to update
        nodes_to_update = sample_ids if sample_ids else list(self.graph.nodes())

        self.logger.info(
            f"Updating metadata for {len(nodes_to_update)} nodes (mode={mode})..."
        )

        stats: dict[str, Union[int, set[str]]] = {
            "nodes_updated": 0,
            "nodes_failed": 0,
            "fields_added": set(),
            "fields_updated": set(),
        }

        now = datetime.now(timezone.utc).isoformat()

        with ProgressTracker(
            total=len(nodes_to_update),
            title=f"Updating metadata ({mode} mode)",
            logger=self.logger,
        ) as tracker:
            for i, node_id in enumerate(nodes_to_update):
                try:
                    # Rate limit the request
                    self.rate_limiter.acquire()

                    # Fetch fresh metadata
                    sound = self.client.get_sound(int(node_id))
                    new_metadata = self._extract_sample_metadata(sound)

                    # Get current attributes
                    current_attrs = dict(self.graph.nodes[node_id])

                    if mode == "merge":
                        # Merge: add new fields, update existing
                        for key, value in new_metadata.items():
                            if key not in current_attrs:
                                cast(set, stats["fields_added"]).add(key)
                            elif current_attrs.get(key) != value:
                                cast(set, stats["fields_updated"]).add(key)

                            self.graph.nodes[node_id][key] = value

                    else:  # mode == 'replace'
                        # Replace: clear and set new attributes
                        self.graph.nodes[node_id].clear()
                        self.graph.nodes[node_id].update(new_metadata)
                        self.graph.nodes[node_id]["type"] = "sample"

                    # Update metadata refresh timestamp
                    self.graph.nodes[node_id]["last_metadata_update_at"] = now

                    stats["nodes_updated"] = cast(int, stats["nodes_updated"]) + 1

                except Exception as e:
                    self.logger.warning(f"Failed to update metadata for {node_id}: {e}")
                    stats["nodes_failed"] = cast(int, stats["nodes_failed"]) + 1

                tracker.update(i + 1)

        # Save checkpoint after metadata update
        self._save_checkpoint({"metadata_updated": True})

        self.logger.info(
            f"Metadata update complete: {stats['nodes_updated']} updated, "
            f"{stats['nodes_failed']} failed, "
            f"{len(cast(set, stats['fields_added']))} new fields, "
            f"{len(cast(set, stats['fields_updated']))} fields updated"
        )

        return stats

    def get_samples_by_existence_check_age(
        self, max_age_days: Optional[int] = None, limit: Optional[int] = None
    ) -> list[str]:
        """
        Get sample IDs sorted by last existence check age.

        Returns samples that haven't been checked recently, with samples
        that have never been checked appearing first.

        Args:
            max_age_days: Optional maximum age in days. If provided, only returns
                         samples older than this threshold.
            limit: Optional maximum number of samples to return.

        Returns:
            List of sample IDs sorted by age (oldest/never-checked first)

        Example:
            # Get 300 oldest samples for partial validation
            samples = loader.get_samples_by_existence_check_age(limit=300)

            # Get all samples not checked in last 30 days
            samples = loader.get_samples_by_existence_check_age(max_age_days=30)
        """
        from datetime import datetime, timedelta, timezone

        # Build list of (sample_id, last_check_timestamp) tuples
        samples_with_age: list[tuple[str, Optional[datetime]]] = []

        for node_id in self.graph.nodes():
            last_check = self.graph.nodes[node_id].get("last_existence_check_at")

            # Samples with no timestamp (never checked) get priority
            if last_check is None:
                samples_with_age.append((str(node_id), None))
            else:
                # Parse ISO timestamp
                try:
                    check_time = datetime.fromisoformat(
                        last_check.replace("Z", "+00:00")
                    )
                    samples_with_age.append((str(node_id), check_time))
                except (ValueError, AttributeError):
                    # Invalid timestamp, treat as never checked
                    samples_with_age.append((str(node_id), None))

        # Sort: None (never checked) first, then oldest timestamps
        samples_with_age.sort(
            key=lambda x: (
                x[1] is not None,
                x[1] or datetime.min.replace(tzinfo=timezone.utc),
            )
        )

        # Filter by max age if specified
        if max_age_days is not None:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            samples_with_age = [
                (sample_id, check_time)
                for sample_id, check_time in samples_with_age
                if check_time is None or check_time < cutoff_time
            ]

        # Extract sample IDs
        sample_ids = [sample_id for sample_id, _ in samples_with_age]

        # Apply limit if specified
        if limit is not None:
            sample_ids = sample_ids[:limit]

        return sample_ids

    def get_samples_by_metadata_age(
        self, max_age_days: Optional[int] = None, limit: Optional[int] = None
    ) -> list[str]:
        """
        Get sample IDs sorted by last metadata update age.

        Returns samples whose metadata hasn't been refreshed recently,
        with samples that have never been updated appearing first.

        Args:
            max_age_days: Optional maximum age in days. If provided, only returns
                         samples older than this threshold.
            limit: Optional maximum number of samples to return.

        Returns:
            List of sample IDs sorted by age (oldest/never-updated first)

        Example:
            # Get 100 oldest samples for metadata refresh
            samples = loader.get_samples_by_metadata_age(limit=100)

            # Get all samples not updated in last 90 days
            samples = loader.get_samples_by_metadata_age(max_age_days=90)
        """
        from datetime import datetime, timedelta, timezone

        # Build list of (sample_id, last_update_timestamp) tuples
        samples_with_age: list[tuple[str, Optional[datetime]]] = []

        for node_id in self.graph.nodes():
            last_update = self.graph.nodes[node_id].get("last_metadata_update_at")

            # Samples with no timestamp (never updated) get priority
            if last_update is None:
                samples_with_age.append((str(node_id), None))
            else:
                # Parse ISO timestamp
                try:
                    update_time = datetime.fromisoformat(
                        last_update.replace("Z", "+00:00")
                    )
                    samples_with_age.append((str(node_id), update_time))
                except (ValueError, AttributeError):
                    # Invalid timestamp, treat as never updated
                    samples_with_age.append((str(node_id), None))

        # Sort: None (never updated) first, then oldest timestamps
        samples_with_age.sort(
            key=lambda x: (
                x[1] is not None,
                x[1] or datetime.min.replace(tzinfo=timezone.utc),
            )
        )

        # Filter by max age if specified
        if max_age_days is not None:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            samples_with_age = [
                (sample_id, update_time)
                for sample_id, update_time in samples_with_age
                if update_time is None or update_time < cutoff_time
            ]

        # Extract sample IDs
        sample_ids = [sample_id for sample_id, _ in samples_with_age]

        # Apply limit if specified
        if limit is not None:
            sample_ids = sample_ids[:limit]

        return sample_ids

    def _search_samples(
        self, query: Optional[str], tags: Optional[list[str]], max_samples: int
    ) -> list[dict[str, Any]]:
        """
        Override parent method to optimize with page_size=150 and complete fields.

        This optimization fetches up to 150 samples with complete metadata per request,
        eliminating the need for follow-up metadata requests.

        Args:
            query: Text search query
            tags: List of tags to filter by
            max_samples: Maximum number of samples to fetch

        Returns:
            List of sample dictionaries with metadata
        """
        # complete fields parameter (29 response fields)
        # Note: original_filename and md5 are filter-only parameters, not response fields
        comprehensive_fields = (
            "id,url,name,tags,description,category,subcategory,geotag,created,"
            "license,type,channels,filesize,bitrate,bitdepth,duration,samplerate,"
            "username,pack,previews,images,num_downloads,avg_rating,num_ratings,"
            "num_comments,comments,similar_sounds,analysis,ac_analysis"
        )

        samples: list[Any] = []
        now = datetime.now(timezone.utc).isoformat()

        try:
            # Build search filter
            search_filter = ""
            if tags:
                tag_filter = " ".join(f"tag:{tag}" for tag in tags)
                search_filter = tag_filter

            # Perform search with rate limiting and retry on 429
            self.rate_limiter.acquire()
            self._increment_request_count()

            # Use text_search with pagination and complete fields
            # Sort by popularity (downloads, ratings) to get most useful samples first
            page_size = min(150, max_samples)  # Freesound max page size is 150

            # Wrap API call with retry logic
            def _do_search():
                return self.client.text_search(
                    query=query or "",
                    filter=search_filter if search_filter else None,
                    page_size=page_size,
                    sort="downloads_desc",  # Sort by most downloaded (most popular)
                    fields=comprehensive_fields,  # Get ALL metadata in one call!
                )

            results = self._retry_with_backoff(_do_search)

            # Extract metadata directly from search results (no follow-up calls needed!)
            for sound in results:
                if len(samples) >= max_samples:
                    break

                # Cache the sound object for future use
                self._sound_cache[sound.id] = sound

                # Extract complete metadata
                sample_data = self._extract_sample_metadata(sound)

                # Set last_metadata_update_at timestamp
                sample_data["last_metadata_update_at"] = now

                samples.append(sample_data)

            # Fetch additional pages if needed
            while len(samples) < max_samples and results.next:
                self.rate_limiter.acquire()
                self._increment_request_count()
                results = self._retry_with_backoff(results.next_page)

                for sound in results:
                    if len(samples) >= max_samples:
                        break

                    # Cache the sound object
                    self._sound_cache[sound.id] = sound

                    # Extract complete metadata
                    sample_data = self._extract_sample_metadata(sound)
                    sample_data["last_metadata_update_at"] = now

                    samples.append(sample_data)

            self.logger.info(
                f"Search returned {len(samples)} samples with complete metadata "
                f"(no follow-up calls needed)"
            )

        except Exception as e:
            raise DataProcessingError(f"Failed to search Freesound API: {e}") from e

        return samples

    def _fetch_sample_metadata(
        self, sample_id: int, return_sound: bool = False
    ) -> Union[dict[str, Any], tuple[dict[str, Any], Any]]:
        """
        Override parent method to track API requests and set metadata timestamp.

        Args:
            sample_id: Freesound sample ID
            return_sound: If True, returns (metadata, sound_object) tuple

        Returns:
            Dictionary with sample metadata, or tuple if return_sound=True
        """
        # Only increment if not in cache (parent checks cache first)
        if sample_id not in self._sound_cache:
            self._increment_request_count()

        # Call parent implementation
        result = super()._fetch_sample_metadata(sample_id, return_sound)

        # Set last_metadata_update_at timestamp
        now = datetime.now(timezone.utc).isoformat()

        if return_sound:
            if isinstance(result, tuple):
                metadata, sound = result
                metadata["last_metadata_update_at"] = now
                return metadata, sound
            else:
                # Shouldn't happen but handle gracefully
                result["last_metadata_update_at"] = now
                return result
        else:
            if isinstance(result, dict):
                result["last_metadata_update_at"] = now
                return result
            else:
                # Shouldn't happen but handle gracefully
                return result

    def _fetch_similar_sounds_for_sample(
        self, sample_id: int
    ) -> list[tuple[int, float]]:
        """
        Override parent method to optimize with page_size=150 and complete fields.

        This optimization fetches up to 150 similar sounds with complete metadata
        in a single API call, eliminating the need for follow-up metadata requests.

        complete fields include ALL 30 available fields:
        id, url, name, tags, description, category, subcategory, geotag, created,
        license, type, channels, filesize, bitrate, bitdepth, duration, samplerate,
        username, pack, previews, images, num_downloads, avg_rating, num_ratings,
        num_comments, comments, similar_sounds, analysis, ac_analysis,
        original_filename, md5

        Args:
            sample_id: Freesound sample ID

        Returns:
            List of (similar_id, score) tuples (excluding self-loops)
        """
        # Increment counter for similar sounds request
        self._increment_request_count()

        # complete fields parameter (ALL 30 available fields)
        # Note: OAuth2-only fields (bookmark, rate) and non-public fields excluded
        # analysis_stats/analysis_frames are inside analysis object
        # Note: original_filename and md5 are filter-only parameters, not response fields
        comprehensive_fields = (
            "id,url,name,tags,description,category,subcategory,geotag,created,"
            "license,type,channels,filesize,bitrate,bitdepth,duration,samplerate,"
            "username,pack,previews,images,num_downloads,avg_rating,num_ratings,"
            "num_comments,comments,similar_sounds,analysis,ac_analysis"
        )

        similar_list = []

        try:
            # Rate limit the request
            self.rate_limiter.acquire()

            # Fetch similar sounds with tuned parameters
            # page_size=150 (API maximum) and complete fields
            similar_sounds = self._retry_with_backoff(
                self.client.get_sound, sample_id
            ).get_similar(
                page_size=150,  # API maximum for list endpoints
                fields=comprehensive_fields,
            )

            # Extract IDs and scores, cache metadata for similar sounds
            now = datetime.now(timezone.utc).isoformat()

            for similar in similar_sounds:
                similar_id = similar.id

                # Skip self-loops
                if similar_id == sample_id:
                    continue

                # Cache the complete sound object (saves future API calls!)
                self._sound_cache[similar_id] = similar

                # Update last_metadata_update_at for cached sample
                # This is stored in the sound object's metadata
                if hasattr(similar, "_metadata"):
                    similar._metadata["last_metadata_update_at"] = now

                score = 1.0
                similar_list.append((similar_id, score))

            if similar_list:
                self.logger.debug(
                    f"Sample {sample_id}: found {len(similar_list)} similar sounds "
                    f"with complete metadata (cached)"
                )

        except Exception as e:
            self.logger.debug(f"Could not fetch similar sounds for {sample_id}: {e}")

        return similar_list

    def close(self) -> None:
        """Close the metadata cache connection to release file locks."""
        if hasattr(self, "metadata_cache") and self.metadata_cache is not None:
            self.metadata_cache.close()
            self.metadata_cache = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (ensures cleanup)."""
        self.close()

    def __del__(self):
        """Destructor (ensures cleanup)."""
        self.close()
