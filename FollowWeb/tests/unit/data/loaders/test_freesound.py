"""
Unit tests for FreesoundLoader.

Tests Freesound API integration, search functionality, graph construction,
and error handling with mocked freesound-python client responses.
"""

from unittest.mock import MagicMock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.exceptions import DataProcessingError
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader

pytestmark = [pytest.mark.unit, pytest.mark.data]

def create_mock_sound(
    sound_id,
    name="test_sound.wav",
    tags=None,
    duration=1.0,
    username="test_user",
    previews=None,
):
    """Helper to create a properly mocked Freesound sound object using MagicMock."""
    if tags is None:
        tags = []
    if previews is None:
        previews = {}

    # Use MagicMock for automatic magic method support
    sound = MagicMock()
    sound.id = sound_id
    sound.name = name
    sound.tags = tags
    sound.duration = duration
    sound.username = username
    sound.previews = previews

    # Configure as_dict() to return a proper dictionary (not a Mock)
    sound.as_dict.return_value = {
        "id": sound_id,
        "name": name,
        "tags": tags,
        "duration": duration,
        "username": username,
        "previews": previews,
    }
    return sound


@pytest.fixture
def mock_freesound_client():
    """Create a mock Freesound client using MagicMock for better method support."""
    with patch("FollowWeb_Visualizor.data.loaders.freesound.freesound") as mock_fs:
        client = MagicMock()
        mock_fs.FreesoundClient.return_value = client
        yield client


@pytest.fixture
def mock_sound():
    """Create a mock Freesound sound object."""
    return create_mock_sound(
        sound_id=12345,
        name="test_sound.wav",
        tags=["drum", "percussion"],
        duration=2.5,
        username="test_user",
        previews={
            "preview-hq-mp3": "https://freesound.org/preview.mp3",
            "preview_hq_mp3": "https://freesound.org/preview.mp3",
        },
    )


class TestFreesoundLoaderInitialization:
    """Test FreesoundLoader initialization."""

    def test_init_with_api_key_in_config(self, mock_freesound_client):
        """Test initialization with API key in config."""
        config = {"api_key": "test_key_123"}
        loader = FreesoundLoader(config=config)

        assert loader.client == mock_freesound_client
        mock_freesound_client.set_token.assert_called_once_with("test_key_123")

    def test_init_with_api_key_in_env(self, mock_freesound_client):
        """Test initialization with API key from environment."""
        with patch.dict("os.environ", {"FREESOUND_API_KEY": "env_key_456"}):
            loader = FreesoundLoader(config={})

            assert loader.client == mock_freesound_client
            mock_freesound_client.set_token.assert_called_once_with("env_key_456")

    def test_init_without_api_key_raises_error(self):
        """Test initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(DataProcessingError, match="API key required"):
                FreesoundLoader(config={})

    def test_init_with_custom_rate_limit(self, mock_freesound_client):
        """Test initialization with custom rate limit."""
        config = {"api_key": "test_key", "requests_per_minute": 30}
        loader = FreesoundLoader(config=config)

        assert loader.rate_limiter.rate == 30

    def test_init_with_default_rate_limit(self, mock_freesound_client):
        """Test initialization with default rate limit."""
        config = {"api_key": "test_key"}
        loader = FreesoundLoader(config=config)

        assert loader.rate_limiter.rate == 60


class TestFreesoundLoaderFetchData:
    """Test FreesoundLoader fetch_data method."""

    def test_fetch_data_requires_query_or_tags(self, mock_freesound_client):
        """Test that fetch_data requires query or tags."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        with pytest.raises(
            DataProcessingError, match="Must provide either query or tags"
        ):
            loader.fetch_data()

    def test_fetch_data_with_query(self, mock_freesound_client, mock_sound):
        """Test fetch_data with text query."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        # Mock search results using MagicMock for automatic iterator support
        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter([mock_sound])
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        # Mock get_sound to return full sound object
        mock_freesound_client.get_sound.return_value = mock_sound

        data = loader.fetch_data(query="drum", max_samples=10, include_similar=False)

        assert "samples" in data
        assert "relationships" in data
        assert len(data["samples"]) == 1
        assert data["samples"][0]["id"] == 12345
        assert data["samples"][0]["name"] == "test_sound.wav"

    def test_fetch_data_with_tags(self, mock_freesound_client, mock_sound):
        """Test fetch_data with tags."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter([mock_sound])
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        # Mock get_sound to return full sound object
        mock_freesound_client.get_sound.return_value = mock_sound

        data = loader.fetch_data(
            tags=["drum", "loop"], max_samples=10, include_similar=False
        )

        assert len(data["samples"]) == 1
        mock_freesound_client.text_search.assert_called_once()

    def test_fetch_data_pagination(self, mock_freesound_client):
        """Test fetch_data handles pagination."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        # Create mock sounds for pagination
        sound1 = create_mock_sound(1, "sound1", [], 1.0, "user1", {})
        sound2 = create_mock_sound(2, "sound2", [], 1.0, "user2", {})

        # First page using MagicMock
        page1 = MagicMock()
        page1.__iter__.return_value = iter([sound1])
        page1.next = MagicMock()

        # Second page using MagicMock
        page2 = MagicMock()
        page2.__iter__.return_value = iter([sound2])
        page2.next = None

        page1.next_page.return_value = page2
        mock_freesound_client.text_search.return_value = page1

        # Mock get_sound to return the appropriate sound
        def get_sound_side_effect(sound_id):
            return sound1 if sound_id == 1 else sound2

        mock_freesound_client.get_sound.side_effect = get_sound_side_effect

        data = loader.fetch_data(query="test", max_samples=10, include_similar=False)

        assert len(data["samples"]) == 2
        assert data["samples"][0]["id"] == 1
        assert data["samples"][1]["id"] == 2

    def test_fetch_data_respects_max_samples(self, mock_freesound_client):
        """Test fetch_data respects max_samples limit."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        # Create 5 mock sounds
        sounds = [
            create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {}) for i in range(5)
        ]

        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter(sounds)
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        # Mock get_sound to return the appropriate sound
        def get_sound_side_effect(sound_id):
            return sounds[sound_id]

        mock_freesound_client.get_sound.side_effect = get_sound_side_effect

        data = loader.fetch_data(query="test", max_samples=3, include_similar=False)

        assert len(data["samples"]) == 3

    def test_fetch_data_handles_api_error(self, mock_freesound_client):
        """Test fetch_data handles API errors."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        mock_freesound_client.text_search.side_effect = Exception("API Error")

        with pytest.raises(DataProcessingError, match="Failed to search Freesound API"):
            loader.fetch_data(query="test")

    def test_fetch_data_returns_empty_for_no_results(self, mock_freesound_client):
        """Test fetch_data returns empty data for no results."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter([])
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        data = loader.fetch_data(query="nonexistent", include_similar=False)

        assert data["samples"] == []
        assert data["relationships"]["similar"] == {}


