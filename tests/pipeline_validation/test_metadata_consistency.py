"""
Tests for metadata consistency validation.

Verifies that metadata in SQLite cache matches graph topology,
all nodes have corresponding metadata, and data is synchronized.
"""

import json
import pickle

import networkx as nx
import pytest

from FollowWeb_Visualizor.data.storage.metadata_cache import MetadataCache


@pytest.fixture
def consistent_checkpoint(tmp_path):
    """Create a checkpoint with consistent graph and metadata."""
    checkpoint_dir = tmp_path / "consistent"
    checkpoint_dir.mkdir()
    
    # Create graph
    graph = nx.DiGraph()
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    graph.add_node(2, name="sample2", audio_url="http://example.com/2.mp3")
    graph.add_node(3, name="sample3", audio_url="http://example.com/3.mp3")
    graph.add_edge(1, 2, weight=0.8)
    graph.add_edge(2, 3, weight=0.6)
    
    # Save graph
    topology_path = checkpoint_dir / "graph_topology.gpickle"
    with open(topology_path, 'wb') as f:
        pickle.dump(graph, f)
    
    # Create matching metadata
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    with MetadataCache(str(metadata_db_path)) as cache:
        cache.set(1, {"name": "sample1", "audio_url": "http://example.com/1.mp3"})
        cache.set(2, {"name": "sample2", "audio_url": "http://example.com/2.mp3"})
        cache.set(3, {"name": "sample3", "audio_url": "http://example.com/3.mp3"})
        cache.flush()
    
    return checkpoint_dir, graph


@pytest.fixture
def inconsistent_checkpoint(tmp_path):
    """Create a checkpoint with inconsistent graph and metadata."""
    checkpoint_dir = tmp_path / "inconsistent"
    checkpoint_dir.mkdir()
    
    # Create graph with 3 nodes
    graph = nx.DiGraph()
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    graph.add_node(2, name="sample2", audio_url="http://example.com/2.mp3")
    graph.add_node(3, name="sample3", audio_url="http://example.com/3.mp3")
    
    # Save graph
    topology_path = checkpoint_dir / "graph_topology.gpickle"
    with open(topology_path, 'wb') as f:
        pickle.dump(graph, f)
    
    # Create metadata with only 2 nodes (missing node 3)
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    with MetadataCache(str(metadata_db_path)) as cache:
        cache.set(1, {"name": "sample1", "audio_url": "http://example.com/1.mp3"})
        cache.set(2, {"name": "sample2", "audio_url": "http://example.com/2.mp3"})
        # Node 3 missing from metadata
        cache.flush()
    
    return checkpoint_dir, graph


@pytest.fixture
def mismatched_attributes_checkpoint(tmp_path):
    """Create a checkpoint where metadata attributes don't match graph."""
    checkpoint_dir = tmp_path / "mismatched"
    checkpoint_dir.mkdir()
    
    # Create graph
    graph = nx.DiGraph()
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    graph.add_node(2, name="sample2", audio_url="http://example.com/2.mp3")
    
    # Save graph
    topology_path = checkpoint_dir / "graph_topology.gpickle"
    with open(topology_path, 'wb') as f:
        pickle.dump(graph, f)
    
    # Create metadata with different values
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    with MetadataCache(str(metadata_db_path)) as cache:
        cache.set(1, {"name": "different_name", "audio_url": "http://example.com/1.mp3"})
        cache.set(2, {"name": "sample2", "audio_url": "http://different.com/2.mp3"})
        cache.flush()
    
    return checkpoint_dir, graph


