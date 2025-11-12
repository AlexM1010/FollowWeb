"""
Unit tests for IncrementalFreesoundLoader.

Tests incremental loading with checkpoint support, time limits, deleted sample
cleanup, and metadata updates with mocked checkpoint and API operations.
"""

import time
from unittest.mock import Mock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.exceptions import DataProcessingError
from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
    IncrementalFreesoundLoader,
)


def create_mock_sound(sound_id, name="test_sound.wav", tags=None, duration=1.0, username="test_user", previews=None):
    """Helper to create a properly mocked Freesound sound object."""
    if tags is None:
        tags = []
    if previews is None:
        previews = {}
    
    sound = Mock()
    sound.id = sound_id
    sound.name = name
    sound.tags = tags
    sound.duration = duration
    sound.username = username
    sound.previews = previews
    
    # Mock as_dict() to return a proper dictionary (not a Mock)
    sound.as_dict = Mock(return_value={
        'id': sound_id,
        'name': name,
        'tags': tags,
        'duration': duration,
        'username': username,
        'previews': previews
    })
    return sound


@pytest.fixture
def mock_freesound_client():
    """Create a mock Freesound client."""
    with patch('FollowWeb_Visualizor.data.loaders.freesound.freesound') as mock_fs:
        client = Mock()
        mock_fs.FreesoundClient.return_value = client
        yield client


@pytest.fixture
def mock_checkpoint():
    """Create a mock GraphCheckpoint."""
    with patch('FollowWeb_Visualizor.data.loaders.incremental_freesound.GraphCheckpoint') as mock_cp:
        checkpoint_instance = Mock()
        checkpoint_instance.load.return_value = None
        checkpoint_instance.exists.return_value = False
        mock_cp.return_value = checkpoint_instance
        yield checkpoint_instance


@pytest.fixture
def loader_with_mocks(mock_freesound_client, mock_checkpoint):
    """Create IncrementalFreesoundLoader with mocked dependencies."""
    with patch.dict('os.environ', {'FREESOUND_API_KEY': 'test_key'}):
        loader = IncrementalFreesoundLoader()
        return loader


class TestIncrementalFreesoundLoaderInitialization:
    """Test IncrementalFreesoundLoader initialization."""

    def test_init_with_default_config(self, mock_freesound_client, mock_checkpoint):
        """Test initialization with default configuration."""
        with patch.dict('os.environ', {'FREESOUND_API_KEY': 'test_key'}):
            loader = IncrementalFreesoundLoader()
            
            assert loader.checkpoint_interval == 50
            assert loader.max_runtime_hours is None
            assert loader.verify_existing_sounds is False
            assert isinstance(loader.processed_ids, set)

    def test_init_with_custom_config(self, mock_freesound_client, mock_checkpoint):
        """Test initialization with custom configuration."""
        config = {
            'api_key': 'test_key',
            'checkpoint_dir': 'custom_checkpoints',
            'checkpoint_interval': 25,
            'max_runtime_hours': 1.5,
            'verify_existing_sounds': True
        }
        
        loader = IncrementalFreesoundLoader(config=config)
        
        assert loader.checkpoint_interval == 25
        assert loader.max_runtime_hours == 1.5
        assert loader.verify_existing_sounds is True

    def test_init_loads_existing_checkpoint(self, mock_freesound_client, mock_checkpoint):
        """Test initialization loads existing checkpoint."""
        # Mock existing checkpoint data
        existing_graph = nx.DiGraph()
        existing_graph.add_node('1')
        
        def mock_load_checkpoint(self):
            self.graph = existing_graph
            self.processed_ids = {'1', '2'}
        
        with patch.dict('os.environ', {'FREESOUND_API_KEY': 'test_key'}):
            with patch.object(IncrementalFreesoundLoader, '_load_checkpoint', mock_load_checkpoint):
                loader = IncrementalFreesoundLoader()
                
                assert loader.graph.number_of_nodes() == 1
                assert loader.processed_ids == {'1', '2'}


