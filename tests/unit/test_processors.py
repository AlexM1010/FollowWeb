"""
Unit tests for graph processors module.

Tests GraphProcessor class methods including reciprocal filtering,
ego-alter graph creation, and k-core pruning operations.
"""

import logging
import sys
from pathlib import Path

import networkx as nx
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "FollowWeb"))

from FollowWeb_Visualizor.data.processors import GraphProcessor


@pytest.fixture
def processor():
    """Fixture providing GraphProcessor instance."""
    return GraphProcessor()


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.mark.unit
class TestFilterByReciprocity:
    """Test reciprocal edge filtering."""
    
    def test_filters_reciprocal_edges(self, processor):
        """Test that only mutual connections are kept."""
        # Create graph with some reciprocal and some one-way edges
        graph = nx.DiGraph()
        
        # Reciprocal edges
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        
        graph.add_edge("C", "D")
        graph.add_edge("D", "C")
        
        # One-way edges (should be removed)
        graph.add_edge("E", "F")
        graph.add_edge("G", "H")
        
        result = processor.filter_by_reciprocity(graph)
        
        # Should only have reciprocal edges
        assert result.number_of_nodes() == 4  # A, B, C, D
        assert result.number_of_edges() == 4  # A<->B, C<->D
        assert result.has_edge("A", "B")
        assert result.has_edge("B", "A")
        assert result.has_edge("C", "D")
        assert result.has_edge("D", "C")
        assert not result.has_node("E")
        assert not result.has_node("F")
    
    def test_empty_graph(self, processor):
        """Test filtering empty graph."""
        graph = nx.DiGraph()
        result = processor.filter_by_reciprocity(graph)
        
        assert result.number_of_nodes() == 0
        assert result.number_of_edges() == 0
    
    def test_no_reciprocal_edges(self, processor):
        """Test graph with no mutual connections."""
        graph = nx.DiGraph()
        
        # All one-way edges
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        
        result = processor.filter_by_reciprocity(graph)
        
        # Should return empty graph
        assert result.number_of_nodes() == 0
        assert result.number_of_edges() == 0
    
    def test_all_reciprocal_edges(self, processor):
        """Test graph where all edges are mutual."""
        graph = nx.DiGraph()
        
        # All reciprocal
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        graph.add_edge("B", "C")
        graph.add_edge("C", "B")
        graph.add_edge("C", "A")
        graph.add_edge("A", "C")
        
        result = processor.filter_by_reciprocity(graph)
        
        # Should keep all nodes and edges
        assert result.number_of_nodes() == 3
        assert result.number_of_edges() == 6
    
    def test_removes_isolated_nodes(self, processor):
        """Test that nodes with no reciprocal edges are removed."""
        graph = nx.DiGraph()
        
        # Reciprocal pair
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        
        # Node with only outgoing edges (will become isolated)
        graph.add_edge("C", "A")
        graph.add_edge("C", "B")
        
        result = processor.filter_by_reciprocity(graph)
        
        # C should be removed as it has no reciprocal edges
        assert result.number_of_nodes() == 2  # Only A and B
        assert not result.has_node("C")


@pytest.mark.unit
class TestCreateEgoAlterGraph:
    """Test ego-alter graph creation."""
    
    def test_creates_alter_graph(self, processor):
        """Test basic ego-alter graph creation."""
        graph = nx.DiGraph()
        
        # Ego is "user1"
        # Followers of ego
        graph.add_edge("follower1", "user1")
        graph.add_edge("follower2", "user1")
        
        # Following of ego
        graph.add_edge("user1", "following1")
        graph.add_edge("user1", "following2")
        
        # Connections between alters
        graph.add_edge("follower1", "following1")
        graph.add_edge("following1", "follower2")
        
        result = processor.create_ego_alter_graph(graph, "user1")
        
        # Should have 3 alters (following2 is isolated and removed)
        assert result.number_of_nodes() == 3
        # Should have connections between alters
        assert result.has_edge("follower1", "following1")
        assert result.has_edge("following1", "follower2")
        # Should not have ego node
        assert not result.has_node("user1")
        # following2 should be removed as it's isolated
        assert not result.has_node("following2")
    
    def test_ego_not_in_graph(self, processor):
        """Test error when ego node doesn't exist."""
        graph = nx.DiGraph()
        graph.add_edge("A", "B")
        
        with pytest.raises(ValueError, match="not found in graph"):
            processor.create_ego_alter_graph(graph, "nonexistent")
    
    def test_empty_ego_username(self, processor):
        """Test error with empty ego username."""
        graph = nx.DiGraph()
        
        with pytest.raises(ValueError, match="non-empty string"):
            processor.create_ego_alter_graph(graph, "")
        
        with pytest.raises(ValueError, match="non-empty string"):
            processor.create_ego_alter_graph(graph, "   ")
    
    def test_invalid_ego_username_type(self, processor):
        """Test error with non-string ego username."""
        graph = nx.DiGraph()
        
        with pytest.raises(ValueError, match="non-empty string"):
            processor.create_ego_alter_graph(graph, None)
    
    def test_ego_with_no_connections(self, processor):
        """Test ego node with no followers or following."""
        graph = nx.DiGraph()
        
        # Isolated ego
        graph.add_node("isolated_ego")
        
        # Other connections
        graph.add_edge("A", "B")
        
        result = processor.create_ego_alter_graph(graph, "isolated_ego")
        
        # Should return empty graph
        assert result.number_of_nodes() == 0
        assert result.number_of_edges() == 0
    
    def test_alters_with_no_connections(self, processor):
        """Test when alters don't connect to each other."""
        graph = nx.DiGraph()
        
        # Ego with followers/following
        graph.add_edge("follower1", "ego")
        graph.add_edge("follower2", "ego")
        graph.add_edge("ego", "following1")
        
        # No connections between alters
        
        result = processor.create_ego_alter_graph(graph, "ego")
        
        # Should return empty graph (all alters are isolated)
        assert result.number_of_nodes() == 0
        assert result.number_of_edges() == 0
    
    def test_complex_alter_network(self, processor):
        """Test with complex network of alter connections."""
        graph = nx.DiGraph()
        
        # Ego connections
        alters = ["A", "B", "C", "D", "E"]
        for alter in alters:
            graph.add_edge("ego", alter)
            graph.add_edge(alter, "ego")
        
        # Complex alter network
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "E")
        graph.add_edge("E", "A")
        graph.add_edge("A", "C")
        graph.add_edge("B", "D")
        
        result = processor.create_ego_alter_graph(graph, "ego")
        
        # Should have all alters
        assert result.number_of_nodes() == 5
        # Should have all alter connections
        assert result.number_of_edges() == 7
        assert not result.has_node("ego")


