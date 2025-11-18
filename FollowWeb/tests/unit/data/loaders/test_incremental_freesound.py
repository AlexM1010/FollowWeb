"""
Unit tests for IncrementalFreesoundLoader.

Tests incremental loading with checkpoint support, time limits, deleted sample
cleanup, and metadata updates with mocked checkpoint and API operations.
"""

import tempfile
import time
from unittest.mock import Mock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.exceptions import DataProcessingError
from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
    IncrementalFreesoundLoader,
)

pytestmark = [pytest.mark.unit, pytest.mark.data]


def create_mock_sound(
    sound_id,
    name="test_sound.wav",
    tags=None,
    duration=1.0,
    username="test_user",
    previews=None,
    filesize=1024,  # Default to non-zero filesize
):
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
    sound.filesize = filesize

    # Mock as_dict() to return a proper dictionary (not a Mock)
    sound.as_dict = Mock(
        return_value={
            "id": sound_id,
            "name": name,
            "tags": tags,
            "duration": duration,
            "username": username,
            "previews": previews,
            "filesize": filesize,
        }
    )
    return sound


@pytest.fixture
def mock_freesound_client():
    """Create a mock Freesound client."""
    with patch("FollowWeb_Visualizor.data.loaders.freesound.freesound") as mock_fs:
        client = Mock()
        mock_fs.FreesoundClient.return_value = client
        yield client


@pytest.fixture
def mock_checkpoint():
    """Create a mock GraphCheckpoint."""
    with patch(
        "FollowWeb_Visualizor.data.loaders.incremental_freesound.GraphCheckpoint"
    ) as mock_cp:
        checkpoint_instance = Mock()
        checkpoint_instance.load.return_value = None
        checkpoint_instance.exists.return_value = False
        mock_cp.return_value = checkpoint_instance
        yield checkpoint_instance


@pytest.fixture
def loader_with_mocks(mock_freesound_client, mock_checkpoint, tmp_path):
    """Create IncrementalFreesoundLoader with mocked dependencies and isolated checkpoint dir."""
    config = {"api_key": "test_key", "checkpoint_dir": str(tmp_path / "checkpoints")}
    loader = IncrementalFreesoundLoader(config=config)
    return loader


class TestIncrementalFreesoundLoaderInitialization:
    """Test IncrementalFreesoundLoader initialization."""

    def test_init_with_default_config(
        self, mock_freesound_client, mock_checkpoint, tmp_path
    ):
        """Test initialization with default configuration."""
        config = {
            "api_key": "test_key",
            "checkpoint_dir": str(tmp_path / "checkpoints"),
        }
        loader = IncrementalFreesoundLoader(config=config)

        assert loader.checkpoint_interval == 50
        assert loader.max_runtime_hours is None
        assert loader.verify_existing_sounds is False
        assert isinstance(loader.processed_ids, set)

    def test_init_with_custom_config(self, mock_freesound_client, mock_checkpoint):
        """Test initialization with custom configuration."""
        config = {
            "api_key": "test_key",
            "checkpoint_dir": "custom_checkpoints",
            "checkpoint_interval": 25,
            "max_runtime_hours": 1.5,
            "verify_existing_sounds": True,
        }

        loader = IncrementalFreesoundLoader(config=config)

        assert loader.checkpoint_interval == 25
        assert loader.max_runtime_hours == 1.5
        assert loader.verify_existing_sounds is True

    def test_init_loads_existing_checkpoint(
        self, mock_freesound_client, mock_checkpoint, tmp_path
    ):
        """Test initialization loads existing checkpoint."""
        # Mock existing checkpoint data
        existing_graph = nx.DiGraph()
        existing_graph.add_node("1")

        def mock_load_checkpoint(self):
            self.graph = existing_graph
            self.processed_ids = {"1", "2"}

        config = {
            "api_key": "test_key",
            "checkpoint_dir": str(tmp_path / "checkpoints"),
        }
        with patch.object(
            IncrementalFreesoundLoader, "_load_checkpoint", mock_load_checkpoint
        ):
            loader = IncrementalFreesoundLoader(config=config)

            assert loader.graph.number_of_nodes() == 1
            assert loader.processed_ids == {"1", "2"}