class TestFreesoundLoaderSimilarSounds:
    """Test FreesoundLoader similar sounds functionality."""

    def test_fetch_similar_sounds(self, mock_freesound_client, mock_sound):
        """Test fetching similar sounds relationships."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        # Mock search results
        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter([mock_sound])
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        # Mock similar sounds with proper as_dict()
        similar_sound = create_mock_sound(67890, "similar.wav", [], 1.0, "user", {})

        # Mock get_sound to return the sound with get_similar method
        mock_sound.get_similar.return_value = [similar_sound]
        mock_freesound_client.get_sound.return_value = mock_sound

        data = loader.fetch_data(query="drum", max_samples=10, include_similar=True)

        assert "similar" in data["relationships"]
        assert 12345 in data["relationships"]["similar"]
        assert data["relationships"]["similar"][12345] == [(67890, 1.0)]

    def test_skip_similar_sounds_when_disabled(self, mock_freesound_client, mock_sound):
        """Test skipping similar sounds when include_similar=False."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter([mock_sound])
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        # Mock get_sound for metadata fetching
        mock_freesound_client.get_sound.return_value = mock_sound

        data = loader.fetch_data(query="drum", max_samples=10, include_similar=False)

        assert data["relationships"]["similar"] == {}
        # get_sound is called once for metadata, but get_similar should not be called
        assert mock_freesound_client.get_sound.call_count == 1

    def test_similar_sounds_handles_errors_gracefully(
        self, mock_freesound_client, mock_sound
    ):
        """Test similar sounds handles errors gracefully."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter([mock_sound])
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        # Mock error when fetching similar sounds
        mock_freesound_client.get_sound.side_effect = Exception("API Error")

        # Should not raise, just log warning
        data = loader.fetch_data(query="drum", max_samples=10, include_similar=True)

        assert 12345 not in data["relationships"]["similar"]


class TestFreesoundLoaderBuildGraph:
    """Test FreesoundLoader build_graph method."""

    def test_build_graph_creates_nodes(self, mock_freesound_client):
        """Test build_graph creates nodes from samples."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        data = {
            "samples": [
                {
                    "id": 1,
                    "name": "sound1",
                    "tags": ["drum"],
                    "duration": 2.0,
                    "username": "user1",
                    "audio_url": "http://test.com/1.mp3",
                },
                {
                    "id": 2,
                    "name": "sound2",
                    "tags": ["synth"],
                    "duration": 3.0,
                    "username": "user2",
                    "audio_url": "http://test.com/2.mp3",
                },
            ],
            "relationships": {"similar": {}},
        }

        graph = loader.build_graph(data)

        assert graph.number_of_nodes() == 2
        assert graph.has_node("1")
        assert graph.has_node("2")
        assert graph.nodes["1"]["name"] == "sound1"
        assert graph.nodes["1"]["tags"] == ["drum"]
        assert graph.nodes["2"]["name"] == "sound2"

    def test_build_graph_creates_edges(self, mock_freesound_client):
        """Test build_graph creates edges from relationships."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        data = {
            "samples": [
                {
                    "id": 1,
                    "name": "sound1",
                    "tags": [],
                    "duration": 1.0,
                    "username": "user1",
                    "audio_url": "",
                },
                {
                    "id": 2,
                    "name": "sound2",
                    "tags": [],
                    "duration": 1.0,
                    "username": "user2",
                    "audio_url": "",
                },
            ],
            "relationships": {"similar": {1: [(2, 0.8)]}},
        }

        graph = loader.build_graph(data)

        assert graph.number_of_edges() == 1
        assert graph.has_edge("1", "2")
        assert graph.edges["1", "2"]["type"] == "similar"
        assert graph.edges["1", "2"]["weight"] == 0.8

    def test_build_graph_skips_missing_target_nodes(self, mock_freesound_client):
        """Test build_graph skips edges to non-existent nodes."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        data = {
            "samples": [
                {
                    "id": 1,
                    "name": "sound1",
                    "tags": [],
                    "duration": 1.0,
                    "username": "user1",
                    "audio_url": "",
                }
            ],
            "relationships": {
                "similar": {
                    1: [(999, 0.5)]  # Node 999 doesn't exist
                }
            },
        }

        graph = loader.build_graph(data)

        assert graph.number_of_nodes() == 1
        assert graph.number_of_edges() == 0

    def test_build_graph_handles_empty_data(self, mock_freesound_client):
        """Test build_graph handles empty data."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        data = {"samples": [], "relationships": {"similar": {}}}

        graph = loader.build_graph(data)

        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_build_graph_sets_node_attributes(self, mock_freesound_client):
        """Test build_graph sets all node attributes correctly."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        data = {
            "samples": [
                {
                    "id": 123,
                    "name": "test_sound.wav",
                    "tags": ["drum", "loop"],
                    "duration": 4.5,
                    "username": "audio_creator",
                    "audio_url": "https://example.com/sound.mp3",
                }
            ],
            "relationships": {"similar": {}},
        }

        graph = loader.build_graph(data)

        node_attrs = graph.nodes["123"]
        assert node_attrs["name"] == "test_sound.wav"
        assert node_attrs["tags"] == ["drum", "loop"]
        assert node_attrs["duration"] == 4.5
        assert node_attrs["user"] == "audio_creator"
        assert node_attrs["audio_url"] == "https://example.com/sound.mp3"
        assert node_attrs["type"] == "sample"


