"""
Unit tests for Renderer abstract base class.

Tests interface enforcement, metadata methods, and configuration handling.
"""

from typing import Any, Optional

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.types import VisualizationMetrics
from FollowWeb_Visualizor.visualization.renderers.base import Renderer

pytestmark = [pytest.mark.unit, pytest.mark.visualization]


class ConcreteRenderer(Renderer):
    """Concrete implementation of Renderer for testing."""

    def __init__(self, vis_config: dict[str, Any], should_fail: bool = False):
        super().__init__(vis_config)
        self.should_fail = should_fail
        self.generate_called = False
        self.last_graph = None
        self.last_filename = None
        self.last_metrics = None

    def generate_visualization(
        self,
        graph: nx.DiGraph,
        output_filename: str,
        metrics: Optional[VisualizationMetrics] = None,
    ) -> bool:
        """Generate test visualization."""
        self.generate_called = True
        self.last_graph = graph
        self.last_filename = output_filename
        self.last_metrics = metrics

        if self.should_fail:
            return False

        return True


class CustomExtensionRenderer(ConcreteRenderer):
    """Renderer with custom file extension."""

    def get_file_extension(self) -> str:
        return ".svg"


class LargeGraphRenderer(ConcreteRenderer):
    """Renderer that supports large graphs."""

    def supports_large_graphs(self) -> bool:
        return True


class TestRendererInterface:
    """Test Renderer interface enforcement."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that Renderer cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Renderer({})

    def test_concrete_implementation_required(self):
        """Test that subclasses must implement abstract methods."""

        class IncompleteRenderer(Renderer):
            """Renderer missing required methods."""

            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteRenderer({})

    def test_generate_visualization_must_be_implemented(self):
        """Test that generate_visualization must be implemented."""

        class NoGenerateRenderer(Renderer):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            NoGenerateRenderer({})

    def test_concrete_renderer_can_be_instantiated(self):
        """Test that concrete implementation can be instantiated."""
        config = {"width": "100%", "height": "90vh"}
        renderer = ConcreteRenderer(config)

        assert isinstance(renderer, Renderer)
        assert hasattr(renderer, "generate_visualization")
        assert hasattr(renderer, "get_file_extension")
        assert hasattr(renderer, "supports_large_graphs")


class TestRendererGenerateVisualization:
    """Test Renderer generate_visualization method."""

    def test_generate_visualization_called(self):
        """Test that generate_visualization is called correctly."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()
        graph.add_edge(1, 2)

        result = renderer.generate_visualization(graph, "output.html")

        assert renderer.generate_called
        assert result is True

    def test_generate_visualization_receives_graph(self):
        """Test that generate_visualization receives the graph."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()
        graph.add_nodes_from([1, 2, 3])
        graph.add_edges_from([(1, 2), (2, 3)])

        renderer.generate_visualization(graph, "output.html")

        assert renderer.last_graph is graph
        assert renderer.last_graph.number_of_nodes() == 3
        assert renderer.last_graph.number_of_edges() == 2

    def test_generate_visualization_receives_filename(self):
        """Test that generate_visualization receives the filename."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()
        filename = "test_output.html"

        renderer.generate_visualization(graph, filename)

        assert renderer.last_filename == filename

    def test_generate_visualization_receives_metrics(self):
        """Test that generate_visualization receives metrics."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()
        graph.add_edge(1, 2)

        # Create mock metrics (None is acceptable)
        metrics = None

        renderer.generate_visualization(graph, "output.html", metrics=metrics)

        assert renderer.last_metrics is metrics

    def test_generate_visualization_returns_bool(self):
        """Test that generate_visualization returns boolean."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()

        result = renderer.generate_visualization(graph, "output.html")

        assert isinstance(result, bool)

    def test_generate_visualization_can_fail(self):
        """Test that generate_visualization can return False on failure."""
        renderer = ConcreteRenderer({}, should_fail=True)
        graph = nx.DiGraph()

        result = renderer.generate_visualization(graph, "output.html")

        assert result is False