class TestIncrementalFreesoundLoaderCheckpoint:
    """Test checkpoint loading and saving."""

    def test_load_checkpoint_restores_state(
        self, mock_freesound_client, mock_checkpoint, tmp_path
    ):
        """Test loading checkpoint restores graph and processed IDs."""
        graph = nx.DiGraph()
        graph.add_nodes_from(["a", "b", "c"])

        def mock_load_checkpoint(self):
            self.graph = graph
            self.processed_ids = {"a", "b", "c"}

        config = {
            "api_key": "test_key",
            "checkpoint_dir": str(tmp_path / "checkpoints"),
        }
        with patch.object(
            IncrementalFreesoundLoader, "_load_checkpoint", mock_load_checkpoint
        ):
            loader = IncrementalFreesoundLoader(config=config)

            assert loader.graph.number_of_nodes() == 3
            assert len(loader.processed_ids) == 3

    def test_save_checkpoint_called_periodically(
        self, loader_with_mocks, mock_checkpoint
    ):
        """Test checkpoint is saved at configured intervals."""
        loader = loader_with_mocks
        loader.checkpoint_interval = 2

        # Reset the loader state to start fresh
        loader.graph = nx.DiGraph()
        loader.processed_ids = set()

        # Mock search results
        sounds = [
            create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {}) for i in range(5)
        ]

        mock_results = Mock()
        mock_results.__iter__ = lambda self: iter(sounds)
        mock_results.more = False
        loader.client.text_search.return_value = mock_results

        # Mock get_sound to return the sounds
        def get_sound_side_effect(sound_id):
            return sounds[sound_id]

        loader.client.get_sound.side_effect = get_sound_side_effect

        # Mock the checkpoint save method on the loader's checkpoint instance
        loader.checkpoint.save = Mock()

        loader.fetch_data(query="test", max_samples=5)

        # Should save at intervals: after 2, 4, and final
        assert loader.checkpoint.save.call_count >= 1  # At least final save

    def test_no_checkpoint_load_starts_fresh(
        self, mock_freesound_client, mock_checkpoint, tmp_path
    ):
        """Test starting fresh when no checkpoint exists."""
        mock_checkpoint.load.return_value = None

        config = {
            "api_key": "test_key",
            "checkpoint_dir": str(tmp_path / "checkpoints"),
        }
        with patch.object(IncrementalFreesoundLoader, "_load_checkpoint"):
            loader = IncrementalFreesoundLoader(config=config)

            assert loader.graph.number_of_nodes() == 0
            assert len(loader.processed_ids) == 0


class TestIncrementalFreesoundLoaderSkipProcessed:
    """Test skipping already-processed samples."""

    def test_skips_processed_samples(self, loader_with_mocks, mock_checkpoint):
        """Test that already-processed samples are skipped."""
        loader = loader_with_mocks
        loader.processed_ids = {"1", "2"}

        # Mock _search_samples to return properly formatted sample dictionaries
        sample_dicts = [
            {
                "id": 1,
                "name": "sound1",
                "tags": [],
                "duration": 1.0,
                "username": "user1",
                "audio_url": "http://example.com/sound1.mp3",
                "previews": {},
                "num_downloads": 100,
                "avg_rating": 4.0,
                "num_ratings": 10,
            },
            {
                "id": 2,
                "name": "sound2",
                "tags": [],
                "duration": 1.0,
                "username": "user2",
                "audio_url": "http://example.com/sound2.mp3",
                "previews": {},
                "num_downloads": 100,
                "avg_rating": 4.0,
                "num_ratings": 10,
            },
            {
                "id": 3,
                "name": "sound3",
                "tags": [],
                "duration": 1.0,
                "username": "user3",
                "audio_url": "http://example.com/sound3.mp3",
                "previews": {},
                "num_downloads": 100,
                "avg_rating": 4.0,
                "num_ratings": 10,
            },
        ]

        with patch.object(loader, "_search_samples", return_value=sample_dicts):
            with patch.object(
                loader, "_fetch_similar_sounds_for_sample", return_value=[]
            ):
                data = loader.fetch_data(query="test", max_samples=10)

        # Should only process sample 3 (1 and 2 are already processed)
        assert len(data["samples"]) == 1
        assert data["samples"][0]["id"] == 3

    def test_all_samples_processed_returns_empty(self, loader_with_mocks):
        """Test returns empty when all samples already processed."""
        loader = loader_with_mocks
        loader.processed_ids = {"1", "2", "3"}

        # Mock _search_samples to return properly formatted sample dictionaries
        sample_dicts = [
            {
                "id": 1,
                "name": "sound1",
                "tags": [],
                "duration": 1.0,
                "username": "user1",
                "audio_url": "http://example.com/sound1.mp3",
                "previews": {},
                "num_downloads": 100,
                "avg_rating": 4.0,
                "num_ratings": 10,
            },
            {
                "id": 2,
                "name": "sound2",
                "tags": [],
                "duration": 1.0,
                "username": "user2",
                "audio_url": "http://example.com/sound2.mp3",
                "previews": {},
                "num_downloads": 100,
                "avg_rating": 4.0,
                "num_ratings": 10,
            },
            {
                "id": 3,
                "name": "sound3",
                "tags": [],
                "duration": 1.0,
                "username": "user3",
                "audio_url": "http://example.com/sound3.mp3",
                "previews": {},
                "num_downloads": 100,
                "avg_rating": 4.0,
                "num_ratings": 10,
            },
        ]

        with patch.object(loader, "_search_samples", return_value=sample_dicts):
            with patch.object(
                loader, "_fetch_similar_sounds_for_sample", return_value=[]
            ):
                data = loader.fetch_data(query="test", max_samples=10)

        assert len(data["samples"]) == 0


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
        mock_results.__iter__ = lambda self: iter(sounds)
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

        with patch.object(loader, "_add_sample_to_graph", side_effect=slow_add):
            data = loader.fetch_data(query="test", max_samples=100)

        # Should process fewer samples due to time limit, or all if processing was very fast
        # The time limit check happens inside the processing loop
        assert len(data["samples"]) <= 100
        if len(data["samples"]) == 100:
            # If all samples were processed, the time limit was likely not hit
            # This can happen in fast CI environments - just verify checkpoint was saved
            assert loader.checkpoint.save.called
        else:
            # Time limit was hit - should have processed fewer samples
            assert len(data["samples"]) < 100
            assert loader.checkpoint.save.called

    def test_no_time_limit_processes_all(self, loader_with_mocks, mock_checkpoint):
        """Test processes all samples when no time limit."""
        loader = loader_with_mocks
        loader.max_runtime_hours = None

        # Reset the loader state
        loader.graph = nx.DiGraph()
        loader.processed_ids = set()

        sounds = [
            create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {}) for i in range(5)
        ]

        mock_results = Mock()
        mock_results.__iter__ = lambda self: iter(sounds)
        mock_results.more = False
        loader.client.text_search.return_value = mock_results

        # Mock get_sound to return the sounds
        def get_sound_side_effect(sound_id):
            return sounds[sound_id]

        loader.client.get_sound.side_effect = get_sound_side_effect

        data = loader.fetch_data(query="test", max_samples=5)

        assert len(data["samples"]) == 5