class TestIncrementalFreesoundLoaderCheckpoint:
    """Test checkpoint loading and saving."""

    def test_load_checkpoint_restores_state(self, mock_freesound_client, mock_checkpoint):
        """Test loading checkpoint restores graph and processed IDs."""
        graph = nx.DiGraph()
        graph.add_nodes_from(['a', 'b', 'c'])
        
        def mock_load_checkpoint(self):
            self.graph = graph
            self.processed_ids = {'a', 'b', 'c'}
        
        with patch.dict('os.environ', {'FREESOUND_API_KEY': 'test_key'}):
            with patch.object(IncrementalFreesoundLoader, '_load_checkpoint', mock_load_checkpoint):
                loader = IncrementalFreesoundLoader()
                
                assert loader.graph.number_of_nodes() == 3
                assert len(loader.processed_ids) == 3

    def test_save_checkpoint_called_periodically(self, loader_with_mocks, mock_checkpoint):
        """Test checkpoint is saved at configured intervals."""
        loader = loader_with_mocks
        loader.checkpoint_interval = 2
        
        # Reset the loader state to start fresh
        loader.graph = nx.DiGraph()
        loader.processed_ids = set()
        
        # Mock search results
        sounds = [
            create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
            for i in range(5)
        ]
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter(sounds))
        mock_results.more = False
        loader.client.text_search.return_value = mock_results
        
        # Mock get_sound to return the sounds
        def get_sound_side_effect(sound_id):
            return sounds[sound_id]
        loader.client.get_sound.side_effect = get_sound_side_effect
        
        # Mock the checkpoint save method on the loader's checkpoint instance
        loader.checkpoint.save = Mock()
        
        loader.fetch_data(query='test', max_samples=5)
        
        # Should save at intervals: after 2, 4, and final
        assert loader.checkpoint.save.call_count >= 2

    def test_no_checkpoint_load_starts_fresh(self, mock_freesound_client, mock_checkpoint):
        """Test starting fresh when no checkpoint exists."""
        mock_checkpoint.load.return_value = None
        
        with patch.dict('os.environ', {'FREESOUND_API_KEY': 'test_key'}):
            with patch.object(IncrementalFreesoundLoader, '_load_checkpoint'):
                loader = IncrementalFreesoundLoader()
                
                assert loader.graph.number_of_nodes() == 0
                assert len(loader.processed_ids) == 0


class TestIncrementalFreesoundLoaderSkipProcessed:
    """Test skipping already-processed samples."""

    def test_skips_processed_samples(self, loader_with_mocks, mock_checkpoint):
        """Test that already-processed samples are skipped."""
        loader = loader_with_mocks
        loader.processed_ids = {'1', '2'}
        
        # Mock search results including processed samples
        sounds = [
            create_mock_sound(1, "sound1", [], 1.0, "user1", {}),
            create_mock_sound(2, "sound2", [], 1.0, "user2", {}),
            create_mock_sound(3, "sound3", [], 1.0, "user3", {})
        ]
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter(sounds))
        mock_results.more = False
        loader.client.text_search.return_value = mock_results
        
        # Mock similar sounds
        mock_sound_obj = Mock()
        mock_sound_obj.get_similar.return_value = []
        loader.client.get_sound.return_value = mock_sound_obj
        
        data = loader.fetch_data(query='test', max_samples=10)
        
        # Should only process sample 3
        assert len(data['samples']) == 1
        assert data['samples'][0]['id'] == 3

    def test_all_samples_processed_returns_empty(self, loader_with_mocks):
        """Test returns empty when all samples already processed."""
        loader = loader_with_mocks
        loader.processed_ids = {'1', '2', '3'}
        
        sounds = [
            create_mock_sound(1, "sound1", [], 1.0, "user1", {}),
            create_mock_sound(2, "sound2", [], 1.0, "user2", {}),
            create_mock_sound(3, "sound3", [], 1.0, "user3", {})
        ]
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter(sounds))
        mock_results.more = False
        loader.client.text_search.return_value = mock_results
        
        data = loader.fetch_data(query='test', max_samples=10)
        
        assert len(data['samples']) == 0


