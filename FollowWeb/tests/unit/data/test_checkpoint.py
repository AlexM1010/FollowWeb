"""
Unit tests for GraphCheckpoint.

Tests checkpoint save/load with joblib, checkpoint management operations,
and error handling with mocked joblib operations.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint


@pytest.fixture
def temp_checkpoint_path(tmp_path):
    """Create a temporary checkpoint path."""
    return str(tmp_path / "test_checkpoint.pkl")


@pytest.fixture
def sample_graph():
    """Create a sample graph for testing."""
    graph = nx.DiGraph()
    graph.add_node('1', name='node1')
    graph.add_node('2', name='node2')
    graph.add_edge('1', '2', weight=1.0)
    return graph


@pytest.fixture
def sample_processed_ids():
    """Create sample processed IDs set."""
    return {'1', '2', '3'}


class TestGraphCheckpointInitialization:
    """Test GraphCheckpoint initialization."""

    def test_init_with_path(self, temp_checkpoint_path):
        """Test initialization with checkpoint path."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        assert checkpoint.checkpoint_path == Path(temp_checkpoint_path)
        assert hasattr(checkpoint, 'logger')

    def test_init_creates_path_object(self):
        """Test initialization creates Path object."""
        checkpoint = GraphCheckpoint('checkpoints/test.pkl')
        
        assert isinstance(checkpoint.checkpoint_path, Path)
        assert checkpoint.checkpoint_path.name == 'test.pkl'


class TestGraphCheckpointSave:
    """Test checkpoint save functionality."""

    def test_save_creates_checkpoint(self, temp_checkpoint_path, sample_graph, 
                                     sample_processed_ids):
        """Test saving checkpoint creates file."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        checkpoint.save(sample_graph, sample_processed_ids)
        
        assert Path(temp_checkpoint_path).exists()

    def test_save_with_metadata(self, temp_checkpoint_path, sample_graph, 
                                sample_processed_ids):
        """Test saving checkpoint with metadata."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        metadata = {'timestamp': '2024-01-01', 'version': '1.0'}
        
        checkpoint.save(sample_graph, sample_processed_ids, metadata)
        
        assert Path(temp_checkpoint_path).exists()

    def test_save_creates_parent_directory(self, tmp_path, sample_graph, 
                                           sample_processed_ids):
        """Test saving checkpoint creates parent directory if needed."""
        nested_path = tmp_path / "nested" / "dir" / "checkpoint.pkl"
        checkpoint = GraphCheckpoint(str(nested_path))
        
        checkpoint.save(sample_graph, sample_processed_ids)
        
        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_save_overwrites_existing(self, temp_checkpoint_path, sample_graph, 
                                      sample_processed_ids):
        """Test saving checkpoint overwrites existing file."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        # Save first checkpoint
        checkpoint.save(sample_graph, sample_processed_ids)
        first_mtime = Path(temp_checkpoint_path).stat().st_mtime
        
        # Save second checkpoint
        import time
        time.sleep(0.01)  # Ensure different timestamp
        new_graph = nx.DiGraph()
        new_graph.add_node('99')
        checkpoint.save(new_graph, {'99'})
        
        second_mtime = Path(temp_checkpoint_path).stat().st_mtime
        assert second_mtime > first_mtime

    @patch('FollowWeb_Visualizor.data.checkpoint.joblib.dump')
    def test_save_handles_io_error(self, mock_dump, temp_checkpoint_path, 
                                   sample_graph, sample_processed_ids):
        """Test save handles IO errors gracefully."""
        # Mock joblib.dump to raise an error
        mock_dump.side_effect = IOError("Disk full")
        
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        with pytest.raises(IOError, match="Checkpoint save failed"):
            checkpoint.save(sample_graph, sample_processed_ids)

    @patch('FollowWeb_Visualizor.data.checkpoint.joblib.dump')
    def test_save_uses_compression(self, mock_dump, temp_checkpoint_path, 
                                   sample_graph, sample_processed_ids):
        """Test save uses joblib compression."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        checkpoint.save(sample_graph, sample_processed_ids)
        
        # Verify joblib.dump was called with compress=3
        mock_dump.assert_called_once()
        call_args = mock_dump.call_args
        assert call_args[1]['compress'] == 3