class TestMetadataConsistency:
    """Test suite for metadata consistency validation."""
    
    def test_all_graph_nodes_have_metadata(self, consistent_checkpoint):
        """Test that all nodes in graph have corresponding metadata."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        with MetadataCache(str(metadata_db_path)) as cache:
            for node_id in graph.nodes():
                metadata = cache.get(node_id)
                assert metadata is not None, f"Node {node_id} missing metadata"
    
    def test_metadata_count_matches_node_count(self, consistent_checkpoint):
        """Test that metadata count matches graph node count."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        with MetadataCache(str(metadata_db_path)) as cache:
            metadata_count = cache.get_count()
            node_count = graph.number_of_nodes()
            
            assert metadata_count == node_count, \
                f"Metadata count ({metadata_count}) != node count ({node_count})"
    
    def test_metadata_attributes_match_graph_attributes(self, consistent_checkpoint):
        """Test that metadata attributes match graph node attributes."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        with MetadataCache(str(metadata_db_path)) as cache:
            for node_id, graph_attrs in graph.nodes(data=True):
                metadata = cache.get(node_id)
                
                # Check that key attributes match
                assert metadata["name"] == graph_attrs["name"], \
                    f"Name mismatch for node {node_id}"
                assert metadata["audio_url"] == graph_attrs["audio_url"], \
                    f"Audio URL mismatch for node {node_id}"
    
    def test_inconsistent_checkpoint_detected(self, inconsistent_checkpoint):
        """Test that inconsistency between graph and metadata is detected."""
        checkpoint_dir, graph = inconsistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        missing_nodes = []
        
        with MetadataCache(str(metadata_db_path)) as cache:
            for node_id in graph.nodes():
                if not cache.exists(node_id):
                    missing_nodes.append(node_id)
        
        # Should detect node 3 is missing from metadata
        assert len(missing_nodes) > 0, "Inconsistency not detected"
        assert 3 in missing_nodes
    
    def test_mismatched_attributes_detected(self, mismatched_attributes_checkpoint):
        """Test that mismatched attributes between graph and metadata are detected."""
        checkpoint_dir, graph = mismatched_attributes_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        mismatches = []
        
        with MetadataCache(str(metadata_db_path)) as cache:
            for node_id, graph_attrs in graph.nodes(data=True):
                metadata = cache.get(node_id)
                
                if metadata["name"] != graph_attrs["name"]:
                    mismatches.append((node_id, "name"))
                if metadata["audio_url"] != graph_attrs["audio_url"]:
                    mismatches.append((node_id, "audio_url"))
        
        # Should detect 2 mismatches
        assert len(mismatches) == 2
    
    def test_metadata_json_is_valid(self, consistent_checkpoint):
        """Test that metadata stored as JSON is valid."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        import sqlite3
        
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT sample_id, data FROM metadata")
        
        for sample_id, data_json in cursor.fetchall():
            # Should be able to parse JSON
            try:
                data = json.loads(data_json)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON for sample {sample_id}")
        
        conn.close()
    
    def test_metadata_has_timestamps(self, consistent_checkpoint):
        """Test that metadata entries have timestamps."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        import sqlite3
        
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT sample_id, last_updated FROM metadata")
        
        for sample_id, last_updated in cursor.fetchall():
            assert last_updated is not None, \
                f"Sample {sample_id} missing timestamp"
            assert len(last_updated) > 0
        
        conn.close()
    
    def test_no_orphaned_metadata(self, consistent_checkpoint):
        """Test that there's no metadata for non-existent nodes."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        graph_node_ids = set(graph.nodes())
        
        with MetadataCache(str(metadata_db_path)) as cache:
            metadata_node_ids = set(cache.get_all_sample_ids())
        
        # All metadata IDs should exist in graph
        orphaned = metadata_node_ids - graph_node_ids
        
        assert len(orphaned) == 0, \
            f"Found {len(orphaned)} orphaned metadata entries"
    
    def test_metadata_cache_integrity(self, consistent_checkpoint):
        """Test that metadata cache database has integrity."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        import sqlite3
        
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        assert result[0] == "ok", "Database integrity check failed"
        
        conn.close()
    
    def test_sample_ids_are_unique_in_metadata(self, consistent_checkpoint):
        """Test that sample IDs are unique in metadata cache."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        import sqlite3
        
        conn = sqlite3.connect(str(metadata_db_path))
        cursor = conn.cursor()
        
        # Check for duplicate sample IDs
        cursor.execute("""
            SELECT sample_id, COUNT(*) as count
            FROM metadata
            GROUP BY sample_id
            HAVING count > 1
        """)
        
        duplicates = cursor.fetchall()
        
        assert len(duplicates) == 0, \
            f"Found {len(duplicates)} duplicate sample IDs"
        
        conn.close()
    
    def test_metadata_required_fields_present(self, consistent_checkpoint):
        """Test that metadata has all required fields."""
        checkpoint_dir, graph = consistent_checkpoint
        metadata_db_path = checkpoint_dir / "metadata_cache.db"
        
        required_fields = ["name", "audio_url"]
        
        with MetadataCache(str(metadata_db_path)) as cache:
            for node_id in graph.nodes():
                metadata = cache.get(node_id)
                
                for field in required_fields:
                    assert field in metadata, \
                        f"Node {node_id} metadata missing field: {field}"
    
    def test_checkpoint_metadata_json_consistency(self, consistent_checkpoint):
        """Test that checkpoint_metadata.json is consistent with actual data."""
        checkpoint_dir, graph = consistent_checkpoint
        
        # Create checkpoint_metadata.json
        from datetime import datetime
        
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        }
        
        metadata_path = checkpoint_dir / "checkpoint_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        # Load and verify
        with open(metadata_path) as f:
            loaded_metadata = json.load(f)
        
        assert loaded_metadata["nodes"] == graph.number_of_nodes()
        assert loaded_metadata["edges"] == graph.number_of_edges()