class TestRendererMetadataMethods:
    """Test Renderer metadata methods."""

    def test_get_file_extension_default(self):
        """Test default file extension."""
        renderer = ConcreteRenderer({})

        extension = renderer.get_file_extension()

        assert extension == ".html"

    def test_get_file_extension_custom(self):
        """Test custom file extension."""
        renderer = CustomExtensionRenderer({})

        extension = renderer.get_file_extension()

        assert extension == ".svg"

    def test_supports_large_graphs_default(self):
        """Test default large graph support."""
        renderer = ConcreteRenderer({})

        supports = renderer.supports_large_graphs()

        assert supports is False

    def test_supports_large_graphs_custom(self):
        """Test custom large graph support."""
        renderer = LargeGraphRenderer({})

        supports = renderer.supports_large_graphs()

        assert supports is True

    def test_metadata_methods_return_correct_types(self):
        """Test that metadata methods return correct types."""
        renderer = ConcreteRenderer({})

        extension = renderer.get_file_extension()
        supports = renderer.supports_large_graphs()

        assert isinstance(extension, str)
        assert isinstance(supports, bool)


class TestRendererConfiguration:
    """Test Renderer configuration handling."""

    def test_renderer_accepts_config(self):
        """Test that renderer accepts configuration."""
        config = {
            "width": "100%",
            "height": "90vh",
            "show_labels": True,
            "node_size": 10,
        }
        renderer = ConcreteRenderer(config)

        assert renderer.vis_config == config
        assert renderer.vis_config["width"] == "100%"
        assert renderer.vis_config["show_labels"] is True

    def test_renderer_accepts_empty_config(self):
        """Test that renderer accepts empty configuration."""
        renderer = ConcreteRenderer({})

        assert renderer.vis_config == {}

    def test_renderer_has_logger(self):
        """Test that renderer has logger instance."""
        renderer = ConcreteRenderer({})

        assert hasattr(renderer, "logger")
        assert renderer.logger.name == "ConcreteRenderer"

    def test_renderer_config_accessible(self):
        """Test that configuration is accessible in subclass."""
        config = {"custom_setting": "value"}
        renderer = ConcreteRenderer(config)

        assert "custom_setting" in renderer.vis_config
        assert renderer.vis_config["custom_setting"] == "value"


class TestRendererIntegration:
    """Test Renderer integration scenarios."""

    def test_complete_workflow_with_real_graph(self):
        """Test complete workflow with realistic graph."""
        config = {"width": "100%", "height": "90vh"}
        renderer = ConcreteRenderer(config)

        # Create realistic graph
        graph = nx.DiGraph()
        for i in range(10):
            graph.add_node(i, label=f"Node {i}")
        for i in range(9):
            graph.add_edge(i, i + 1, weight=1.0)

        result = renderer.generate_visualization(graph, "test_output.html")

        assert result is True
        assert renderer.last_graph.number_of_nodes() == 10
        assert renderer.last_graph.number_of_edges() == 9

    def test_empty_graph_handling(self):
        """Test handling of empty graph."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()

        result = renderer.generate_visualization(graph, "empty.html")

        assert result is True
        assert renderer.last_graph.number_of_nodes() == 0

    def test_multiple_renders_independent(self):
        """Test that multiple renders are independent."""
        renderer = ConcreteRenderer({})

        graph1 = nx.DiGraph()
        graph1.add_edge(1, 2)

        graph2 = nx.DiGraph()
        graph2.add_edge("a", "b")

        renderer.generate_visualization(graph1, "output1.html")
        first_graph = renderer.last_graph

        renderer.generate_visualization(graph2, "output2.html")
        second_graph = renderer.last_graph

        assert first_graph is not second_graph
        assert renderer.last_filename == "output2.html"

    def test_renderer_with_metrics(self):
        """Test renderer with visualization metrics."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()
        graph.add_edge(1, 2)

        # Pass None as metrics (acceptable)
        result = renderer.generate_visualization(graph, "output.html", metrics=None)

        assert result is True
        assert renderer.last_metrics is None


class TestRendererErrorHandling:
    """Test Renderer error handling."""

    def test_renderer_handles_invalid_graph_type(self):
        """Test that renderer can handle invalid graph types."""
        renderer = ConcreteRenderer({})

        # Renderer should handle this gracefully or let it fail
        # The implementation decides how to handle invalid input
        try:
            renderer.generate_visualization("not a graph", "output.html")
        except (TypeError, AttributeError):
            # Expected if renderer validates input
            pass

    def test_renderer_handles_none_graph(self):
        """Test that renderer can handle None graph."""
        renderer = ConcreteRenderer({})

        try:
            renderer.generate_visualization(None, "output.html")
        except (TypeError, AttributeError):
            # Expected if renderer validates input
            pass

    def test_renderer_handles_empty_filename(self):
        """Test that renderer can handle empty filename."""
        renderer = ConcreteRenderer({})
        graph = nx.DiGraph()

        # Should accept empty filename (implementation decides validation)
        result = renderer.generate_visualization(graph, "")

        assert isinstance(result, bool)