class TestIncrementalFreesoundLoaderTimeLimit:
    """Test time-limited execution."""

    def test_stops_at_time_limit(self, loader_with_mocks, mock_checkpoint):
        """Test execution stops when time limit is reached."""
        loader = loader_with_mocks
        loader.max_runtime_hours = 0.0001  # Very short time limit
        
        # Reset the loader state
        loader.graph = nx.DiGraph()
        loader.processed_ids = set()
        
        # Mock many samples
        sounds = [
            create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
            for i in range(100)
        ]
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter(sounds))
        mock_results.more = False
        loader.client.text_search.return_value = mock_results
        
        # Mock get_sound to return the sounds
        def get_sound_side_effect(sound_id):
            return sounds[sound_id] if sound_id < len(sounds) else sounds[0]
        loader.client.get_sound.side_effect = get_sound_side_effect
        
        # Mock the checkpoint save
        loader.checkpoint.save = Mock()
        
        # Add delay to ensure time limit is hit
        original_add = loader._add_sample_to_graph
        def slow_add(*args, **kwargs):
            time.sleep(0.001)
            return original_add(*args, **kwargs)
        
        with patch.object(loader, '_add_sample_to_graph', side_effect=slow_add):
            data = loader.fetch_data(query='test', max_samples=100)
        
        # Should process fewer than all samples due to time limit
        assert len(data['samples']) < 100
        
        # Should save checkpoint before stopping
        assert loader.checkpoint.save.called

    def test_no_time_limit_processes_all(self, loader_with_mocks, mock_checkpoint):
        """Test processes all samples when no time limit."""
        loader = loader_with_mocks
        loader.max_runtime_hours = None
        
        # Reset the loader state
        loader.graph = nx.DiGraph()
        loader.processed_ids = set()
        
        sounds = [
            create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
            for i in range(5)
        ]
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter(sounds))
        mock_results.more = False
        loader.client.text_search.return_value = mock_results
        
        # Mock get_sound to return the sounds
        def get_sound_side_effect(sound_id):
            return sounds[sound_id]
        loader.client.get_sound.side_effect = get_sound_side_effect
        
        data = loader.fetch_data(query='test', max_samples=5)
        
        assert len(data['samples']) == 5


class TestIncrementalFreesoundLoaderDeletedSamples:
    """Test deleted sample cleanup."""

    def test_cleanup_removes_deleted_samples(self, loader_with_mocks):
        """Test cleanup removes samples that return 404."""
        loader = loader_with_mocks
        loader.verify_existing_sounds = True
        
        # Add samples to graph
        loader.graph.add_node('1', name='sound1')
        loader.graph.add_node('2', name='sound2')
        loader.graph.add_node('3', name='sound3')
        loader.processed_ids = {'1', '2', '3'}
        
        # Mock API responses: sample 2 is deleted (404)
        def mock_get_sound(sample_id):
            if sample_id == 2:
                raise Exception("404 Not Found")
            return create_mock_sound(sample_id, f"sound{sample_id}", [], 1.0, f"user{sample_id}", {})
        
        loader.client.get_sound.side_effect = mock_get_sound
        
        deleted_count = loader.cleanup_deleted_samples()
        
        assert deleted_count == 1
        assert loader.graph.has_node('1')
        assert not loader.graph.has_node('2')
        assert loader.graph.has_node('3')
        assert '2' not in loader.processed_ids

    def test_cleanup_requires_verification_enabled(self, loader_with_mocks):
        """Test cleanup raises error when verification not enabled."""
        loader = loader_with_mocks
        loader.verify_existing_sounds = False
        
        with pytest.raises(DataProcessingError, match="verification not enabled"):
            loader.cleanup_deleted_samples()

    def test_cleanup_handles_api_errors(self, loader_with_mocks):
        """Test cleanup handles non-404 API errors gracefully."""
        loader = loader_with_mocks
        loader.verify_existing_sounds = True
        
        loader.graph.add_node('1', name='sound1')
        loader.processed_ids = {'1'}
        
        # Mock API error that's not 404
        loader.client.get_sound.side_effect = Exception("500 Server Error")
        
        # Should not raise, just skip the sample
        deleted_count = loader.cleanup_deleted_samples()
        
        assert deleted_count == 0
        assert loader.graph.has_node('1')


