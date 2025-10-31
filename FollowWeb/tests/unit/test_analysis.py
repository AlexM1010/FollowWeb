"""
Unit tests for network analysis module.

Tests graph loading, filtering, pruning, network analysis algorithms,
path analysis, and fame analysis functionality.
"""

import os

import networkx as nx
import pytest

from FollowWeb_Visualizor.analysis import (
    FameAnalyzer,
    NetworkAnalyzer,
    PathAnalyzer,
)
from FollowWeb_Visualizor.data.loaders import GraphLoader


class TestGraphLoader:
    """Test GraphLoader functionality."""

    def test_load_valid_json(self, sample_data_file: str, sample_data_exists: bool):
        """Test loading valid JSON data."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() > 0
        assert graph.number_of_edges() > 0

    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        loader = GraphLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_from_json("non_existent_file.json")

    def test_load_invalid_json(self, invalid_json_file: str):
        """Test loading invalid JSON file."""
        loader = GraphLoader()

        with pytest.raises(ValueError, match="Invalid JSON format"):
            loader.load_from_json(invalid_json_file)

    def test_load_empty_json(self, empty_json_file: str):
        """Test loading empty JSON file."""
        loader = GraphLoader()
        graph = loader.load_from_json(empty_json_file)

        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_load_invalid_json_structure(self, temp_file_factory):
        """Test loading JSON with invalid structure."""
        # Create temporary file with invalid structure using fixture
        temp_file = temp_file_factory(suffix=".json", content='{"not": "a list"}')

        loader = GraphLoader()
        with pytest.raises(ValueError, match="JSON root must be a list"):
            loader.load_from_json(str(temp_file))

    def test_filter_by_reciprocity(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test reciprocal edge filtering."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        reciprocal_graph = loader.filter_by_reciprocity(graph)

        assert isinstance(reciprocal_graph, nx.DiGraph)
        # All edges should be reciprocal
        for u, v in reciprocal_graph.edges():
            assert reciprocal_graph.has_edge(v, u)

    def test_filter_empty_graph_reciprocity(self):
        """Test reciprocal filtering on empty graph."""
        loader = GraphLoader()
        empty_graph = nx.DiGraph()

        result = loader.filter_by_reciprocity(empty_graph)

        assert isinstance(result, nx.DiGraph)
        assert result.number_of_nodes() == 0
        assert result.number_of_edges() == 0

    def test_create_ego_alter_graph_valid(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test ego-alter graph creation with valid ego."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        if graph.number_of_nodes() == 0:
            pytest.skip("No nodes in sample data")

        # Get a node that exists in the graph
        ego_node = list(graph.nodes())[0]

        alter_graph = loader.create_ego_alter_graph(graph, ego_node)

        assert isinstance(alter_graph, nx.DiGraph)
        # Ego should not be in the alter graph
        assert ego_node not in alter_graph.nodes()

    def test_create_ego_alter_graph_invalid_ego(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test ego-alter graph creation with invalid ego."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        with pytest.raises(ValueError, match="ego node.*not found in graph"):
            loader.create_ego_alter_graph(graph, "non_existent_user")

    def test_create_ego_alter_graph_empty_ego(self):
        """Test ego-alter graph creation with empty ego username."""
        loader = GraphLoader()
        graph = nx.DiGraph()

        with pytest.raises(ValueError, match="Ego username must be a non-empty string"):
            loader.create_ego_alter_graph(graph, "")

    def test_prune_graph_valid_k(self, sample_data_file: str, sample_data_exists: bool):
        """Test graph pruning with valid k-value."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        original_nodes = graph.number_of_nodes()
        pruned_graph = loader.prune_graph(graph, 2)

        assert isinstance(pruned_graph, nx.DiGraph)
        assert pruned_graph.number_of_nodes() <= original_nodes

    def test_prune_graph_zero_k(self, sample_data_file: str, sample_data_exists: bool):
        """Test graph pruning with k=0."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        pruned_graph = loader.prune_graph(graph, 0)

        # Should return original graph for k=0
        assert pruned_graph.number_of_nodes() == graph.number_of_nodes()

    def test_prune_graph_negative_k(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test graph pruning with negative k-value."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        pruned_graph = loader.prune_graph(graph, -1)

        # Should return original graph for negative k
        assert pruned_graph.number_of_nodes() == graph.number_of_nodes()


class TestNetworkAnalyzer:
    """Test NetworkAnalyzer functionality."""

    def test_analyze_network_valid_graph(
        self, small_test_data: str, test_data_exists: bool
    ):
        """Test network analysis on valid graph."""
        if not test_data_exists:
            pytest.skip("Test data files not available")

        from FollowWeb_Visualizor.data.loaders import GraphLoader

        loader = GraphLoader()
        graph = loader.load_from_json(small_test_data)

        if graph.number_of_nodes() < 2:
            pytest.skip("Need at least 2 nodes for analysis")

        analyzer = NetworkAnalyzer()
        analyzed_graph = analyzer.analyze_network(graph)

        assert isinstance(analyzed_graph, nx.Graph)

        # Check that analysis attributes were added
        if analyzed_graph.number_of_nodes() > 0:
            sample_node = list(analyzed_graph.nodes(data=True))[0]
            node_attrs = sample_node[1]

            assert "community" in node_attrs
            assert "degree" in node_attrs
            assert "betweenness" in node_attrs
            assert "eigenvector" in node_attrs

    def test_analyze_network_empty_graph(self):
        """Test network analysis on empty graph."""
        analyzer = NetworkAnalyzer()
        empty_graph = nx.DiGraph()

        result = analyzer.analyze_network(empty_graph)

        assert isinstance(result, nx.Graph)
        assert result.number_of_nodes() == 0

    def test_analyze_network_single_node(self):
        """Test network analysis on single node graph."""
        analyzer = NetworkAnalyzer()
        single_graph = nx.DiGraph()
        single_graph.add_node("single_node")

        result = analyzer.analyze_network(single_graph)

        # Should skip analysis for graphs with < 2 nodes
        assert isinstance(result, nx.Graph)
        assert result.number_of_nodes() == 1


class TestPathAnalyzer:
    """Test PathAnalyzer functionality."""

    def test_analyze_path_lengths_valid_graph(
        self, small_test_data: str, test_data_exists: bool
    ):
        """Test path length analysis on valid graph."""
        if not test_data_exists:
            pytest.skip("Test data files not available")

        from FollowWeb_Visualizor.data.loaders import GraphLoader

        loader = GraphLoader()
        graph = loader.load_from_json(small_test_data)

        if graph.number_of_nodes() < 2:
            pytest.skip("Need at least 2 nodes for path analysis")

        analyzer = PathAnalyzer()
        results = analyzer.analyze_path_lengths(graph)

        assert isinstance(results, dict)
        if results:  # If analysis was performed
            assert "average_path_length" in results
            assert "diameter" in results
            assert "total_pairs" in results
            assert "path_distribution" in results

    def test_analyze_path_lengths_empty_graph(self):
        """Test path length analysis on empty graph."""
        analyzer = PathAnalyzer()
        empty_graph = nx.DiGraph()

        results = analyzer.analyze_path_lengths(empty_graph)

        assert isinstance(results, dict)
        assert len(results) == 0  # Should return empty dict

    def test_get_contact_path_valid_nodes(self):
        """Test contact path finding with valid nodes."""
        analyzer = PathAnalyzer()

        # Create simple test graph with path from C to A (target to ego)
        graph = nx.DiGraph()
        graph.add_edges_from([("C", "B"), ("B", "A")])

        path = analyzer.get_contact_path(graph, "A", "C")  # ego="A", target="C"

        assert path == ["C", "B", "A"]  # Path from target to ego

    def test_get_contact_path_no_path(self):
        """Test contact path finding with no path."""
        analyzer = PathAnalyzer()

        # Create disconnected graph
        graph = nx.DiGraph()
        graph.add_node("A")
        graph.add_node("B")

        path = analyzer.get_contact_path(graph, "A", "B")

        assert path is None

    def test_get_contact_path_invalid_nodes(self):
        """Test contact path finding with invalid nodes."""
        analyzer = PathAnalyzer()
        graph = nx.DiGraph()
        graph.add_node("A")

        path = analyzer.get_contact_path(graph, "A", "non_existent")

        assert path is None

    def test_print_detailed_contact_path_valid(self):
        """Test detailed contact path printing with valid path."""
        analyzer = PathAnalyzer()

        # Create simple test graph with path from C to A (target to ego)
        graph = nx.DiGraph()
        graph.add_edges_from([("C", "B"), ("B", "A")])

        result = analyzer.print_detailed_contact_path(
            graph, "A", "C"
        )  # ego="A", target="C"

        assert result is True

    def test_print_detailed_contact_path_no_path(self):
        """Test detailed contact path printing with no path."""
        analyzer = PathAnalyzer()

        # Create disconnected graph
        graph = nx.DiGraph()
        graph.add_node("A")
        graph.add_node("B")

        result = analyzer.print_detailed_contact_path(graph, "A", "B")

        assert result is False


class TestFameAnalyzer:
    """Test FameAnalyzer functionality."""

    def test_find_famous_accounts_valid_graph(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test fame analysis on valid graph."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.data.loaders import GraphLoader

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        analyzer = FameAnalyzer()
        unreachable, reachable = analyzer.find_famous_accounts(graph, 5, 2.0)

        assert isinstance(unreachable, list)
        assert isinstance(reachable, list)

        # Check structure of results
        for account in unreachable + reachable:
            assert "username" in account
            assert "followers_in_network" in account
            assert "following_in_network" in account
            assert "ratio" in account

    def test_find_famous_accounts_empty_graph(self):
        """Test fame analysis on empty graph."""
        analyzer = FameAnalyzer()
        empty_graph = nx.DiGraph()

        unreachable, reachable = analyzer.find_famous_accounts(empty_graph, 5, 2.0)

        assert isinstance(unreachable, list)
        assert isinstance(reachable, list)
        assert len(unreachable) == 0
        assert len(reachable) == 0

    def test_find_famous_accounts_high_thresholds(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test fame analysis with high thresholds."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.data.loaders import GraphLoader

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        analyzer = FameAnalyzer()
        # Use very high thresholds
        unreachable, reachable = analyzer.find_famous_accounts(graph, 10000, 100.0)

        # Should find very few or no accounts
        assert isinstance(unreachable, list)
        assert isinstance(reachable, list)

    def test_find_famous_accounts_zero_thresholds(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test fame analysis with zero thresholds."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.data.loaders import GraphLoader

        loader = GraphLoader()
        graph = loader.load_from_json(sample_data_file)

        analyzer = FameAnalyzer()
        unreachable, reachable = analyzer.find_famous_accounts(graph, 0, 0.0)

        # Should find many accounts with zero thresholds
        assert isinstance(unreachable, list)
        assert isinstance(reachable, list)

    def test_find_famous_accounts_sorting(self):
        """Test that famous accounts are properly sorted."""
        analyzer = FameAnalyzer()

        # Create test graph with known structure
        graph = nx.DiGraph()
        graph.add_edges_from(
            [
                ("follower1", "famous1"),
                ("follower2", "famous1"),
                ("follower3", "famous1"),
                ("follower1", "famous2"),
                ("follower2", "famous2"),
                ("famous2", "someone"),
            ]
        )

        unreachable, reachable = analyzer.find_famous_accounts(graph, 2, 2.0)

        # famous1 should be unreachable (follows nobody) with ratio inf
        # famous2 should be reachable (follows someone) with ratio 2.0

        if unreachable:
            # Should be sorted by ratio (desc), then followers (desc)
            for curr_item, next_item in zip(unreachable, unreachable[1:]):
                curr_ratio = curr_item["ratio"]
                next_ratio = next_item["ratio"]
                assert curr_ratio >= next_ratio

        if reachable:
            # Should be sorted by ratio (desc), then followers (desc)
            for curr_item, next_item in zip(reachable, reachable[1:]):
                curr_ratio = curr_item["ratio"]
                next_ratio = next_item["ratio"]
                assert curr_ratio >= next_ratio

    @pytest.mark.skipif(
        os.name == "nt", reason="Permission error testing not reliable on Windows"
    )
    @pytest.mark.skipif(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_OS") == "Windows",
        reason="Skip permission tests on Windows CI due to permission model differences",
    )
    def test_load_permission_error(self, temp_file_factory):
        """Test handling of permission errors during file loading."""
        import os

        # Create a temporary file and make it unreadable using fixture
        temp_file = temp_file_factory(
            suffix=".json",
            content='[{"user": "test", "followers": [], "following": []}]',
        )

        try:
            # Make file unreadable (Unix/Linux approach)
            os.chmod(temp_file, 0o000)

            loader = GraphLoader()
            with pytest.raises(PermissionError, match="Permission denied reading file"):
                loader.load_from_json(str(temp_file))
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(temp_file, 0o644)
            except BaseException:
                pass  # Ignore permission restore errors
