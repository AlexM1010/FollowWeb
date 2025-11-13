"""
Unit tests for connectivity analysis module.

Tests calculate_connectivity_metrics() and validate_connectivity() with various
graph structures including connected, disconnected, and isolated node scenarios.
"""

import logging
import sys
from pathlib import Path

import networkx as nx
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "FollowWeb"))

from FollowWeb_Visualizor.analysis.connectivity import (
    calculate_connectivity_metrics,
    validate_connectivity,
)


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.mark.unit
class TestCalculateConnectivityMetrics:
    """Test connectivity metrics calculation."""
    
    def test_fully_connected_graph(self, mock_logger):
        """Test metrics for a fully connected graph."""
        # Create a fully connected graph
        graph = nx.complete_graph(10)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Should have 1 component
        assert metrics['num_components'] == 1
        assert metrics['largest_component_size'] == 10
        assert metrics['largest_component_pct'] == 100.0
        assert metrics['is_connected'] is True
        
        # Complete graph has density = 1.0
        assert metrics['density'] == 1.0
        
        # Complete graph has clustering coefficient = 1.0
        assert metrics['avg_clustering'] == 1.0
    
    def test_disconnected_graph(self, mock_logger):
        """Test metrics for a disconnected graph."""
        # Create a graph with 3 disconnected components
        graph = nx.Graph()
        
        # Component 1: 5 nodes
        graph.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])
        
        # Component 2: 3 nodes
        graph.add_edges_from([(10, 11), (11, 12)])
        
        # Component 3: 2 nodes
        graph.add_edge(20, 21)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Should have 3 components
        assert metrics['num_components'] == 3
        assert metrics['largest_component_size'] == 5
        assert metrics['largest_component_pct'] == 50.0  # 5 out of 10 nodes
        assert metrics['is_connected'] is False
    
    def test_graph_with_isolated_nodes(self, mock_logger):
        """Test metrics for graph with isolated nodes."""
        # Create graph with connected component and isolated nodes
        graph = nx.Graph()
        
        # Connected component: 4 nodes
        graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
        
        # Isolated nodes
        graph.add_nodes_from([10, 11, 12])
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Should have 4 components (1 connected + 3 isolated)
        assert metrics['num_components'] == 4
        assert metrics['largest_component_size'] == 4
        assert metrics['largest_component_pct'] == pytest.approx(57.14, rel=0.01)  # 4 out of 7
        assert metrics['is_connected'] is False
    
    def test_empty_graph(self, mock_logger):
        """Test metrics for empty graph."""
        graph = nx.Graph()
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Empty graph should return zero metrics
        assert metrics['num_components'] == 0
        assert metrics['largest_component_size'] == 0
        assert metrics['largest_component_pct'] == 0.0
        assert metrics['avg_clustering'] == 0.0
        assert metrics['density'] == 0.0
        assert metrics['is_connected'] is False
    
    def test_directed_graph_conversion(self, mock_logger):
        """Test that directed graphs are converted to undirected."""
        # Create directed graph
        graph = nx.DiGraph()
        graph.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 1)])
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Should be treated as connected (undirected view)
        assert metrics['num_components'] == 1
        assert metrics['is_connected'] is True
    
    def test_star_graph_clustering(self, mock_logger):
        """Test clustering coefficient for star graph (should be 0)."""
        # Create star graph (hub with spokes, no triangles)
        graph = nx.star_graph(10)  # 1 center + 10 outer nodes
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Star graph has no triangles, so clustering = 0
        assert metrics['avg_clustering'] == 0.0
        assert metrics['num_components'] == 1
        assert metrics['is_connected'] is True
    
    def test_triangle_graph_clustering(self, mock_logger):
        """Test clustering coefficient for triangle graph (should be 1)."""
        # Create triangle (complete graph of 3 nodes)
        graph = nx.complete_graph(3)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Triangle has perfect clustering
        assert metrics['avg_clustering'] == 1.0
        assert metrics['density'] == 1.0
    
    def test_path_graph_density(self, mock_logger):
        """Test density for path graph."""
        # Create path graph (linear chain)
        graph = nx.path_graph(10)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Path graph has low density
        # Density = 2*edges / (nodes * (nodes-1)) = 2*9 / (10*9) = 0.2
        assert metrics['density'] == pytest.approx(0.2, rel=0.01)
        assert metrics['num_components'] == 1