class TestGraphCheckpointLoad:
    """Test checkpoint load functionality."""

    def test_load_nonexistent_returns_none(self, temp_checkpoint_path):
        """Test loading nonexistent checkpoint returns None."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        data = checkpoint.load()
        
        assert data is None

    def test_load_returns_saved_data(self, temp_checkpoint_path, sample_graph, 
                                     sample_processed_ids):
        """Test loading checkpoint returns saved data."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        metadata = {'test': 'value'}
        
        checkpoint.save(sample_graph, sample_processed_ids, metadata)
        data = checkpoint.load()
        
        assert data is not None
        assert 'graph' in data
        assert 'processed_ids' in data
        assert 'metadata' in data
        assert data['processed_ids'] == sample_processed_ids
        assert data['metadata']['test'] == 'value'

    def test_load_graph_structure(self, temp_checkpoint_path, sample_graph, 
                                  sample_processed_ids):
        """Test loaded graph maintains structure."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        checkpoint.save(sample_graph, sample_processed_ids)
        data = checkpoint.load()
        
        loaded_graph = data['graph']
        assert loaded_graph.number_of_nodes() == sample_graph.number_of_nodes()
        assert loaded_graph.number_of_edges() == sample_graph.number_of_edges()
        assert loaded_graph.has_node('1')
        assert loaded_graph.has_edge('1', '2')
        assert loaded_graph.nodes['1']['name'] == 'node1'

    def test_load_empty_metadata(self, temp_checkpoint_path, sample_graph, 
                                 sample_processed_ids):
        """Test loading checkpoint with no metadata."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        checkpoint.save(sample_graph, sample_processed_ids)
        data = checkpoint.load()
        
        assert data['metadata'] == {}

    @patch('FollowWeb_Visualizor.data.checkpoint.joblib.load')
    def test_load_handles_corrupted_file(self, mock_load, temp_checkpoint_path):
        """Test load handles corrupted checkpoint file."""
        # Create a file to make exists() return True
        Path(temp_checkpoint_path).touch()
        
        mock_load.side_effect = Exception("Corrupted file")
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        data = checkpoint.load()
        
        assert data is None

    @patch('FollowWeb_Visualizor.data.checkpoint.joblib.load')
    def test_load_handles_missing_keys(self, mock_load, temp_checkpoint_path):
        """Test load handles checkpoint with missing keys."""
        Path(temp_checkpoint_path).touch()
        
        # Return incomplete data
        mock_load.return_value = {'graph': nx.DiGraph()}
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        data = checkpoint.load()
        
        assert data['processed_ids'] == set()
        assert data['metadata'] == {}


class TestGraphCheckpointClear:
    """Test checkpoint clear functionality."""

    def test_clear_removes_file(self, temp_checkpoint_path, sample_graph, 
                                sample_processed_ids):
        """Test clear removes checkpoint file."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        checkpoint.save(sample_graph, sample_processed_ids)
        assert Path(temp_checkpoint_path).exists()
        
        checkpoint.clear()
        assert not Path(temp_checkpoint_path).exists()

    def test_clear_nonexistent_file(self, temp_checkpoint_path):
        """Test clear handles nonexistent file gracefully."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        # Should not raise error
        checkpoint.clear()
        assert not Path(temp_checkpoint_path).exists()

    def test_clear_handles_permission_error(self, temp_checkpoint_path, 
                                           sample_graph, sample_processed_ids):
        """Test clear handles permission errors gracefully."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        checkpoint.save(sample_graph, sample_processed_ids)
        
        with patch.object(Path, 'unlink', side_effect=PermissionError("Access denied")):
            # Should not raise, just log warning
            checkpoint.clear()


class TestGraphCheckpointExists:
    """Test checkpoint exists check."""

    def test_exists_returns_false_for_nonexistent(self, temp_checkpoint_path):
        """Test exists returns False for nonexistent file."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        assert not checkpoint.exists()

    def test_exists_returns_true_for_existing(self, temp_checkpoint_path, 
                                              sample_graph, sample_processed_ids):
        """Test exists returns True for existing file."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        checkpoint.save(sample_graph, sample_processed_ids)
        
        assert checkpoint.exists()

    def test_exists_after_clear(self, temp_checkpoint_path, sample_graph, 
                                sample_processed_ids):
        """Test exists returns False after clear."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        checkpoint.save(sample_graph, sample_processed_ids)
        assert checkpoint.exists()
        
        checkpoint.clear()
        assert not checkpoint.exists()


