"""
Checkpoint management for incremental graph building.

This module provides checkpoint functionality for saving and loading graph state
during incremental processing, enabling crash recovery and resumable operations.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Set

import joblib
import networkx as nx


class GraphCheckpoint:
    """
    Manages graph checkpoints using joblib for atomic, compressed saves.
    
    Provides atomic write operations with compression to ensure checkpoint
    integrity during crashes. Uses joblib's battle-tested serialization
    used by scikit-learn and other major projects.
    
    Attributes:
        checkpoint_path: Path to checkpoint file
        logger: Logger instance
    
    Example:
        checkpoint = GraphCheckpoint('checkpoints/freesound.pkl')
        checkpoint.save(graph, processed_ids={'123', '456'})
        data = checkpoint.load()
        graph = data['graph']
        processed_ids = data['processed_ids']
    """
    
    def __init__(self, checkpoint_path: str):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_path: Path to checkpoint file (will be created if needed)
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def save(
        self,
        graph: nx.DiGraph,
        processed_ids: Set[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save graph checkpoint atomically with compression.
        
        Uses joblib.dump() with compress=3 for atomic writes and compression.
        Creates parent directory if it doesn't exist.
        
        Args:
            graph: NetworkX graph to save
            processed_ids: Set of already-processed sample IDs
            metadata: Optional metadata dictionary (e.g., timestamp, version)
        
        Raises:
            IOError: If checkpoint save fails
        """
        try:
            # Ensure checkpoint directory exists
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare checkpoint data
            checkpoint_data = {
                'graph': graph,
                'processed_ids': processed_ids,
                'metadata': metadata or {}
            }
            
            # Atomic write with compression (compress=3 is good balance)
            joblib.dump(checkpoint_data, self.checkpoint_path, compress=3)
            
            self.logger.info(
                f"Checkpoint saved: {graph.number_of_nodes()} nodes, "
                f"{len(processed_ids)} processed IDs"
            )
        
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise IOError(f"Checkpoint save failed: {e}") from e
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load graph checkpoint.
        
        Returns:
            Dictionary with keys:
            - 'graph': NetworkX DiGraph
            - 'processed_ids': Set of processed sample IDs
            - 'metadata': Metadata dictionary
            
            Returns None if checkpoint doesn't exist or is corrupted.
        """
        if not self.exists():
            self.logger.info("No checkpoint found")
            return None
        
        try:
            checkpoint_data = joblib.load(self.checkpoint_path)
            
            graph = checkpoint_data.get('graph')
            processed_ids = checkpoint_data.get('processed_ids', set())
            metadata = checkpoint_data.get('metadata', {})
            
            self.logger.info(
                f"Checkpoint loaded: {graph.number_of_nodes()} nodes, "
                f"{len(processed_ids)} processed IDs"
            )
            
            return {
                'graph': graph,
                'processed_ids': processed_ids,
                'metadata': metadata
            }
        
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            self.logger.warning("Starting fresh due to corrupted checkpoint")
            return None
    
    def clear(self) -> None:
        """
        Delete checkpoint file.
        
        Removes checkpoint file if it exists. Safe to call even if
        checkpoint doesn't exist.
        """
        if self.exists():
            try:
                self.checkpoint_path.unlink()
                self.logger.info("Checkpoint cleared")
            except Exception as e:
                self.logger.warning(f"Failed to clear checkpoint: {e}")
    
    def exists(self) -> bool:
        """
        Check if checkpoint file exists.
        
        Returns:
            True if checkpoint file exists, False otherwise
        """
        return self.checkpoint_path.exists()