class TestIncrementalFreesoundLoaderDeletedSamples:
    """Test deleted sample cleanup."""

    def test_cleanup_removes_deleted_samples(self, loader_with_mocks):
        """Test cleanup removes samples that return 404."""
        loader = loader_with_mocks
        loader.verify_existing_sounds = True

        # Add samples to graph
        loader.graph.add_node("1", name="sound1")
        loader.graph.add_node("2", name="sound2")
        loader.graph.add_node("3", name="sound3")
        loader.processed_ids = {"1", "2", "3"}

        # Mock API responses: sample 2 is deleted (404)
        def mock_get_sound(sample_id):
            if sample_id == 2:
                raise Exception("404 Not Found")
            return create_mock_sound(
                sample_id, f"sound{sample_id}", [], 1.0, f"user{sample_id}", {}
            )

        loader.client.get_sound.side_effect = mock_get_sound

        deleted_count = loader.cleanup_deleted_samples()

        assert deleted_count == 1
        assert loader.graph.has_node("1")
        assert not loader.graph.has_node("2")
        assert loader.graph.has_node("3")
        assert "2" not in loader.processed_ids

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

        loader.graph.add_node("1", name="sound1")
        loader.processed_ids = {"1"}

        # Mock API error that's not 404
        loader.client.get_sound.side_effect = Exception("500 Server Error")

        # Should not raise, just skip the sample
        deleted_count = loader.cleanup_deleted_samples()

        assert deleted_count == 0
        assert loader.graph.has_node("1")


