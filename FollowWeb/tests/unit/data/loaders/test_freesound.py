"""
Unit tests for FreesoundLoader.

Tests Freesound API integration, search functionality, graph construction,
and error handling with mocked freesound-python client responses.
"""

from unittest.mock import MagicMock, Mock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.exceptions import DataProcessingError
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader


@pytest.fixture
def mock_freesound_client():
    """Create a mock Freesound client."""
    with patch('FollowWeb_Visualizor.data.loaders.freesound.freesound') as mock_fs:
        client = Mock()
        mock_fs.FreesoundClient.return_value = client
        yield client


@pytest.fixture
def mock_sound():
    """Create a mock Freesound sound object."""
    sound = Mock()
    sound.id = 12345
    sound.name = "test_sound.wav"
    sound.tags = ["drum", "percussion"]
    sound.duration = 2.5
    sound.username = "test_user"
    sound.previews = {
        'preview-hq-mp3': 'https://freesound.org/preview.mp3'
    }
    # Mock as_dict() to return a proper dictionary
    sound.as_dict.return_value = {
        'id': 12345,
        'name': "test_sound.wav",
        'tags': ["drum", "percussion"],
        'duration': 2.5,
        'username': "test_user",
        'previews': {
            'preview_hq_mp3': 'https://freesound.org/preview.mp3'
        }
    }
    return sound


class TestFreesoundLoaderInitialization:
    """Test FreesoundLoader initialization."""

    def test_init_with_api_key_in_config(self, mock_freesound_client):
        """Test initialization with API key in config."""
        config = {'api_key': 'test_key_123'}
        loader = FreesoundLoader(config=config)
        
        assert loader.client == mock_freesound_client
        mock_freesound_client.set_token.assert_called_once_with('test_key_123')

    def test_init_with_api_key_in_env(self, mock_freesound_client):
        """Test initialization with API key from environment."""
        with patch.dict('os.environ', {'FREESOUND_API_KEY': 'env_key_456'}):
            loader = FreesoundLoader(config={})
            
            assert loader.client == mock_freesound_client
            mock_freesound_client.set_token.assert_called_once_with('env_key_456')

    def test_init_without_api_key_raises_error(self):
        """Test initialization without API key raises error."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(DataProcessingError, match="API key required"):
                FreesoundLoader(config={})

    def test_init_with_custom_rate_limit(self, mock_freesound_client):
        """Test initialization with custom rate limit."""
        config = {'api_key': 'test_key', 'requests_per_minute': 30}
        loader = FreesoundLoader(config=config)
        
        assert loader.rate_limiter.rate == 30

    def test_init_with_default_rate_limit(self, mock_freesound_client):
        """Test initialization with default rate limit."""
        config = {'api_key': 'test_key'}
        loader = FreesoundLoader(config=config)
        
        assert loader.rate_limiter.rate == 60


class TestFreesoundLoaderFetchData:
    """Test FreesoundLoader fetch_data method."""

    def test_fetch_data_requires_query_or_tags(self, mock_freesound_client):
        """Test that fetch_data requires query or tags."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        with pytest.raises(DataProcessingError, match="Must provide either query or tags"):
            loader.fetch_data()

    def test_fetch_data_with_query(self, mock_freesound_client, mock_sound):
        """Test fetch_data with text query."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        # Mock search results
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter([mock_sound]))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        data = loader.fetch_data(query='drum', max_samples=10, include_similar=False)
        
        assert 'samples' in data
        assert 'relationships' in data
        assert len(data['samples']) == 1
        assert data['samples'][0]['id'] == 12345
        assert data['samples'][0]['name'] == "test_sound.wav"

    def test_fetch_data_with_tags(self, mock_freesound_client, mock_sound):
        """Test fetch_data with tags."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter([mock_sound]))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        data = loader.fetch_data(tags=['drum', 'loop'], max_samples=10, include_similar=False)
        
        assert len(data['samples']) == 1
        mock_freesound_client.text_search.assert_called_once()

    def test_fetch_data_pagination(self, mock_freesound_client):
        """Test fetch_data handles pagination."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        # Create mock sounds for pagination
        sound1 = Mock(id=1, name="sound1", tags=[], duration=1.0, username="user1", previews={})
        sound2 = Mock(id=2, name="sound2", tags=[], duration=1.0, username="user2", previews={})
        
        # First page
        page1 = Mock()
        page1.__iter__ = Mock(return_value=iter([sound1]))
        page1.more = True
        
        # Second page
        page2 = Mock()
        page2.__iter__ = Mock(return_value=iter([sound2]))
        page2.more = False
        
        page1.next_page.return_value = page2
        mock_freesound_client.text_search.return_value = page1
        
        data = loader.fetch_data(query='test', max_samples=10, include_similar=False)
        
        assert len(data['samples']) == 2
        assert data['samples'][0]['id'] == 1
        assert data['samples'][1]['id'] == 2

    def test_fetch_data_respects_max_samples(self, mock_freesound_client):
        """Test fetch_data respects max_samples limit."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        # Create 5 mock sounds
        sounds = [Mock(id=i, name=f"sound{i}", tags=[], duration=1.0, 
                      username=f"user{i}", previews={}) for i in range(5)]
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter(sounds))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        data = loader.fetch_data(query='test', max_samples=3, include_similar=False)
        
        assert len(data['samples']) == 3

    def test_fetch_data_handles_api_error(self, mock_freesound_client):
        """Test fetch_data handles API errors."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        mock_freesound_client.text_search.side_effect = Exception("API Error")
        
        with pytest.raises(DataProcessingError, match="Failed to search Freesound API"):
            loader.fetch_data(query='test')

    def test_fetch_data_returns_empty_for_no_results(self, mock_freesound_client):
        """Test fetch_data returns empty data for no results."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter([]))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        data = loader.fetch_data(query='nonexistent', include_similar=False)
        
        assert data['samples'] == []
        assert data['relationships']['similar'] == {}


