"""
Unit tests for fail-fast architecture with data preservation.

Tests checkpoint verification, error recovery, and failure flag propagation.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from FollowWeb_Visualizor.data.checkpoint_verifier import CheckpointVerifier
from FollowWeb_Visualizor.utils.failure_handler import FailureHandler
from FollowWeb_Visualizor.utils.github_issue_creator import GitHubIssueCreator


class TestCheckpointVerifier:
    """Test checkpoint verification functionality."""

    def test_verify_all_files_exist(self, tmp_path):
        """Test verification passes when all files exist."""
        import pickle
        import sqlite3

        import networkx as nx

        # Create valid pickle file with a NetworkX graph
        graph = nx.DiGraph()
        graph.add_node(1, name="test")
        with open(tmp_path / "graph_topology.gpickle", "wb") as f:
            pickle.dump(graph, f)

        # Create valid SQLite database with metadata table
        db_path = tmp_path / "metadata_cache.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE metadata (sample_id INTEGER PRIMARY KEY, data TEXT)"
        )
        cursor.execute("INSERT INTO metadata VALUES (1, '{}')")
        conn.commit()
        conn.close()

        (tmp_path / "checkpoint_metadata.json").write_text('{"nodes": 100}')

        verifier = CheckpointVerifier(tmp_path)
        success, message = verifier.verify_checkpoint_files()

        assert success is True
        assert "verified" in message.lower()

    def test_verify_missing_topology(self, tmp_path):
        """Test verification fails when topology file is missing."""
        # Create only some files
        (tmp_path / "metadata_cache.db").write_bytes(b"test data")
        (tmp_path / "checkpoint_metadata.json").write_text('{"nodes": 100}')

        verifier = CheckpointVerifier(tmp_path)
        success, message = verifier.verify_checkpoint_files()

        assert success is False
        assert "graph_topology.gpickle" in message

    def test_verify_empty_file(self, tmp_path):
        """Test verification fails when file is empty."""
        # Create files but one is empty
        (tmp_path / "graph_topology.gpickle").write_bytes(b"test data")
        (tmp_path / "metadata_cache.db").write_bytes(b"")  # Empty
        (tmp_path / "checkpoint_metadata.json").write_text('{"nodes": 100}')

        verifier = CheckpointVerifier(tmp_path)
        success, message = verifier.verify_checkpoint_files()

        assert success is False
        assert "empty" in message.lower()

    def test_verify_invalid_json(self, tmp_path):
        """Test verification fails when JSON is invalid."""
        # Create files but JSON is invalid
        (tmp_path / "graph_topology.gpickle").write_bytes(b"test data")
        (tmp_path / "metadata_cache.db").write_bytes(b"test data")
        (tmp_path / "checkpoint_metadata.json").write_text("invalid json{")

        verifier = CheckpointVerifier(tmp_path)
        success, message = verifier.verify_checkpoint_files()

        assert success is False
        assert "invalid" in message.lower()


class TestFailureHandler:
    """Test failure flag management."""

    def test_set_and_check_failure_flag(self, tmp_path):
        """Test setting and checking failure flags."""
        handler = FailureHandler(tmp_path)

        # Initially no flag
        flag_exists, flag_data = handler.check_failure_flag()
        assert flag_exists is False

        # Set flag
        handler.set_failure_flag(
            workflow_name="test-workflow",
            run_id="12345",
            error_message="Test error",
            data_preserved=True,
        )

        # Check flag exists
        flag_exists, flag_data = handler.check_failure_flag()
        assert flag_exists is True
        assert flag_data["workflow_name"] == "test-workflow"
        assert flag_data["run_id"] == "12345"
        assert flag_data["error_message"] == "Test error"
        assert flag_data["data_preserved"] is True

    def test_clear_failure_flag(self, tmp_path):
        """Test clearing failure flags."""
        handler = FailureHandler(tmp_path)

        # Set flag
        handler.set_failure_flag(
            workflow_name="test-workflow", run_id="12345", error_message="Test error"
        )

        # Clear flag
        handler.clear_failure_flag()

        # Check flag is gone
        flag_exists, _ = handler.check_failure_flag()
        assert flag_exists is False

    def test_get_skip_reason(self, tmp_path):
        """Test getting formatted skip reason."""
        handler = FailureHandler(tmp_path)

        # No flag initially
        skip_reason = handler.get_skip_reason()
        assert skip_reason is None

        # Set flag
        handler.set_failure_flag(
            workflow_name="test-workflow",
            run_id="12345",
            error_message="Test error",
            data_preserved=True,
        )

        # Get skip reason
        skip_reason = handler.get_skip_reason()
        assert skip_reason is not None
        assert "test-workflow" in skip_reason
        assert "Test error" in skip_reason
        assert "Data preserved: True" in skip_reason


class TestGitHubIssueCreator:
    """Test GitHub issue creation."""

    def test_create_failure_issue(self, tmp_path, monkeypatch):
        """Test creating failure issue."""
        # Set environment variables
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "test/repo")

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        creator = GitHubIssueCreator()

        success, message = creator.create_failure_issue(
            title="Test Failure",
            error_message="Test error occurred",
            workflow_name="test-workflow",
            run_id="12345",
            checkpoint_status={"nodes": 100, "edges": 200, "saved_to_permanent": True},
        )

        assert success is True

        # Check issue file was created
        issue_file = tmp_path / "data/freesound_library/pending_issue.json"
        assert issue_file.exists()

        # Verify issue content
        with open(issue_file) as f:
            issue_data = json.load(f)

        assert issue_data["title"] == "Test Failure"
        assert "Test error occurred" in issue_data["body"]
        assert "test-workflow" in issue_data["body"]

    def test_build_issue_body(self):
        """Test building issue body with all sections."""
        creator = GitHubIssueCreator()

        body = creator._build_issue_body(
            error_message="Test error",
            workflow_name="test-workflow",
            run_id="12345",
            checkpoint_status={"nodes": 100, "saved": True},
            logs="Test log content",
            additional_info={"key": "value"},
        )

        assert "Test error" in body
        assert "test-workflow" in body
        assert "12345" in body
        assert "nodes" in body
        assert "Test log content" in body
        assert "key" in body


class TestFailFastIntegration:
    """Integration tests for fail-fast behavior."""

    @pytest.mark.integration
    def test_checkpoint_save_verification_failure(self, tmp_path):
        """Test that checkpoint save verification triggers fail-fast."""
        from FollowWeb_Visualizor.data.loaders import IncrementalFreesoundLoader

        # Create loader with temp checkpoint dir
        config = {"checkpoint_dir": str(tmp_path), "api_key": "test-key"}

        loader = IncrementalFreesoundLoader(config)

        # Add some data to graph
        loader.graph.add_node("1", name="test")

        # Mock the file writing to create incomplete checkpoint
        original_open = open

        def mock_open(*args, **kwargs):
            # Allow JSON file to be written
            if "checkpoint_metadata.json" in str(args[0]):
                return original_open(*args, **kwargs)
            # Block other files to simulate incomplete save
            if "graph_topology.gpickle" in str(args[0]):
                raise OSError("Simulated write failure")
            return original_open(*args, **kwargs)

        # This should raise RuntimeError due to verification failure
        with patch("builtins.open", side_effect=mock_open):
            with pytest.raises((RuntimeError, IOError)):
                loader._save_checkpoint({"test": "data"})

    @pytest.mark.integration
    def test_error_recovery_preserves_data(self, tmp_path, monkeypatch):
        """Test that error recovery saves data before failing."""
        from FollowWeb_Visualizor.data.loaders import IncrementalFreesoundLoader

        # Set environment variables
        monkeypatch.setenv("GITHUB_WORKFLOW", "test-workflow")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")

        # Create loader
        config = {"checkpoint_dir": str(tmp_path), "api_key": "test-key"}

        loader = IncrementalFreesoundLoader(config)

        # Add some test data to graph
        loader.graph.add_node("1", name="test")

        # Mock backup manager to avoid actual backup
        loader.backup_manager = MagicMock()
        loader.backup_manager.create_backup.return_value = True

        # Call error recovery
        test_error = ValueError("Test error")

        with pytest.raises(RuntimeError, match="Critical error"):
            loader.handle_error_with_data_preservation(
                error=test_error, context="test context"
            )

        # Verify failure flag was set
        flag_file = tmp_path / "failure_flags.json"
        assert flag_file.exists()

        with open(flag_file) as f:
            flag_data = json.load(f)

        assert flag_data["workflow_name"] == "test-workflow"
        assert flag_data["error_message"] == "test context: Test error"