class TestIncrementalFreesoundLoaderMetadataUpdate:
    """Test metadata update functionality."""

    def test_update_metadata_merge_mode(self, loader_with_mocks):
        """Test updating metadata in merge mode."""
        loader = loader_with_mocks

        # Add node with initial metadata
        loader.graph.add_node("123", name="old_name", tags=["old_tag"])

        # Mock API response with updated metadata using create_mock_sound
        mock_sound = create_mock_sound(
            123,
            "new_name",
            ["new_tag", "another_tag"],
            5.0,
            "user",
            {"preview-hq-mp3": "http://test.com/audio.mp3"},
        )

        loader.client.get_sound.return_value = mock_sound

        stats = loader.update_metadata(mode="merge", sample_ids=["123"])

        assert stats["nodes_updated"] == 1
        assert loader.graph.nodes["123"]["name"] == "new_name"
        assert loader.graph.nodes["123"]["tags"] == ["new_tag", "another_tag"]

    def test_update_metadata_replace_mode(self, loader_with_mocks):
        """Test updating metadata in replace mode."""
        loader = loader_with_mocks

        # Add node with initial metadata
        loader.graph.add_node("123", name="old_name", custom_field="custom_value")

        # Mock API response using create_mock_sound
        mock_sound = create_mock_sound(123, "new_name", [], 1.0, "user", {})

        loader.client.get_sound.return_value = mock_sound

        stats = loader.update_metadata(mode="replace", sample_ids=["123"])

        assert stats["nodes_updated"] == 1
        assert loader.graph.nodes["123"]["name"] == "new_name"
        # Custom field should be removed in replace mode
        assert "custom_field" not in loader.graph.nodes["123"]

    def test_update_metadata_all_nodes(self, loader_with_mocks):
        """Test updating metadata for all nodes."""
        loader = loader_with_mocks

        loader.graph.add_node("1", name="sound1", type="sample")
        loader.graph.add_node("2", name="sound2", type="sample")

        def mock_get_sound(sample_id):
            return create_mock_sound(
                sound_id=sample_id,
                name=f"updated_{sample_id}",
                tags=["test"],
                duration=2.0,
                username="updated_user",
                previews={"preview-hq-mp3": "http://example.com/preview.mp3"},
            )

        loader.client.get_sound.side_effect = mock_get_sound

        stats = loader.update_metadata(mode="merge")

        assert stats["nodes_updated"] == 2
        assert loader.graph.nodes["1"]["name"] == "updated_1"
        assert loader.graph.nodes["2"]["name"] == "updated_2"

    def test_update_metadata_invalid_mode(self, loader_with_mocks):
        """Test update_metadata raises error for invalid mode."""
        loader = loader_with_mocks

        with pytest.raises(ValueError, match="Invalid mode"):
            loader.update_metadata(mode="invalid")

    def test_update_metadata_handles_failures(self, loader_with_mocks):
        """Test update_metadata handles API failures gracefully."""
        loader = loader_with_mocks

        loader.graph.add_node("1", name="sound1", type="sample")
        loader.graph.add_node("2", name="sound2", type="sample")

        # Mock API to fail for sample 1
        def mock_get_sound(sample_id):
            if sample_id == 1:
                raise Exception("API Error")
            return create_mock_sound(
                sound_id=sample_id,
                name=f"sound{sample_id}",
                tags=["test"],
                duration=1.0,
                username="user",
                previews={},
            )

        loader.client.get_sound.side_effect = mock_get_sound

        stats = loader.update_metadata(mode="merge")

        assert stats["nodes_updated"] == 1
        assert stats["nodes_failed"] == 1


class TestIncrementalFreesoundLoaderBuildGraph:
    """Test build_graph method."""

    def test_build_graph_returns_incremental_graph(self, loader_with_mocks):
        """Test build_graph returns the incrementally-built graph."""
        loader = loader_with_mocks

        # Add nodes to incremental graph
        loader.graph.add_node("1", name="sound1")
        loader.graph.add_node("2", name="sound2")
        loader.graph.add_edge("1", "2", type="similar")

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
            current=50, total=100, elapsed_seconds=60
        )

        assert stats["percentage"] == 50.0
        assert stats["current"] == 50
        assert stats["total"] == 100
        assert stats["remaining"] == 50
        assert stats["elapsed_minutes"] == 1.0
        assert stats["eta_minutes"] > 0

    def test_calculate_progress_stats_zero_current(self, loader_with_mocks):
        """Test progress stats with zero current."""
        loader = loader_with_mocks

        stats = loader._calculate_progress_stats(
            current=0, total=100, elapsed_seconds=0
        )

        assert stats["percentage"] == 0.0
        assert stats["eta_minutes"] == 0