class TestFreesoundLoaderSimilarSounds:
    """Test FreesoundLoader similar sounds functionality."""

    def test_fetch_similar_sounds(self, mock_freesound_client, mock_sound):
        """Test fetching similar sounds relationships."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        # Mock search results
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter([mock_sound]))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        # Mock similar sounds
        similar_sound = Mock(id=67890)
        mock_sound_obj = Mock()
        mock_sound_obj.get_similar.return_value = [similar_sound]
        mock_freesound_client.get_sound.return_value = mock_sound_obj
        
        data = loader.fetch_data(query='drum', max_samples=10, include_similar=True)
        
        assert 'similar' in data['relationships']
        assert 12345 in data['relationships']['similar']
        assert data['relationships']['similar'][12345] == [(67890, 1.0)]

    def test_skip_similar_sounds_when_disabled(self, mock_freesound_client, mock_sound):
        """Test skipping similar sounds when include_similar=False."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter([mock_sound]))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        data = loader.fetch_data(query='drum', max_samples=10, include_similar=False)
        
        assert data['relationships']['similar'] == {}
        mock_freesound_client.get_sound.assert_not_called()

    def test_similar_sounds_handles_errors_gracefully(self, mock_freesound_client, mock_sound):
        """Test similar sounds handles errors gracefully."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter([mock_sound]))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        # Mock error when fetching similar sounds
        mock_freesound_client.get_sound.side_effect = Exception("API Error")
        
        # Should not raise, just log warning
        data = loader.fetch_data(query='drum', max_samples=10, include_similar=True)
        
        assert 12345 not in data['relationships']['similar']


class TestFreesoundLoaderBuildGraph:
    """Test FreesoundLoader build_graph method."""

    def test_build_graph_creates_nodes(self, mock_freesound_client):
        """Test build_graph creates nodes from samples."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        data = {
            'samples': [
                {'id': 1, 'name': 'sound1', 'tags': ['drum'], 'duration': 2.0, 
                 'username': 'user1', 'audio_url': 'http://test.com/1.mp3'},
                {'id': 2, 'name': 'sound2', 'tags': ['synth'], 'duration': 3.0,
                 'username': 'user2', 'audio_url': 'http://test.com/2.mp3'}
            ],
            'relationships': {'similar': {}}
        }
        
        graph = loader.build_graph(data)
        
        assert graph.number_of_nodes() == 2
        assert graph.has_node('1')
        assert graph.has_node('2')
        assert graph.nodes['1']['name'] == 'sound1'
        assert graph.nodes['1']['tags'] == ['drum']
        assert graph.nodes['2']['name'] == 'sound2'

    def test_build_graph_creates_edges(self, mock_freesound_client):
        """Test build_graph creates edges from relationships."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        data = {
            'samples': [
                {'id': 1, 'name': 'sound1', 'tags': [], 'duration': 1.0, 
                 'username': 'user1', 'audio_url': ''},
                {'id': 2, 'name': 'sound2', 'tags': [], 'duration': 1.0,
                 'username': 'user2', 'audio_url': ''}
            ],
            'relationships': {
                'similar': {
                    1: [(2, 0.8)]
                }
            }
        }
        
        graph = loader.build_graph(data)
        
        assert graph.number_of_edges() == 1
        assert graph.has_edge('1', '2')
        assert graph.edges['1', '2']['type'] == 'similar'
        assert graph.edges['1', '2']['weight'] == 0.8

    def test_build_graph_skips_missing_target_nodes(self, mock_freesound_client):
        """Test build_graph skips edges to non-existent nodes."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        data = {
            'samples': [
                {'id': 1, 'name': 'sound1', 'tags': [], 'duration': 1.0,
                 'username': 'user1', 'audio_url': ''}
            ],
            'relationships': {
                'similar': {
                    1: [(999, 0.5)]  # Node 999 doesn't exist
                }
            }
        }
        
        graph = loader.build_graph(data)
        
        assert graph.number_of_nodes() == 1
        assert graph.number_of_edges() == 0

    def test_build_graph_handles_empty_data(self, mock_freesound_client):
        """Test build_graph handles empty data."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        data = {'samples': [], 'relationships': {'similar': {}}}
        
        graph = loader.build_graph(data)
        
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_build_graph_sets_node_attributes(self, mock_freesound_client):
        """Test build_graph sets all node attributes correctly."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        data = {
            'samples': [
                {
                    'id': 123,
                    'name': 'test_sound.wav',
                    'tags': ['drum', 'loop'],
                    'duration': 4.5,
                    'username': 'audio_creator',
                    'audio_url': 'https://example.com/sound.mp3'
                }
            ],
            'relationships': {'similar': {}}
        }
        
        graph = loader.build_graph(data)
        
        node_attrs = graph.nodes['123']
        assert node_attrs['name'] == 'test_sound.wav'
        assert node_attrs['tags'] == ['drum', 'loop']
        assert node_attrs['duration'] == 4.5
        assert node_attrs['user'] == 'audio_creator'
        assert node_attrs['audio_url'] == 'https://example.com/sound.mp3'
        assert node_attrs['type'] == 'sample'