class TestIncrementalFreesoundLoaderMetadataUpdate:
    """Test metadata update functionality."""

    def test_update_metadata_merge_mode(self, loader_with_mocks):
        """Test updating metadata in merge mode."""
        loader = loader_with_mocks
        
        # Add node with initial metadata
        loader.graph.add_node('123', name='old_name', tags=['old_tag'])
        
        # Mock API response with updated metadata using create_mock_sound
        mock_sound = create_mock_sound(
            123, 'new_name', ['new_tag', 'another_tag'], 5.0, 'user',
            {'preview-hq-mp3': 'http://test.com/audio.mp3'}
        )
        
        loader.client.get_sound.return_value = mock_sound
        
        stats = loader.update_metadata(mode='merge', sample_ids=['123'])
        
        assert stats['nodes_updated'] == 1
        assert loader.graph.nodes['123']['name'] == 'new_name'
        assert loader.graph.nodes['123']['tags'] == ['new_tag', 'another_tag']

    def test_update_metadata_replace_mode(self, loader_with_mocks):
        """Test updating metadata in replace mode."""
        loader = loader_with_mocks
        
        # Add node with initial metadata
        loader.graph.add_node('123', name='old_name', custom_field='custom_value')
        
        # Mock API response using create_mock_sound
        mock_sound = create_mock_sound(123, 'new_name', [], 1.0, 'user', {})
        
        loader.client.get_sound.return_value = mock_sound
        
        stats = loader.update_metadata(mode='replace', sample_ids=['123'])
        
        assert stats['nodes_updated'] == 1
        assert loader.graph.nodes['123']['name'] == 'new_name'
        # Custom field should be removed in replace mode
        assert 'custom_field' not in loader.graph.nodes['123']

    def test_update_metadata_all_nodes(self, loader_with_mocks):
        """Test updating metadata for all nodes."""
        loader = loader_with_mocks
        
        loader.graph.add_node('1', name='sound1', type='sample')
        loader.graph.add_node('2', name='sound2', type='sample')
        
        def mock_get_sound(sample_id):
            return create_mock_sound(
                sound_id=sample_id,
                name=f'updated_{sample_id}',
                tags=['test'],
                duration=2.0,
                username='updated_user',
                previews={'preview-hq-mp3': 'http://example.com/preview.mp3'}
            )
        
        loader.client.get_sound.side_effect = mock_get_sound
        
        stats = loader.update_metadata(mode='merge')
        
        assert stats['nodes_updated'] == 2
        assert loader.graph.nodes['1']['name'] == 'updated_1'
        assert loader.graph.nodes['2']['name'] == 'updated_2'

    def test_update_metadata_invalid_mode(self, loader_with_mocks):
        """Test update_metadata raises error for invalid mode."""
        loader = loader_with_mocks
        
        with pytest.raises(ValueError, match="Invalid mode"):
            loader.update_metadata(mode='invalid')

    def test_update_metadata_handles_failures(self, loader_with_mocks):
        """Test update_metadata handles API failures gracefully."""
        loader = loader_with_mocks
        
        loader.graph.add_node('1', name='sound1', type='sample')
        loader.graph.add_node('2', name='sound2', type='sample')
        
        # Mock API to fail for sample 1
        def mock_get_sound(sample_id):
            if sample_id == 1:
                raise Exception("API Error")
            return create_mock_sound(
                sound_id=sample_id,
                name=f'sound{sample_id}',
                tags=['test'],
                duration=1.0,
                username='user',
                previews={}
            )
        
        loader.client.get_sound.side_effect = mock_get_sound
        
        stats = loader.update_metadata(mode='merge')
        
        assert stats['nodes_updated'] == 1
        assert stats['nodes_failed'] == 1


