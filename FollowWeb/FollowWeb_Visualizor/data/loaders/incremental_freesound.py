"""
Incremental Freesound data loader with checkpoint support.

This module extends FreesoundLoader with incremental graph building capabilities,
checkpoint management, and time-limited execution for long-running operations.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from ...core.exceptions import DataProcessingError
from ...output.formatters import EmojiFormatter
from ...utils import ProgressTracker
from ..checkpoint import GraphCheckpoint
from .freesound import FreesoundLoader


class IncrementalFreesoundLoader(FreesoundLoader):
    """
    Incremental Freesound loader with checkpoint support.
    
    Extends FreesoundLoader to support:
    - Checkpoint loading and saving for crash recovery
    - Incremental processing (skip already-processed samples)
    - Time-limited execution with graceful stopping
    - Progress tracking and statistics
    - Deleted sample cleanup
    - Flexible metadata updates
    
    The loader maintains a checkpoint file that tracks:
    - Current graph state
    - Set of processed sample IDs
    - Processing metadata (timestamp, progress, etc.)
    
    Attributes:
        checkpoint: GraphCheckpoint instance for state management
        processed_ids: Set of already-processed sample IDs
        graph: Current graph state (loaded from checkpoint or new)
        start_time: Processing start time for time limit tracking
        checkpoint_interval: Number of samples between checkpoint saves
        max_runtime_hours: Maximum runtime before graceful stop
        verify_existing_sounds: Whether to verify existing samples via API
    
    Example:
        loader = IncrementalFreesoundLoader(
            config={
                'api_key': 'your_key',
                'checkpoint_dir': 'checkpoints',
                'checkpoint_interval': 50,
                'max_runtime_hours': 2.0
            }
        )
        graph = loader.load(query='drum', max_samples=1000)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize incremental loader with checkpoint support.
        
        Args:
            config: Configuration dictionary with optional keys:
                   - checkpoint_dir: Directory for checkpoint files (default: 'checkpoints')
                   - checkpoint_interval: Samples between saves (default: 50)
                   - max_runtime_hours: Max runtime before stop (default: None)
                   - verify_existing_sounds: Verify samples via API (default: False)
                   Plus all FreesoundLoader config options
        """
        super().__init__(config)
        
        # Checkpoint configuration
        checkpoint_dir = self.config.get('checkpoint_dir', 'checkpoints')
        self.checkpoint_interval = self.config.get('checkpoint_interval', 50)
        self.max_runtime_hours = self.config.get('max_runtime_hours')
        self.verify_existing_sounds = self.config.get('verify_existing_sounds', False)
        
        # Initialize checkpoint manager
        checkpoint_filename = f"freesound_{int(time.time())}.pkl"
        checkpoint_path = f"{checkpoint_dir}/{checkpoint_filename}"
        self.checkpoint = GraphCheckpoint(checkpoint_path)
        
        # State tracking
        self.processed_ids: Set[str] = set()
        self.graph: nx.DiGraph = nx.DiGraph()
        self.start_time: Optional[float] = None
        
        # Try to load existing checkpoint
        self._load_checkpoint()
        
        self.logger.info(
            f"IncrementalFreesoundLoader initialized: "
            f"checkpoint_interval={self.checkpoint_interval}, "
            f"max_runtime_hours={self.max_runtime_hours}"
        )
    
    def _load_checkpoint(self) -> None:
        """Load checkpoint if it exists."""
        checkpoint_data = self.checkpoint.load()
        
        if checkpoint_data:
            self.graph = checkpoint_data['graph']
            self.processed_ids = checkpoint_data['processed_ids']
            
            metadata = checkpoint_data.get('metadata', {})
            last_update = metadata.get('timestamp', 'unknown')
            
            self.logger.info(
                f"Resumed from checkpoint: {self.graph.number_of_nodes()} nodes, "
                f"{len(self.processed_ids)} processed samples, "
                f"last update: {last_update}"
            )
    
    def _save_checkpoint(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save current state to checkpoint.
        
        Args:
            metadata: Optional metadata to include in checkpoint
        """
        checkpoint_metadata = {
            'timestamp': datetime.now().isoformat(),
            'nodes': self.graph.number_of_nodes(),
            'edges': self.graph.number_of_edges(),
            'processed_count': len(self.processed_ids)
        }
        
        if metadata:
            checkpoint_metadata.update(metadata)
        
        self.checkpoint.save(self.graph, self.processed_ids, checkpoint_metadata)
    
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
        self,
        current: int,
        total: int,
        elapsed_seconds: float
    ) -> Dict[str, Any]:
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
            'percentage': percentage,
            'current': current,
            'total': total,
            'remaining': remaining,
            'elapsed_minutes': elapsed_seconds / 60,
            'eta_minutes': eta_minutes
        }
    
    def fetch_data(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_samples: int = 1000,
        include_similar: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch sample data incrementally with checkpoint support.
        
        Overrides parent method to support incremental processing:
        - Skips already-processed samples
        - Saves checkpoints periodically
        - Respects time limits
        - Tracks progress statistics
        
        Args:
            query: Text search query
            tags: List of tags to filter by
            max_samples: Maximum number of samples to fetch
            include_similar: Fetch similar sounds relationships
        
        Returns:
            Dictionary with 'samples' and 'relationships' keys
        """
        if not query and not tags:
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
        new_samples = [
            s for s in all_samples
            if str(s['id']) not in self.processed_ids
        ]
        
        self.logger.info(
            f"Found {len(all_samples)} total samples, "
            f"{len(new_samples)} new samples to process"
        )
        
        if not new_samples:
            self.logger.info("No new samples to process")
            return {'samples': [], 'relationships': {'similar': {}}}
        
        # Process samples incrementally with progress tracking
        processed_samples = []
        relationships = {'similar': {}}
        
        with ProgressTracker(
            total=len(new_samples),
            title="Processing new samples incrementally",
            logger=self.logger
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
                    
                    self._save_checkpoint({
                        'stopped_reason': 'time_limit',
                        'progress': stats
                    })
                    break
                
                # Add sample to graph
                self._add_sample_to_graph(sample, include_similar)
                processed_samples.append(sample)
                
                # Mark as processed
                self.processed_ids.add(str(sample['id']))
                
                # Periodic checkpoint save
                if (i + 1) % self.checkpoint_interval == 0:
                    elapsed = time.time() - self.start_time
                    stats = self._calculate_progress_stats(i + 1, len(new_samples), elapsed)
                    
                    self.logger.info(
                        f"Progress: {stats['percentage']:.1f}% "
                        f"({stats['current']}/{stats['total']}), "
                        f"ETA: {stats['eta_minutes']:.1f} min"
                    )
                    
                    self._save_checkpoint({'progress': stats})
                
                tracker.update(i + 1)
        
        # Final checkpoint save
        elapsed = time.time() - self.start_time
        final_stats = self._calculate_progress_stats(
            len(processed_samples),
            len(new_samples),
            elapsed
        )
        
        self._save_checkpoint({
            'completed': True,
            'final_stats': final_stats
        })
        
        success_msg = EmojiFormatter.format(
            "success",
            f"Processed {len(processed_samples)} new samples in "
            f"{final_stats['elapsed_minutes']:.1f} minutes"
        )
        self.logger.info(success_msg)
        
        return {
            'samples': processed_samples,
            'relationships': relationships
        }
    
    def _add_sample_to_graph(
        self,
        sample: Dict[str, Any],
        include_similar: bool = True
    ) -> None:
        """
        Add a single sample to the graph with relationships.
        
        Args:
            sample: Sample dictionary with metadata
            include_similar: Whether to fetch and add similar sounds
        """
        sample_id = str(sample['id'])
        
        # Add node if not already in graph
        if sample_id not in self.graph:
            self.graph.add_node(
                sample_id,
                name=sample['name'],
                tags=sample.get('tags', []),
                duration=sample.get('duration', 0),
                user=sample.get('username', ''),
                audio_url=sample.get('audio_url', ''),
                type='sample'
            )
        
        # Fetch and add similar sounds relationships
        if include_similar:
            try:
                similar_list = self._fetch_similar_sounds_for_sample(int(sample['id']))
                
                for target_id, similarity_score in similar_list:
                    target_node = str(target_id)
                    
                    # Only add edge if target exists in graph
                    if target_node in self.graph:
                        self.graph.add_edge(
                            sample_id,
                            target_node,
                            type='similar',
                            weight=similarity_score
                        )
            
            except Exception as e:
                self.logger.warning(
                    f"Failed to add similar sounds for {sample_id}: {e}"
                )
    
    def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
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
            f"{self.graph.number_of_edges():,} edges"
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
            logger=self.logger
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
                    if '404' in error_str or 'not found' in error_str:
                        deleted_nodes.append(node_id)
                        self.logger.debug(f"Sample {node_id} no longer exists")
                
                tracker.update(i + 1)
        
        # Remove deleted nodes from graph
        for node_id in deleted_nodes:
            self.graph.remove_node(node_id)
            self.processed_ids.discard(node_id)
        
        if deleted_nodes:
            self.logger.info(f"Removed {len(deleted_nodes)} deleted samples")
            self._save_checkpoint({'cleanup_performed': True})
        
        return len(deleted_nodes)
    
    def update_metadata(
        self,
        mode: str = 'merge',
        sample_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
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
        if mode not in ('merge', 'replace'):
            raise ValueError(f"Invalid mode '{mode}'. Must be 'merge' or 'replace'")
        
        # Determine which nodes to update
        nodes_to_update = sample_ids if sample_ids else list(self.graph.nodes())
        
        self.logger.info(
            f"Updating metadata for {len(nodes_to_update)} nodes (mode={mode})..."
        )
        
        stats = {
            'nodes_updated': 0,
            'nodes_failed': 0,
            'fields_added': set(),
            'fields_updated': set()
        }
        
        with ProgressTracker(
            total=len(nodes_to_update),
            title=f"Updating metadata ({mode} mode)",
            logger=self.logger
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
                    
                    if mode == 'merge':
                        # Merge: add new fields, update existing
                        for key, value in new_metadata.items():
                            if key not in current_attrs:
                                stats['fields_added'].add(key)
                            elif current_attrs.get(key) != value:
                                stats['fields_updated'].add(key)
                            
                            self.graph.nodes[node_id][key] = value
                    
                    else:  # mode == 'replace'
                        # Replace: clear and set new attributes
                        self.graph.nodes[node_id].clear()
                        self.graph.nodes[node_id].update(new_metadata)
                        self.graph.nodes[node_id]['type'] = 'sample'
                    
                    stats['nodes_updated'] += 1
                
                except Exception as e:
                    self.logger.warning(f"Failed to update metadata for {node_id}: {e}")
                    stats['nodes_failed'] += 1
                
                tracker.update(i + 1)
        
        # Save checkpoint after metadata update
        self._save_checkpoint({'metadata_updated': True})
        
        self.logger.info(
            f"Metadata update complete: {stats['nodes_updated']} updated, "
            f"{stats['nodes_failed']} failed, "
            f"{len(stats['fields_added'])} new fields, "
            f"{len(stats['fields_updated'])} fields updated"
        )
        
        return stats