@pytest.mark.unit
class TestValidateConnectivity:
    """Test connectivity validation."""
    
    def test_validates_connected_graph(self, mock_logger):
        """Test validation of fully connected graph."""
        # Create connected graph
        graph = nx.complete_graph(10)
        
        validation = validate_connectivity(graph, mock_logger)
        
        assert validation['is_connected'] is True
        assert validation['num_components'] == 1
        assert validation['component_sizes'] == [10]
        assert validation['num_isolated_nodes'] == 0
        assert validation['isolated_nodes'] == []
        assert validation['largest_component_pct'] == 100.0
    
    def test_validates_disconnected_graph(self, mock_logger):
        """Test validation of disconnected graph."""
        # Create disconnected graph
        graph = nx.Graph()
        
        # Component 1: 6 nodes
        graph.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)])
        
        # Component 2: 4 nodes
        graph.add_edges_from([(10, 11), (11, 12), (12, 13)])
        
        # Component 3: 2 nodes
        graph.add_edge(20, 21)
        
        validation = validate_connectivity(graph, mock_logger)
        
        assert validation['is_connected'] is False
        assert validation['num_components'] == 3
        assert validation['component_sizes'] == [6, 4, 2]  # Sorted descending
        assert validation['largest_component_pct'] == 50.0  # 6 out of 12
        assert validation['num_isolated_nodes'] == 0
    
    def test_identifies_isolated_nodes(self, mock_logger):
        """Test identification of isolated nodes."""
        # Create graph with isolated nodes
        graph = nx.Graph()
        
        # Connected component
        graph.add_edges_from([(1, 2), (2, 3)])
        
        # Isolated nodes
        graph.add_nodes_from([10, 11, 12, 13])
        
        validation = validate_connectivity(graph, mock_logger)
        
        assert validation['is_connected'] is False
        assert validation['num_components'] == 5  # 1 connected + 4 isolated
        assert validation['num_isolated_nodes'] == 4
        assert set(validation['isolated_nodes']) == {10, 11, 12, 13}
        assert validation['component_sizes'] == [3, 1, 1, 1, 1]
    
    def test_validates_empty_graph(self, mock_logger):
        """Test validation of empty graph."""
        graph = nx.Graph()
        
        validation = validate_connectivity(graph, mock_logger)
        
        assert validation['is_connected'] is False
        assert validation['num_components'] == 0
        assert validation['component_sizes'] == []
        assert validation['num_isolated_nodes'] == 0
        assert validation['isolated_nodes'] == []
        assert validation['largest_component_pct'] == 0.0
    
    def test_validates_directed_graph(self, mock_logger):
        """Test validation of directed graph (converted to undirected)."""
        # Create directed graph
        graph = nx.DiGraph()
        graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
        
        validation = validate_connectivity(graph, mock_logger)
        
        # Should be treated as connected (undirected view)
        assert validation['is_connected'] is True
        assert validation['num_components'] == 1
    
    def test_component_sizes_sorted_descending(self, mock_logger):
        """Test that component sizes are sorted in descending order."""
        # Create graph with components of different sizes
        graph = nx.Graph()
        
        # Component 1: 2 nodes
        graph.add_edge(1, 2)
        
        # Component 2: 5 nodes
        graph.add_edges_from([(10, 11), (11, 12), (12, 13), (13, 14)])
        
        # Component 3: 3 nodes
        graph.add_edges_from([(20, 21), (21, 22)])
        
        # Component 4: 1 node (isolated)
        graph.add_node(30)
        
        validation = validate_connectivity(graph, mock_logger)
        
        # Should be sorted: [5, 3, 2, 1]
        assert validation['component_sizes'] == [5, 3, 2, 1]
        assert validation['largest_component_pct'] == pytest.approx(45.45, rel=0.01)  # 5 out of 11


@pytest.mark.unit
class TestConnectivityWithVariousGraphTypes:
    """Test connectivity analysis with various graph types."""
    
    def test_cycle_graph(self, mock_logger):
        """Test connectivity of cycle graph."""
        # Create cycle graph (ring)
        graph = nx.cycle_graph(10)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        validation = validate_connectivity(graph, mock_logger)
        
        # Cycle is connected
        assert metrics['is_connected'] is True
        assert validation['is_connected'] is True
        assert metrics['num_components'] == 1
        
        # Cycle has no triangles, so clustering = 0
        assert metrics['avg_clustering'] == 0.0
    
    def test_grid_graph(self, mock_logger):
        """Test connectivity of grid graph."""
        # Create 5x5 grid graph
        graph = nx.grid_2d_graph(5, 5)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        validation = validate_connectivity(graph, mock_logger)
        
        # Grid is connected
        assert metrics['is_connected'] is True
        assert validation['is_connected'] is True
        assert metrics['num_components'] == 1
        assert metrics['largest_component_size'] == 25
    
    def test_barbell_graph(self, mock_logger):
        """Test connectivity of barbell graph (two cliques connected by path)."""
        # Create barbell graph (two complete graphs connected by a path)
        graph = nx.barbell_graph(5, 3)  # Two K5 connected by path of length 3
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        validation = validate_connectivity(graph, mock_logger)
        
        # Barbell is connected
        assert metrics['is_connected'] is True
        assert validation['is_connected'] is True
        assert metrics['num_components'] == 1
        
        # Has high clustering due to cliques
        assert metrics['avg_clustering'] > 0.5
    
    def test_random_graph(self, mock_logger):
        """Test connectivity of random graph."""
        # Create Erdos-Renyi random graph with high probability
        graph = nx.erdos_renyi_graph(20, 0.3, seed=42)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        validation = validate_connectivity(graph, mock_logger)
        
        # With p=0.3 and n=20, likely to be connected
        # Just verify metrics are calculated without errors
        assert 'num_components' in metrics
        assert 'is_connected' in validation
        assert metrics['largest_component_size'] <= 20
    
    def test_large_graph_sampling(self, mock_logger):
        """Test that large graphs use sampling for clustering coefficient."""
        # Create a large graph (>10000 nodes) to trigger sampling path
        # Use a sparse graph to keep memory usage reasonable
        graph = nx.erdos_renyi_graph(12000, 0.001, seed=42)
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Verify metrics are calculated
        assert 'avg_clustering' in metrics
        assert 'num_components' in metrics
        assert 'density' in metrics
        assert metrics['avg_clustering'] >= 0.0
        assert metrics['avg_clustering'] <= 1.0
        
        # Verify graph size is correct
        assert graph.number_of_nodes() == 12000