@pytest.mark.unit
class TestPruneGraph:
    """Test k-core graph pruning."""
    
    def test_prunes_low_degree_nodes(self, processor):
        """Test that nodes below degree threshold are removed."""
        graph = nx.DiGraph()
        
        # Create a graph with varying degrees
        # High degree nodes
        graph.add_edges_from([
            ("A", "B"), ("B", "A"),
            ("A", "C"), ("C", "A"),
            ("B", "C"), ("C", "B"),
        ])
        
        # Low degree node
        graph.add_edge("D", "A")
        
        result = processor.prune_graph(graph, min_degree=2)
        
        # D should be removed (degree 1)
        assert not result.has_node("D")
        # A, B, C should remain
        assert result.has_node("A")
        assert result.has_node("B")
        assert result.has_node("C")
    
    def test_min_degree_zero(self, processor):
        """Test that min_degree=0 returns original graph."""
        graph = nx.DiGraph()
        graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D")])
        
        result = processor.prune_graph(graph, min_degree=0)
        
        # Should return original graph
        assert result.number_of_nodes() == graph.number_of_nodes()
        assert result.number_of_edges() == graph.number_of_edges()
    
    def test_negative_min_degree(self, processor):
        """Test that negative min_degree returns original graph."""
        graph = nx.DiGraph()
        graph.add_edges_from([("A", "B"), ("B", "C")])
        
        result = processor.prune_graph(graph, min_degree=-1)
        
        # Should return original graph
        assert result.number_of_nodes() == graph.number_of_nodes()
    
    def test_high_min_degree_removes_all(self, processor):
        """Test that very high min_degree can remove all nodes."""
        graph = nx.DiGraph()
        
        # Small graph with low degrees
        graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])
        
        result = processor.prune_graph(graph, min_degree=100)
        
        # Should remove all nodes
        assert result.number_of_nodes() == 0
    
    def test_empty_graph(self, processor):
        """Test pruning empty graph."""
        graph = nx.DiGraph()
        
        result = processor.prune_graph(graph, min_degree=2)
        
        assert result.number_of_nodes() == 0
        assert result.number_of_edges() == 0
    
    def test_complete_graph(self, processor):
        """Test pruning complete graph (all nodes high degree)."""
        # Create complete directed graph
        graph = nx.complete_graph(5, create_using=nx.DiGraph())
        
        result = processor.prune_graph(graph, min_degree=4)
        
        # All nodes should remain (each has degree 8 in directed complete graph)
        assert result.number_of_nodes() == 5
    
    def test_preserves_graph_structure(self, processor):
        """Test that pruning preserves edge relationships."""
        graph = nx.DiGraph()
        
        # Create a core with high connectivity
        graph.add_edges_from([
            ("A", "B"), ("B", "A"),
            ("A", "C"), ("C", "A"),
            ("B", "C"), ("C", "B"),
            ("A", "D"), ("D", "A"),
            ("B", "D"), ("D", "B"),
            ("C", "D"), ("D", "C"),
        ])
        
        # Add peripheral nodes
        graph.add_edge("E", "A")
        graph.add_edge("F", "B")
        
        result = processor.prune_graph(graph, min_degree=4)
        
        # Core nodes should remain with their connections
        assert result.has_edge("A", "B")
        assert result.has_edge("B", "C")
        assert result.has_edge("C", "D")


@pytest.mark.unit
class TestGraphProcessorInitialization:
    """Test GraphProcessor initialization."""
    
    def test_initialization(self):
        """Test that GraphProcessor initializes correctly."""
        processor = GraphProcessor()
        
        assert processor is not None
        assert hasattr(processor, 'logger')
        assert isinstance(processor.logger, logging.Logger)
    
    def test_multiple_instances(self):
        """Test that multiple instances can be created."""
        processor1 = GraphProcessor()
        processor2 = GraphProcessor()
        
        assert processor1 is not processor2
        assert processor1.logger is not None
        assert processor2.logger is not None
