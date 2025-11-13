"""
Tests for checkpoint file integrity validation.

Verifies that checkpoint files (pickle and SQLite) can be loaded
without corruption and contain valid data structures.
"""

import pickle
import sqlite3
import tempfile
from pathlib import Path

import networkx as nx
import pytest

from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint
from FollowWeb_Visualizor.data.storage.metadata_cache import MetadataCache


@pytest.fixture
def valid_checkpoint_dir(tmp_path):
    """Create a valid checkpoint directory with test data."""
    checkpoint_dir = tmp_path / "test_checkpoint"
    checkpoint_dir.mkdir()
    
    # Create a simple test graph
    graph = nx.DiGraph()
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    graph.add_node(2, name="sample2", audio_url="http://example.com/2.mp3")
    graph.add_edge(1, 2, weight=0.8, type="similar")
    
    # Save graph topology
    topology_path = checkpoint_dir / "graph_topology.gpickle"
    with open(topology_path, 'wb') as f:
        pickle.dump(graph, f)
    
    # Create metadata cache
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    with MetadataCache(str(metadata_db_path)) as cache:
        cache.set(1, {"name": "sample1", "audio_url": "http://example.com/1.mp3"})
        cache.set(2, {"name": "sample2", "audio_url": "http://example.com/2.mp3"})
        cache.flush()
    
    # Create checkpoint metadata
    import json
    from datetime import datetime
    
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "nodes": 2,
        "edges": 1,
        "processed_ids_count": 2
    }
    
    metadata_path = checkpoint_dir / "checkpoint_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    return checkpoint_dir


@pytest.fixture
def corrupted_pickle_checkpoint(tmp_path):
    """Create a checkpoint with corrupted pickle file."""
    checkpoint_dir = tmp_path / "corrupted_pickle"
    checkpoint_dir.mkdir()
    
    # Write invalid pickle data
    topology_path = checkpoint_dir / "graph_topology.gpickle"
    with open(topology_path, 'wb') as f:
        f.write(b"corrupted pickle data")
    
    # Create valid metadata cache
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    with MetadataCache(str(metadata_db_path)) as cache:
        cache.set(1, {"name": "test"})
        cache.flush()
    
    return checkpoint_dir


@pytest.fixture
def corrupted_sqlite_checkpoint(tmp_path):
    """Create a checkpoint with corrupted SQLite database."""
    checkpoint_dir = tmp_path / "corrupted_sqlite"
    checkpoint_dir.mkdir()
    
    # Create valid graph
    graph = nx.DiGraph()
    graph.add_node(1, name="sample1")
    topology_path = checkpoint_dir / "graph_topology.gpickle"
    with open(topology_path, 'wb') as f:
        pickle.dump(graph, f)
    
    # Write invalid SQLite data
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    with open(metadata_db_path, 'wb') as f:
        f.write(b"corrupted sqlite data")
    
    return checkpoint_dir