class TestIncrementalFreesoundLoaderBuildGraph:
    """Test build_graph method."""

    def test_build_graph_returns_incremental_graph(self, loader_with_mocks):
        """Test build_graph returns the incrementally-built graph."""
        loader = loader_with_mocks
        
        # Add nodes to incremental graph
        loader.graph.add_node('1', name='sound1')
        loader.graph.add_node('2', name='sound2')
        loader.graph.add_edge('1', '2', type='similar')
        
        # build_graph should return the existing graph
        graph = loader.build_graph({})
        
        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 1
        assert graph is loader.graph


class TestIncrementalFreesoundLoaderProgressStats:
    """Test progress statistics calculation."""

    def test_calculate_progress_stats(self, loader_with_mocks):
        """Test progress statistics calculation."""
        loader = loader_with_mocks
        
        stats = loader._calculate_progress_stats(
            current=50,
            total=100,
            elapsed_seconds=60
        )
        
        assert stats['percentage'] == 50.0
        assert stats['current'] == 50
        assert stats['total'] == 100
        assert stats['remaining'] == 50
        assert stats['elapsed_minutes'] == 1.0
        assert stats['eta_minutes'] > 0

    def test_calculate_progress_stats_zero_current(self, loader_with_mocks):
        """Test progress stats with zero current."""
        loader = loader_with_mocks
        
        stats = loader._calculate_progress_stats(
            current=0,
            total=100,
            elapsed_seconds=0
        )
        
        assert stats['percentage'] == 0.0
        assert stats['eta_minutes'] == 0


class TestIncrementalFreesoundLoaderIntegration:
    """Test complete incremental loading workflows."""

    def test_complete_incremental_workflow(self, loader_with_mocks, mock_checkpoint):
        """Test complete incremental loading workflow."""
        loader = loader_with_mocks
        loader.checkpoint_interval = 2
        
        # Mock search results
        sounds = [
            create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
            for i in range(3)
        ]
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter(sounds))
        mock_results.more = False
        loader.client.text_search.return_value = mock_results
        
        # Mock similar sounds
        mock_sound_obj = Mock()
        mock_sound_obj.get_similar.return_value = []
        loader.client.get_sound.return_value = mock_sound_obj
        
        # Fetch data
        data = loader.fetch_data(query='test', max_samples=10)
        
        # Build graph
        graph = loader.build_graph(data)
        
        assert graph.number_of_nodes() == 3
        assert len(loader.processed_ids) == 3
        assert mock_checkpoint.save.called

    def test_resume_from_checkpoint(self, mock_freesound_client, mock_checkpoint):
        """Test resuming from existing checkpoint."""
        # Mock existing checkpoint
        existing_graph = nx.DiGraph()
        existing_graph.add_node('1', name='sound1')
        
        mock_checkpoint.load.return_value = {
            'graph': existing_graph,
            'processed_ids': {'1'},
            'metadata': {}
        }
        
        with patch.dict('os.environ', {'FREESOUND_API_KEY': 'test_key'}):
            loader = IncrementalFreesoundLoader()
            
            # Mock new samples (including already-processed one)
            sounds = [
                create_mock_sound(1, "sound1", [], 1.0, "user1", {}),
                create_mock_sound(2, "sound2", [], 1.0, "user2", {})
            ]
            
            mock_results = Mock()
            mock_results.__iter__ = Mock(return_value=iter(sounds))
            mock_results.more = False
            loader.client.text_search.return_value = mock_results
            
            mock_sound_obj = Mock()
            mock_sound_obj.get_similar.return_value = []
            loader.client.get_sound.return_value = mock_sound_obj
            
            data = loader.fetch_data(query='test', max_samples=10)
            
            # Should only process sample 2
            assert len(data['samples']) == 1
            assert data['samples'][0]['id'] == 2
    