class TestGraphCheckpointIntegration:
    """Test complete checkpoint workflows."""

    def test_save_load_cycle(self, temp_checkpoint_path):
        """Test complete save-load cycle."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        # Create test data
        graph = nx.DiGraph()
        graph.add_nodes_from([('a', {'value': 1}), ('b', {'value': 2})])
        graph.add_edge('a', 'b', weight=0.5)
        processed_ids = {'a', 'b', 'c'}
        metadata = {'timestamp': '2024-01-01', 'count': 3}
        
        # Save
        checkpoint.save(graph, processed_ids, metadata)
        
        # Load
        data = checkpoint.load()
        
        # Verify
        assert data['graph'].number_of_nodes() == 2
        assert data['graph'].nodes['a']['value'] == 1
        assert data['graph'].has_edge('a', 'b')
        assert data['processed_ids'] == processed_ids
        assert data['metadata']['timestamp'] == '2024-01-01'

    def test_multiple_checkpoints_independent(self, tmp_path):
        """Test multiple checkpoints are independent."""
        checkpoint1 = GraphCheckpoint(str(tmp_path / "checkpoint1.pkl"))
        checkpoint2 = GraphCheckpoint(str(tmp_path / "checkpoint2.pkl"))
        
        graph1 = nx.DiGraph()
        graph1.add_node('1')
        
        graph2 = nx.DiGraph()
        graph2.add_node('2')
        
        checkpoint1.save(graph1, {'1'})
        checkpoint2.save(graph2, {'2'})
        
        data1 = checkpoint1.load()
        data2 = checkpoint2.load()
        
        assert data1['graph'].has_node('1')
        assert not data1['graph'].has_node('2')
        assert data2['graph'].has_node('2')
        assert not data2['graph'].has_node('1')

    def test_incremental_updates(self, temp_checkpoint_path):
        """Test incremental checkpoint updates."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        # First save
        graph = nx.DiGraph()
        graph.add_node('1')
        checkpoint.save(graph, {'1'})
        
        # Load and update
        data = checkpoint.load()
        graph = data['graph']
        processed_ids = data['processed_ids']
        
        graph.add_node('2')
        processed_ids.add('2')
        
        # Save updated state
        checkpoint.save(graph, processed_ids)
        
        # Verify
        final_data = checkpoint.load()
        assert final_data['graph'].number_of_nodes() == 2
        assert final_data['processed_ids'] == {'1', '2'}

    def test_large_graph_checkpoint(self, temp_checkpoint_path):
        """Test checkpoint with larger graph."""
        checkpoint = GraphCheckpoint(temp_checkpoint_path)
        
        # Create larger graph
        graph = nx.DiGraph()
        for i in range(100):
            graph.add_node(str(i), value=i)
            if i > 0:
                graph.add_edge(str(i-1), str(i), weight=i*0.1)
        
        processed_ids = {str(i) for i in range(100)}
        
        checkpoint.save(graph, processed_ids)
        data = checkpoint.load()
        
        assert data['graph'].number_of_nodes() == 100
        assert data['graph'].number_of_edges() == 99
        assert len(data['processed_ids']) == 100