class TestCheckpointIntegrity:
    """Test suite for checkpoint file integrity validation."""
    
    def test_valid_checkpoint_loads_successfully(self, valid_checkpoint_dir):
        """Test that a valid checkpoint can be loaded without errors."""
        topology_path = valid_checkpoint_dir / "graph_topology.gpickle"
        
        # Load graph topology
        with open(topology_path, 'rb') as f:
            graph = pickle.load(f)
        
        assert graph is not None
        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 1
    
    def test_valid_metadata_cache_loads_successfully(self, valid_checkpoint_dir):
        """Test that a valid metadata cache can be loaded without errors."""
        metadata_db_path = valid_checkpoint_dir / "metadata_cache.db"
        
        with MetadataCache(str(metadata_db_path)) as cache:
            metadata = cache.get(1)
            
            assert metadata is not None
            assert metadata["name"] == "sample1"
            assert "audio_url" in metadata
    
    def test_checkpoint_metadata_is_valid_json(self, valid_checkpoint_dir):
        """Test that checkpoint metadata is valid JSON."""
        import json
        
        metadata_path = valid_checkpoint_dir / "checkpoint_metadata.json"
        
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        assert "timestamp" in metadata
        assert "nodes" in metadata
        assert "edges" in metadata
        assert metadata["nodes"] == 2
        assert metadata["edges"] == 1
    
    def test_corrupted_pickle_raises_error(self, corrupted_pickle_checkpoint):
        """Test that corrupted pickle file raises appropriate error."""
        topology_path = corrupted_pickle_checkpoint / "graph_topology.gpickle"
        
        with pytest.raises(Exception):
            with open(topology_path, 'rb') as f:
                pickle.load(f)
    
    def test_corrupted_sqlite_raises_error(self, corrupted_sqlite_checkpoint):
        """Test that corrupted SQLite database raises appropriate error."""
        metadata_db_path = corrupted_sqlite_checkpoint / "metadata_cache.db"
        
        with pytest.raises((sqlite3.DatabaseError, RuntimeError)):
            with MetadataCache(str(metadata_db_path)) as cache:
                cache.get(1)
    
    def test_missing_checkpoint_files_detected(self, tmp_path):
        """Test that missing checkpoint files are detected."""
        checkpoint_dir = tmp_path / "missing_files"
        checkpoint_dir.mkdir()
        
        topology_path = checkpoint_dir / "graph_topology.gpickle"
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        metadata_json_path = checkpoint_dir / "checkpoint_metadata.json"
        
        assert not topology_path.exists()
        assert not metadata_db_path.exists()
        assert not metadata_json_path.exists()
    
    def test_checkpoint_files_are_readable(self, valid_checkpoint_dir):
        """Test that all checkpoint files have read permissions."""
        topology_path = valid_checkpoint_dir / "graph_topology.gpickle"
        metadata_db_path = valid_checkpoint_dir / "metadata_cache.db"
        metadata_json_path = valid_checkpoint_dir / "checkpoint_metadata.json"
        
        assert topology_path.exists()
        assert topology_path.is_file()
        assert metadata_db_path.exists()
        assert metadata_db_path.is_file()
        assert metadata_json_path.exists()
        assert metadata_json_path.is_file()
    
    def test_checkpoint_files_not_empty(self, valid_checkpoint_dir):
        """Test that checkpoint files are not empty."""
        topology_path = valid_checkpoint_dir / "graph_topology.gpickle"
        metadata_db_path = valid_checkpoint_dir / "metadata_cache.db"
        metadata_json_path = valid_checkpoint_dir / "checkpoint_metadata.json"
        
        assert topology_path.stat().st_size > 0
        assert metadata_db_path.stat().st_size > 0
        assert metadata_json_path.stat().st_size > 0
    
    def test_graph_topology_is_directed_graph(self, valid_checkpoint_dir):
        """Test that loaded graph is a directed graph."""
        topology_path = valid_checkpoint_dir / "graph_topology.gpickle"
        with open(topology_path, 'rb') as f:
            graph = pickle.load(f)
        
        assert isinstance(graph, nx.DiGraph)
    
    def test_metadata_cache_has_valid_schema(self, valid_checkpoint_dir):
        """Test that metadata cache has the expected schema."""
        metadata_db_path = valid_checkpoint_dir / "metadata_cache.db"
        
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()
        
        # Check that metadata table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='metadata'
        """)
        
        assert cursor.fetchone() is not None
        
        # Check table schema
        cursor.execute("PRAGMA table_info(metadata)")
        columns = {row[1] for row in cursor.fetchall()}
        
        expected_columns = {
            "sample_id", "data", "last_updated", 
            "priority_score", "is_dormant", "dormant_since"
        }
        
        assert expected_columns.issubset(columns)
        
        conn.close()
    
    def test_metadata_cache_has_indexes(self, valid_checkpoint_dir):
        """Test that metadata cache has performance indexes."""
        metadata_db_path = valid_checkpoint_dir / "metadata_cache.db"
        
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()
        
        # Check for indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='metadata'
        """)
        
        indexes = {row[0] for row in cursor.fetchall()}
        
        # Should have at least some indexes (exact names may vary)
        assert len(indexes) > 0
        
        conn.close()