class TestFreesoundLoaderMetadataExtraction:
    """Test FreesoundLoader metadata extraction."""

    def test_extract_sample_metadata_complete(self, mock_freesound_client, mock_sound):
        """Test extracting complete metadata from sound object."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        metadata = loader._extract_sample_metadata(mock_sound)

        assert metadata["id"] == 12345
        assert metadata["name"] == "test_sound.wav"
        assert metadata["tags"] == ["drum", "percussion"]
        assert metadata["duration"] == 2.5
        assert metadata["username"] == "test_user"
        assert metadata["audio_url"] == "https://freesound.org/preview.mp3"

    def test_extract_sample_metadata_missing_fields(self, mock_freesound_client):
        """Test extracting metadata with missing fields."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        # Sound with minimal attributes
        sound = create_mock_sound(999, "minimal.wav", [], 0, "", {})

        metadata = loader._extract_sample_metadata(sound)

        assert metadata["id"] == 999
        assert metadata["name"] == "minimal.wav"
        assert metadata["tags"] == []
        assert metadata["duration"] == 0
        assert metadata["username"] == ""
        assert metadata["audio_url"] == ""

    def test_extract_sample_metadata_no_preview(self, mock_freesound_client):
        """Test extracting metadata when preview is missing."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        sound = create_mock_sound(111, "no_preview.wav", [], 1.0, "user", {})

        metadata = loader._extract_sample_metadata(sound)

        assert metadata["audio_url"] == ""


class TestFreesoundLoaderIntegration:
    """Test FreesoundLoader integration scenarios."""

    def test_complete_workflow(self, mock_freesound_client):
        """Test complete workflow from fetch to graph."""
        loader = FreesoundLoader(config={"api_key": "test_key"})

        # Mock sounds
        sound1 = create_mock_sound(1, "s1", ["tag1"], 1.0, "u1", {})
        sound2 = create_mock_sound(2, "s2", ["tag2"], 2.0, "u2", {})

        mock_results = MagicMock()
        mock_results.__iter__.return_value = iter([sound1, sound2])
        mock_results.next = None
        mock_freesound_client.text_search.return_value = mock_results

        # Mock get_sound to return full sound objects
        def get_sound_side_effect(sound_id):
            if sound_id == 1:
                return sound1
            elif sound_id == 2:
                return sound2
            return sound1  # default

        mock_freesound_client.get_sound.side_effect = get_sound_side_effect

        # Mock similar sounds on sound1
        similar = create_mock_sound(2, "s2", ["tag2"], 2.0, "u2", {})
        sound1.get_similar.return_value = [similar]

        # Use load() method for complete workflow
        graph = loader.load(query="test", max_samples=10)

        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() == 2
        assert graph.has_edge("1", "2")
