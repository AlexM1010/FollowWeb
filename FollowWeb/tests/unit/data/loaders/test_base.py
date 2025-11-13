"""
Unit tests for DataLoader abstract base class.

Tests interface enforcement, template method pattern, and validation logic.
"""

from typing import Any, Dict

import networkx as nx
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.data]

from FollowWeb_Visualizor.core.exceptions import DataProcessingError
from FollowWeb_Visualizor.data.loaders.base import DataLoader


class ConcreteLoader(DataLoader):
    """Concrete implementation of DataLoader for testing."""

    def __init__(self, config=None, should_fail_fetch=False, should_fail_build=False):
        super().__init__(config)
        self.should_fail_fetch = should_fail_fetch
        self.should_fail_build = should_fail_build
        self.fetch_called = False
        self.build_called = False

    def fetch_data(self, **params) -> Dict[str, Any]:
        """Fetch test data."""
        self.fetch_called = True

        if self.should_fail_fetch:
            raise DataProcessingError("Fetch failed")

        return {
            "nodes": params.get("nodes", [{"id": 1}, {"id": 2}]),
            "edges": params.get("edges", [{"source": 1, "target": 2}]),
        }

    def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
        """Build test graph."""
        self.build_called = True

        if self.should_fail_build:
            raise DataProcessingError("Build failed")

        graph = nx.DiGraph()
        for node in data["nodes"]:
            graph.add_node(node["id"])
        for edge in data["edges"]:
            graph.add_edge(edge["source"], edge["target"])

        return graph


class InvalidLoader(DataLoader):
    """Invalid loader that returns wrong type from build_graph."""

    def fetch_data(self, **params) -> Dict[str, Any]:
        return {"data": "test"}

    def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
        # Return wrong type to test validation
        return "not a graph"