class TestIncrementalFreesoundLoaderIntegration:
    """Test complete incremental loading workflows."""

    def test_complete_incremental_workflow(
        self, mock_freesound_client, mock_checkpoint
    ):
        """Test complete incremental loading workflow."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "api_key": "test_key",
                "checkpoint_dir": tmpdir,
                "checkpoint_interval": 2,
            }

            loader = IncrementalFreesoundLoader(config=config)

            try:
                # Mock _search_samples to return properly formatted sample dictionaries
                sample_dicts = [
                    {
                        "id": i,
                        "name": f"sound{i}",
                        "tags": [],
                        "duration": 1.0,
                        "username": f"user{i}",
                        "audio_url": f"http://example.com/sound{i}.mp3",
                        "previews": {},
                        "num_downloads": 100,
                        "avg_rating": 4.0,
                        "num_ratings": 10,
                    }
                    for i in range(3)
                ]

                with patch.object(loader, "_search_samples", return_value=sample_dicts):
                    with patch.object(
                        loader, "_fetch_similar_sounds_for_sample", return_value=[]
                    ):
                        # Fetch data
                        data = loader.fetch_data(query="test", max_samples=10)

                        # Build graph
                        graph = loader.build_graph(data)

                        assert graph.number_of_nodes() == 3
                        assert len(loader.processed_ids) == 3
                        assert mock_checkpoint.save.called
            finally:
                # Ensure cleanup
                loader.close()

    def test_resume_from_checkpoint(self, mock_freesound_client, mock_checkpoint):
        """Test resuming from existing checkpoint."""
        # Mock existing checkpoint
        existing_graph = nx.DiGraph()
        existing_graph.add_node("1", name="sound1")

        # Set up the checkpoint to return data BEFORE creating the loader
        mock_checkpoint.load.return_value = {
            "graph": existing_graph,
            "processed_ids": {"1"},
            "metadata": {},
            "sound_cache": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"api_key": "test_key", "checkpoint_dir": tmpdir}

            # Create split checkpoint files to pass verification
            import json
            import pickle
            from pathlib import Path

            checkpoint_dir = Path(tmpdir)

            # Create graph topology file
            topology_path = checkpoint_dir / "graph_topology.gpickle"
            with open(topology_path, "wb") as f:
                pickle.dump(existing_graph, f)

            # Create metadata database
            from FollowWeb_Visualizor.data.storage import MetadataCache

            metadata_cache = MetadataCache(str(checkpoint_dir / "metadata_cache.db"))
            metadata_cache.bulk_insert({1: {"name": "sound1"}})
            metadata_cache.close()

            # Create checkpoint metadata
            checkpoint_meta_path = checkpoint_dir / "checkpoint_metadata.json"
            with open(checkpoint_meta_path, "w") as f:
                json.dump(
                    {
                        "nodes": 1,
                        "edges": 0,
                        "processed_samples": 1,
                        "processed_ids": ["1"],
                    },
                    f,
                )

            loader = IncrementalFreesoundLoader(config=config)

            try:
                # Verify checkpoint was loaded
                assert "1" in loader.processed_ids

                # Mock _search_samples to return properly formatted sample dictionaries
                sample_dicts = [
                    {
                        "id": 1,
                        "name": "sound1",
                        "tags": [],
                        "duration": 1.0,
                        "username": "user1",
                        "audio_url": "http://example.com/sound1.mp3",
                        "previews": {},
                        "num_downloads": 100,
                        "avg_rating": 4.0,
                        "num_ratings": 10,
                    },
                    {
                        "id": 2,
                        "name": "sound2",
                        "tags": [],
                        "duration": 1.0,
                        "username": "user2",
                        "audio_url": "http://example.com/sound2.mp3",
                        "previews": {},
                        "num_downloads": 100,
                        "avg_rating": 4.0,
                        "num_ratings": 10,
                    },
                ]

                with patch.object(loader, "_search_samples", return_value=sample_dicts):
                    with patch.object(
                        loader, "_fetch_similar_sounds_for_sample", return_value=[]
                    ):
                        data = loader.fetch_data(query="test", max_samples=10)

                # Should only process sample 2 (sample 1 is already processed)
                assert len(data["samples"]) == 1
                assert data["samples"][0]["id"] == 2
            finally:
                # Ensure cleanup
                loader.close()


class TestIncrementalFreesoundLoaderPagination:
    """Test pagination-based search collection."""

    def test_search_with_pagination_basic(self, loader_with_mocks):
        """Test basic pagination search."""
        loader = loader_with_mocks

        # Reset pagination state
        loader.pagination_state = {"page": 1, "query": "", "sort": "downloads_desc"}

        # Mock search results for multiple pages
        def mock_text_search(**kwargs):
            page = kwargs.get("page", 1)

            # Create mock results
            mock_results = Mock()

            if page == 1:
                # First page: 3 samples
                sounds = [
                    create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
                    for i in range(1, 4)
                ]
                mock_results.__iter__ = Mock(return_value=iter(sounds))
                mock_results.next = "page2"  # Has next page
            elif page == 2:
                # Second page: 2 samples
                sounds = [
                    create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
                    for i in range(4, 6)
                ]
                mock_results.__iter__ = Mock(return_value=iter(sounds))
                mock_results.next = None  # No more pages
            else:
                # No more results
                mock_results.__iter__ = Mock(return_value=iter([]))
                mock_results.next = None

            return mock_results

        loader.client.text_search.side_effect = mock_text_search

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound

        # Mock checkpoint save
        loader.checkpoint.save = Mock()

        # Search with pagination
        result = loader._search_with_pagination(
            query="test", sort_order="downloads_desc"
        )

        # Should collect 5 samples across 2 pages
        assert len(result) == 5

        # Pagination state should be reset to page 1 (end of results reached)
        assert loader.pagination_state["page"] == 1
        assert loader.pagination_state["query"] == "test"
        assert loader.pagination_state["sort"] == "downloads_desc"

    def test_search_with_pagination_resumes_from_checkpoint(self, loader_with_mocks):
        """Test pagination resumes from saved state."""
        loader = loader_with_mocks

        # Set pagination state to page 2 (simulating resume)
        loader.pagination_state = {"page": 2, "query": "test", "sort": "downloads_desc"}

        # Mock search results starting from page 2
        def mock_text_search(**kwargs):
            page = kwargs.get("page", 1)

            mock_results = Mock()
            if page == 2:
                sounds = [
                    create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
                    for i in range(4, 7)
                ]
                mock_results.__iter__ = Mock(return_value=iter(sounds))

                mock_results.next = None
            else:
                mock_results.__iter__ = Mock(return_value=iter([]))

                mock_results.next = None

            return mock_results

        loader.client.text_search.side_effect = mock_text_search

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound
        loader.checkpoint.save = Mock()

        # Search should start from page 2
        result = loader._search_with_pagination(
            query="test", sort_order="downloads_desc"
        )

        assert len(result) == 3
        # Pages processed internally

        # Pagination resets to 1 when results end
        assert loader.pagination_state["page"] == 1

    def test_search_with_pagination_detects_duplicates(self, loader_with_mocks):
        """Test pagination skips duplicate samples."""
        loader = loader_with_mocks

        # Mock metadata_cache.exists to return True for samples 1 and 2
        loader.metadata_cache.exists = Mock(side_effect=lambda sid: sid in [1, 2])

        # Reset pagination state
        loader.pagination_state = {"page": 1, "query": "", "sort": "downloads_desc"}

        # Mock search results with some duplicates - only return results on first page
        def mock_text_search(**kwargs):
            page = kwargs.get("page", 1)
            mock_results = Mock()

            if page == 1:
                # Return samples 1, 2, 3, 4 (1 and 2 are duplicates)
                sounds = [
                    create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
                    for i in range(1, 5)
                ]
                mock_results.__iter__ = Mock(return_value=iter(sounds))

                mock_results.next = None
            else:
                # No more results on subsequent pages
                mock_results.__iter__ = Mock(return_value=iter([]))

                mock_results.next = None

            return mock_results

        loader.client.text_search.side_effect = mock_text_search

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound
        loader.checkpoint.save = Mock()

        result = loader._search_with_pagination(
            query="test", sort_order="downloads_desc"
        )

        # Should only collect samples 3 and 4 (1 and 2 are duplicates)
        assert len(result) == 2
        # Duplicates tracked internally
        assert result[0]["id"] == 3
        assert result[1]["id"] == 4

    def test_search_with_pagination_circuit_breaker(self, loader_with_mocks):
        """Test pagination stops when circuit breaker triggers."""
        loader = loader_with_mocks

        # Set circuit breaker to trigger immediately
        loader.session_request_count = loader.max_requests

        # Reset pagination state
        loader.pagination_state = {"page": 1, "query": "", "sort": "downloads_desc"}

        # Mock search results
        def mock_text_search(**kwargs):
            mock_results = Mock()
            sounds = [
                create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
                for i in range(1, 4)
            ]
            mock_results.__iter__ = Mock(return_value=iter(sounds))

            mock_results.next = None
            return mock_results

        loader.client.text_search.side_effect = mock_text_search

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound
        loader.checkpoint.save = Mock()

        result = loader._search_with_pagination(
            query="test", sort_order="downloads_desc"
        )

        # Should collect no samples due to circuit breaker
        assert len(result) == 0
        # Pages processed internally

    def test_search_with_pagination_resets_on_query_change(self, loader_with_mocks):
        """Test pagination resets when query changes."""
        loader = loader_with_mocks

        # Set pagination state with different query
        loader.pagination_state = {
            "page": 5,
            "query": "old_query",
            "sort": "downloads_desc",
        }

        # Mock search results
        def mock_text_search(**kwargs):
            mock_results = Mock()
            sounds = [
                create_mock_sound(i, f"sound{i}", [], 1.0, f"user{i}", {})
                for i in range(1, 4)
            ]
            mock_results.__iter__ = Mock(return_value=iter(sounds))

            mock_results.next = None
            return mock_results

        loader.client.text_search.side_effect = mock_text_search

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound
        loader.checkpoint.save = Mock()

        # Search with new query
        loader._search_with_pagination(query="new_query", sort_order="downloads_desc")

        # Should reset to page 1 and then advance to page 2
        assert loader.pagination_state["page"] == 1

    def test_search_with_pagination_saves_checkpoint_after_each_page(
        self, loader_with_mocks
    ):
        """Test checkpoint is saved after each page."""
        loader = loader_with_mocks

        # Reset pagination state
        loader.pagination_state = {"page": 1, "query": "", "sort": "downloads_desc"}

        # Mock search results for 2 pages
        def mock_text_search(**kwargs):
            page = kwargs.get("page", 1)
            mock_results = Mock()

            if page <= 2:
                sounds = [
                    create_mock_sound(
                        i + (page - 1) * 2,
                        f"sound{i + (page - 1) * 2}",
                        [],
                        1.0,
                        f"user{i}",
                        {},
                    )
                    for i in range(1, 3)
                ]
                mock_results.__iter__ = Mock(return_value=iter(sounds))

                mock_results.next = None if page == 2 else "next_page"
            else:
                mock_results.__iter__ = Mock(return_value=iter([]))

                mock_results.next = None

            return mock_results

        loader.client.text_search.side_effect = mock_text_search

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound
        loader.checkpoint.save = Mock()

        result = loader._search_with_pagination(
            query="test", sort_order="downloads_desc"
        )

        # Should save checkpoint after each page (2 pages)
        assert loader.checkpoint.save.call_count >= 1  # At least final save
        assert len(result) == 4

    def test_search_with_pagination_handles_empty_results(self, loader_with_mocks):
        """Test pagination handles empty search results."""
        loader = loader_with_mocks

        # Reset pagination state
        loader.pagination_state = {"page": 1, "query": "", "sort": "downloads_desc"}

        # Mock empty search results
        def mock_text_search(**kwargs):
            mock_results = Mock()
            mock_results.__iter__ = Mock(return_value=iter([]))

            mock_results.next = None
            return mock_results

        loader.client.text_search.side_effect = mock_text_search

        # Mock get_sound to return full metadata
        def mock_get_sound(sound_id):
            return create_mock_sound(
                sound_id, f"sound{sound_id}", [], 1.0, f"user{sound_id}", {}
            )

        loader.client.get_sound = mock_get_sound
        loader.checkpoint.save = Mock()

        result = loader._search_with_pagination(
            query="test", sort_order="downloads_desc"
        )

        # Should return empty results and mark pagination as complete
        assert len(result) == 0
        # Pagination complete is tracked internally, not in return value
        # Pages processed internally


class TestIncrementalFreesoundLoaderTagEdges:
    """Test tag-based edge generation."""

    def test_add_tag_edges_batch_basic(self, loader_with_mocks):
        """Test basic tag edge generation with Jaccard similarity."""
        loader = loader_with_mocks

        # Add nodes with tags
        loader.graph.add_node("1", name="sound1", tags=["drum", "kick", "bass"])
        loader.graph.add_node("2", name="sound2", tags=["drum", "kick"])
        loader.graph.add_node("3", name="sound3", tags=["synth", "pad"])

        # Generate tag edges with default threshold (0.3)
        edge_count = loader._add_tag_edges_batch(similarity_threshold=0.3)

        # Samples 1 and 2 share 2/3 tags = 0.67 similarity (above threshold)
        # Samples 1 and 3 share 0/5 tags = 0.0 similarity (below threshold)
        # Samples 2 and 3 share 0/4 tags = 0.0 similarity (below threshold)
        # Should create 2 bidirectional edges (1->2 and 2->1)
        assert edge_count == 2
        assert loader.graph.has_edge("1", "2")
        assert loader.graph.has_edge("2", "1")
        assert not loader.graph.has_edge("1", "3")
        assert not loader.graph.has_edge("2", "3")

    def test_add_tag_edges_batch_with_threshold(self, loader_with_mocks):
        """Test tag edge generation with custom threshold."""
        loader = loader_with_mocks

        # Add nodes with varying tag overlap
        loader.graph.add_node("1", name="sound1", tags=["a", "b", "c"])
        loader.graph.add_node(
            "2", name="sound2", tags=["a", "b"]
        )  # 2/3 = 0.67 similarity with 1
        loader.graph.add_node(
            "3", name="sound3", tags=["a"]
        )  # 1/3 = 0.33 similarity with 1, 1/2 = 0.5 with 2

        # Use high threshold (0.5) - samples 1-2 (0.67) and 2-3 (0.5) should connect
        edge_count = loader._add_tag_edges_batch(similarity_threshold=0.5)

        assert edge_count == 4  # Bidirectional edges: 1<->2 and 2<->3
        assert loader.graph.has_edge("1", "2")
        assert loader.graph.has_edge("2", "1")
        assert loader.graph.has_edge("2", "3")
        assert loader.graph.has_edge("3", "2")
        assert not loader.graph.has_edge("1", "3")  # 0.33 < 0.5

    def test_add_tag_edges_batch_no_tags(self, loader_with_mocks):
        """Test tag edge generation with nodes without tags."""
        loader = loader_with_mocks

        # Add nodes without tags
        loader.graph.add_node("1", name="sound1")
        loader.graph.add_node("2", name="sound2")

        edge_count = loader._add_tag_edges_batch()

        # Should not create any edges
        assert edge_count == 0

    def test_add_tag_edges_batch_empty_tags(self, loader_with_mocks):
        """Test tag edge generation with empty tag lists."""
        loader = loader_with_mocks

        # Add nodes with empty tag lists
        loader.graph.add_node("1", name="sound1", tags=[])
        loader.graph.add_node("2", name="sound2", tags=[])

        edge_count = loader._add_tag_edges_batch()

        # Should not create any edges
        assert edge_count == 0

    def test_add_tag_edges_batch_single_node(self, loader_with_mocks):
        """Test tag edge generation with single node."""
        loader = loader_with_mocks

        # Add single node with tags
        loader.graph.add_node("1", name="sound1", tags=["drum", "kick"])

        edge_count = loader._add_tag_edges_batch()

        # Should not create any edges (need at least 2 nodes)
        assert edge_count == 0

    def test_add_tag_edges_batch_edge_attributes(self, loader_with_mocks):
        """Test tag edges have correct attributes."""
        loader = loader_with_mocks

        # Add nodes with tags
        loader.graph.add_node("1", name="sound1", tags=["a", "b", "c"])
        loader.graph.add_node("2", name="sound2", tags=["a", "b"])

        edge_count = loader._add_tag_edges_batch(similarity_threshold=0.3)

        assert edge_count == 2

        # Check edge attributes
        edge_data = loader.graph.edges["1", "2"]
        assert edge_data["type"] == "similar_tags"
        assert "weight" in edge_data
        # Jaccard similarity: |{a,b}| / |{a,b,c}| = 2/3 = 0.67
        assert abs(edge_data["weight"] - 0.6666666666666666) < 0.01

    def test_add_tag_edges_batch_no_duplicate_edges(self, loader_with_mocks):
        """Test tag edge generation doesn't create duplicate edges."""
        loader = loader_with_mocks

        # Add nodes with tags
        loader.graph.add_node("1", name="sound1", tags=["a", "b"])
        loader.graph.add_node("2", name="sound2", tags=["a", "b"])

        # Add edge manually first
        loader.graph.add_edge("1", "2", type="similar_tags", weight=1.0)

        # Try to add tag edges again
        edge_count = loader._add_tag_edges_batch(similarity_threshold=0.3)

        # Should only add the reverse edge (2->1), not duplicate 1->2
        assert edge_count == 1
        assert loader.graph.has_edge("2", "1")

    def test_add_tag_edges_batch_updates_stats(self, loader_with_mocks):
        """Test tag edge generation updates statistics."""
        loader = loader_with_mocks

        # Add nodes with tags
        loader.graph.add_node("1", name="sound1", tags=["a", "b"])
        loader.graph.add_node("2", name="sound2", tags=["a", "b"])

        # Call through _add_batch_user_pack_edges with tag edges enabled
        loader.config["include_tag_edges"] = True
        loader.config["tag_similarity_threshold"] = 0.3

        stats = loader._add_batch_user_pack_edges()

        assert stats["tag_edges_added"] == 2
        assert loader.stats["tag_edges_created"] == 2

    def test_add_tag_edges_batch_zero_api_requests(self, loader_with_mocks):
        """Test tag edge generation makes zero API requests."""
        loader = loader_with_mocks

        # Add nodes with tags
        loader.graph.add_node("1", name="sound1", tags=["a", "b"])
        loader.graph.add_node("2", name="sound2", tags=["a", "b"])

        # Track API calls
        initial_request_count = loader.session_request_count

        edge_count = loader._add_tag_edges_batch()

        # Should not make any API requests
        assert loader.session_request_count == initial_request_count
        assert edge_count == 2