class TestFreesoundLoaderMetadataExtraction:
    """Test FreesoundLoader metadata extraction."""

    def test_extract_sample_metadata_complete(self, mock_freesound_client, mock_sound):
        """Test extracting complete metadata from sound object."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        metadata = loader._extract_sample_metadata(mock_sound)
        
        assert metadata['id'] == 12345
        assert metadata['name'] == "test_sound.wav"
        assert metadata['tags'] == ["drum", "percussion"]
        assert metadata['duration'] == 2.5
        assert metadata['username'] == "test_user"
        assert metadata['audio_url'] == 'https://freesound.org/preview.mp3'

    def test_extract_sample_metadata_missing_fields(self, mock_freesound_client):
        """Test extracting metadata with missing fields."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        # Sound with minimal attributes - use spec to limit attributes
        sound = Mock(spec=['id', 'name'])
        sound.id = 999
        sound.name = "minimal.wav"
        
        metadata = loader._extract_sample_metadata(sound)
        
        assert metadata['id'] == 999
        assert metadata['name'] == "minimal.wav"
        assert metadata['tags'] == []
        assert metadata['duration'] == 0
        assert metadata['username'] == ''
        assert metadata['audio_url'] == ''

    def test_extract_sample_metadata_no_preview(self, mock_freesound_client):
        """Test extracting metadata when preview is missing."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        sound = Mock()
        sound.id = 111
        sound.name = "no_preview.wav"
        sound.tags = []
        sound.duration = 1.0
        sound.username = "user"
        sound.previews = {}
        
        metadata = loader._extract_sample_metadata(sound)
        
        assert metadata['audio_url'] == ''


class TestFreesoundLoaderIntegration:
    """Test FreesoundLoader integration scenarios."""

    def test_complete_workflow(self, mock_freesound_client):
        """Test complete workflow from fetch to graph."""
        loader = FreesoundLoader(config={'api_key': 'test_key'})
        
        # Mock sounds
        sound1 = Mock(id=1, name="s1", tags=["tag1"], duration=1.0, username="u1", previews={})
        sound2 = Mock(id=2, name="s2", tags=["tag2"], duration=2.0, username="u2", previews={})
        
        mock_results = Mock()
        mock_results.__iter__ = Mock(return_value=iter([sound1, sound2]))
        mock_results.more = False
        mock_freesound_client.text_search.return_value = mock_results
        
        # Mock similar sounds
        similar = Mock(id=2)
        sound1_obj = Mock()
        sound1_obj.get_similar.return_value = [similar]
        mock_freesound_client.get_sound.return_value = sound1_obj
        
        # Use load() method for complete workflow
        graph = loader.load(query='test', max_samples=10)
        
        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() == 2
        assert graph.has_edge('1', '2')