class TestDataLoaderInterface:
    """Test DataLoader interface enforcement."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that DataLoader cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DataLoader()

    def test_concrete_implementation_required(self):
        """Test that subclasses must implement abstract methods."""

        class IncompleteLoader(DataLoader):
            """Loader missing required methods."""

            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteLoader()

    def test_fetch_data_must_be_implemented(self):
        """Test that fetch_data must be implemented."""

        class NoFetchLoader(DataLoader):
            def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
                return nx.DiGraph()

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            NoFetchLoader()

    def test_build_graph_must_be_implemented(self):
        """Test that build_graph must be implemented."""

        class NoBuildLoader(DataLoader):
            def fetch_data(self, **params) -> Dict[str, Any]:
                return {}

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            NoBuildLoader()

    def test_concrete_loader_can_be_instantiated(self):
        """Test that concrete implementation can be instantiated."""
        loader = ConcreteLoader()
        assert isinstance(loader, DataLoader)
        assert hasattr(loader, "fetch_data")
        assert hasattr(loader, "build_graph")
        assert hasattr(loader, "load")


class TestDataLoaderTemplateMethod:
    """Test DataLoader template method pattern in load()."""

    def test_load_orchestrates_workflow(self):
        """Test that load() orchestrates fetch_data and build_graph."""
        loader = ConcreteLoader()
        graph = loader.load()

        assert loader.fetch_called
        assert loader.build_called
        assert isinstance(graph, nx.DiGraph)

    def test_load_passes_params_to_fetch(self):
        """Test that load() passes parameters to fetch_data."""
        loader = ConcreteLoader()
        custom_nodes = [{"id": "a"}, {"id": "b"}]
        custom_edges = [{"source": "a", "target": "b"}]

        graph = loader.load(nodes=custom_nodes, edges=custom_edges)

        assert graph.has_node("a")
        assert graph.has_node("b")
        assert graph.has_edge("a", "b")

    def test_load_validates_graph(self):
        """Test that load() validates the returned graph."""
        loader = InvalidLoader()

        with pytest.raises(
            DataProcessingError, match="build_graph\\(\\) must return nx.DiGraph"
        ):
            loader.load()

    def test_load_handles_fetch_errors(self):
        """Test that load() handles fetch_data errors."""
        loader = ConcreteLoader(should_fail_fetch=True)

        with pytest.raises(DataProcessingError, match="Fetch failed"):
            loader.load()

    def test_load_handles_build_errors(self):
        """Test that load() handles build_graph errors."""
        loader = ConcreteLoader(should_fail_build=True)

        with pytest.raises(DataProcessingError, match="Build failed"):
            loader.load()

    def test_load_wraps_unexpected_errors(self):
        """Test that load() wraps unexpected errors."""

        class BrokenLoader(DataLoader):
            def fetch_data(self, **params) -> Dict[str, Any]:
                raise ValueError("Unexpected error")

            def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
                return nx.DiGraph()

        loader = BrokenLoader()

        with pytest.raises(DataProcessingError, match="Failed to load data"):
            loader.load()


class TestDataLoaderValidation:
    """Test DataLoader graph validation."""

    def test_validate_accepts_valid_digraph(self):
        """Test that validation accepts valid DiGraph."""
        loader = ConcreteLoader()
        graph = nx.DiGraph()
        graph.add_node(1)
        graph.add_edge(1, 2)

        # Should not raise
        loader._validate_graph(graph)

    def test_validate_rejects_non_digraph(self):
        """Test that validation rejects non-DiGraph types."""
        loader = ConcreteLoader()

        with pytest.raises(
            DataProcessingError, match="build_graph\\(\\) must return nx.DiGraph"
        ):
            loader._validate_graph("not a graph")

        with pytest.raises(
            DataProcessingError, match="build_graph\\(\\) must return nx.DiGraph"
        ):
            loader._validate_graph(nx.Graph())  # Undirected graph

    def test_validate_logs_statistics(self, caplog):
        """Test that validation logs graph statistics."""
        import logging
        caplog.set_level(logging.INFO)
        
        loader = ConcreteLoader()
        graph = nx.DiGraph()
        graph.add_nodes_from([1, 2, 3])
        graph.add_edges_from([(1, 2), (2, 3)])

        loader._validate_graph(graph)

        # Check that statistics were logged
        assert "3 nodes" in caplog.text or "3" in caplog.text
        assert "2 edges" in caplog.text or "2" in caplog.text

    def test_validate_warns_empty_graph(self, caplog):
        """Test that validation warns for empty graphs."""
        loader = ConcreteLoader()
        graph = nx.DiGraph()

        loader._validate_graph(graph)

        assert "no nodes" in caplog.text.lower()

    def test_validate_warns_no_edges(self, caplog):
        """Test that validation warns for graphs with no edges."""
        loader = ConcreteLoader()
        graph = nx.DiGraph()
        graph.add_node(1)

        loader._validate_graph(graph)

        assert "no edges" in caplog.text.lower()


class TestDataLoaderConfiguration:
    """Test DataLoader configuration handling."""

    def test_loader_accepts_config(self):
        """Test that loader accepts configuration."""
        config = {"api_key": "test_key", "max_items": 100}
        loader = ConcreteLoader(config=config)

        assert loader.config == config
        assert loader.config["api_key"] == "test_key"
        assert loader.config["max_items"] == 100

    def test_loader_defaults_empty_config(self):
        """Test that loader defaults to empty config."""
        loader = ConcreteLoader()

        assert loader.config == {}

    def test_loader_has_logger(self):
        """Test that loader has logger instance."""
        loader = ConcreteLoader()

        assert hasattr(loader, "logger")
        assert loader.logger.name == "ConcreteLoader"

    def test_loader_has_cache_manager(self):
        """Test that loader has cache manager."""
        loader = ConcreteLoader()

        assert hasattr(loader, "cache_manager")
        assert loader.cache_manager is not None


class TestDataLoaderIntegration:
    """Test DataLoader integration scenarios."""

    def test_complete_workflow_with_real_graph(self):
        """Test complete workflow with realistic graph data."""
        loader = ConcreteLoader()

        nodes = [{"id": f"user_{i}"} for i in range(10)]
        edges = [{"source": f"user_{i}", "target": f"user_{i+1}"} for i in range(9)]

        graph = loader.load(nodes=nodes, edges=edges)

        assert graph.number_of_nodes() == 10
        assert graph.number_of_edges() == 9
        assert graph.has_node("user_0")
        assert graph.has_edge("user_0", "user_1")

    def test_empty_data_produces_empty_graph(self):
        """Test that empty data produces empty graph."""
        loader = ConcreteLoader()

        graph = loader.load(nodes=[], edges=[])

        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_multiple_loads_independent(self):
        """Test that multiple loads are independent."""
        loader = ConcreteLoader()

        graph1 = loader.load(nodes=[{"id": 1}], edges=[])
        graph2 = loader.load(nodes=[{"id": 2}], edges=[])

        assert graph1.number_of_nodes() == 1
        assert graph2.number_of_nodes() == 1
        assert graph1.has_node(1)
        assert graph2.has_node(2)
        assert not graph1.has_node(2)
        assert not graph2.has_node(1)
