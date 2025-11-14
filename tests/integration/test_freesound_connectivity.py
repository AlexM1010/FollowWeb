"""
Integration tests for Freesound connectivity analysis.

Tests connectivity metrics calculation and storage in checkpoint,
and connectivity validation with warnings for disconnected graphs.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch

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


@pytest.fixture
def freesound_graph_connected():
    """Fixture providing a connected Freesound-like graph."""
    graph = nx.DiGraph()
    
    # Add sample nodes with Freesound-like attributes
    for i in range(1, 21):
        sample_id = 12340 + i
        graph.add_node(
            sample_id,
            name=f'sample{i}.wav',
            type='sample',
            num_downloads=1000 - (i * 20),
            tags=['test', 'sound'],
            username=f'user{i % 5}'
        )
    
    # Add edges to create connected graph
    for i in range(1, 20):
        graph.add_edge(12340 + i, 12340 + i + 1, weight=0.9 - (i * 0.02))
    
    # Add some cross-connections
    graph.add_edge(12341, 12350, weight=0.85)
    graph.add_edge(12345, 12355, weight=0.80)
    graph.add_edge(12350, 12360, weight=0.75)
    
    return graph


@pytest.fixture
def freesound_graph_disconnected():
    """Fixture providing a disconnected Freesound-like graph."""
    graph = nx.DiGraph()
    
    # Component 1: 10 samples
    for i in range(1, 11):
        sample_id = 12340 + i
        graph.add_node(
            sample_id,
            name=f'sample{i}.wav',
            type='sample',
            num_downloads=1000 - (i * 20),
            tags=['test', 'sound'],
            username=f'user{i % 3}'
        )
    
    for i in range(1, 10):
        graph.add_edge(12340 + i, 12340 + i + 1, weight=0.9)
    
    # Component 2: 5 samples (disconnected)
    for i in range(20, 25):
        sample_id = 12340 + i
        graph.add_node(
            sample_id,
            name=f'sample{i}.wav',
            type='sample',
            num_downloads=500 - (i * 10),
            tags=['test', 'isolated'],
            username=f'user{i % 2}'
        )
    
    for i in range(20, 24):
        graph.add_edge(12340 + i, 12340 + i + 1, weight=0.8)
    
    # Component 3: 3 isolated samples
    for i in range(30, 33):
        sample_id = 12340 + i
        graph.add_node(
            sample_id,
            name=f'sample{i}.wav',
            type='sample',
            num_downloads=300,
            tags=['test', 'isolated'],
            username='isolated_user'
        )
    
    return graph


@pytest.mark.integration
class TestFreesoundConnectivityMetrics:
    """Test connectivity metrics calculation for Freesound graphs."""
    
    def test_calculates_metrics_for_connected_graph(
        self,
        freesound_graph_connected,
        mock_logger
    ):
        """Test connectivity metrics for connected Freesound graph."""
        metrics = calculate_connectivity_metrics(
            freesound_graph_connected,
            mock_logger
        )
        
        # Should be fully connected
        assert metrics['is_connected'] is True
        assert metrics['num_components'] == 1
        assert metrics['largest_component_size'] == 20
        assert metrics['largest_component_pct'] == 100.0
        
        # Should have reasonable density and clustering
        assert 0.0 <= metrics['density'] <= 1.0
        assert 0.0 <= metrics['avg_clustering'] <= 1.0
    
    def test_calculates_metrics_for_disconnected_graph(
        self,
        freesound_graph_disconnected,
        mock_logger
    ):
        """Test connectivity metrics for disconnected Freesound graph."""
        metrics = calculate_connectivity_metrics(
            freesound_graph_disconnected,
            mock_logger
        )
        
        # Should be disconnected
        assert metrics['is_connected'] is False
        assert metrics['num_components'] > 1
        
        # Largest component should be the first one (10 nodes)
        assert metrics['largest_component_size'] == 10
        assert metrics['largest_component_pct'] == pytest.approx(55.56, rel=0.01)  # 10 out of 18
    
    def test_metrics_stored_in_checkpoint_format(
        self,
        freesound_graph_connected,
        mock_logger
    ):
        """Test that metrics can be stored in checkpoint metadata format."""
        metrics = calculate_connectivity_metrics(
            freesound_graph_connected,
            mock_logger
        )
        
        # Simulate checkpoint metadata structure
        checkpoint_metadata = {
            'timestamp': '2024-11-10T02:15:30Z',
            'nodes': freesound_graph_connected.number_of_nodes(),
            'edges': freesound_graph_connected.number_of_edges(),
            'connectivity_metrics': {
                'timestamp': '2024-11-10T02:15:30Z',
                'num_components': metrics['num_components'],
                'largest_component_size': metrics['largest_component_size'],
                'largest_component_pct': metrics['largest_component_pct'],
                'avg_clustering': metrics['avg_clustering'],
                'density': metrics['density'],
            }
        }
        
        # Verify structure
        assert 'connectivity_metrics' in checkpoint_metadata
        assert checkpoint_metadata['connectivity_metrics']['num_components'] == 1
        assert checkpoint_metadata['connectivity_metrics']['largest_component_pct'] == 100.0


@pytest.mark.integration
class TestFreesoundConnectivityValidation:
    """Test connectivity validation for Freesound graphs."""
    
    def test_validates_connected_graph_without_warnings(
        self,
        freesound_graph_connected,
        mock_logger,
        caplog
    ):
        """Test validation of connected graph produces no warnings."""
        with caplog.at_level(logging.WARNING):
            validation = validate_connectivity(
                freesound_graph_connected,
                mock_logger
            )
        
        # Should be connected
        assert validation['is_connected'] is True
        assert validation['num_components'] == 1
        assert validation['num_isolated_nodes'] == 0
        
        # Should not produce warnings
        assert len([r for r in caplog.records if r.levelname == 'WARNING']) == 0
    
    def test_validates_disconnected_graph_with_warnings(
        self,
        freesound_graph_disconnected,
        mock_logger,
        caplog
    ):
        """Test validation of disconnected graph produces warnings."""
        with caplog.at_level(logging.WARNING):
            validation = validate_connectivity(
                freesound_graph_disconnected,
                mock_logger
            )
        
        # Should be disconnected
        assert validation['is_connected'] is False
        assert validation['num_components'] > 1
        
        # Should produce warnings about disconnection
        warning_messages = [r.message for r in caplog.records if r.levelname == 'WARNING']
        assert len(warning_messages) > 0
        assert any('not fully connected' in msg for msg in warning_messages)
    
    def test_identifies_isolated_samples(
        self,
        freesound_graph_disconnected,
        mock_logger
    ):
        """Test identification of isolated samples in Freesound graph."""
        validation = validate_connectivity(
            freesound_graph_disconnected,
            mock_logger
        )
        
        # Should identify isolated nodes
        assert validation['num_isolated_nodes'] == 3
        assert len(validation['isolated_nodes']) == 3
        
        # Isolated nodes should be the ones without edges
        isolated_ids = set(validation['isolated_nodes'])
        assert isolated_ids == {12370, 12371, 12372}
    
    def test_component_size_distribution(
        self,
        freesound_graph_disconnected,
        mock_logger
    ):
        """Test component size distribution for disconnected graph."""
        validation = validate_connectivity(
            freesound_graph_disconnected,
            mock_logger
        )
        
        # Should have correct component sizes
        # Component 1: 10 nodes, Component 2: 5 nodes, Component 3: 3 isolated (1 each)
        assert validation['component_sizes'] == [10, 5, 1, 1, 1]
        
        # Largest component should be 55.56% (10 out of 18)
        assert validation['largest_component_pct'] == pytest.approx(55.56, rel=0.01)


@pytest.mark.integration
class TestConnectivityWithRealWorldScenarios:
    """Test connectivity analysis with real-world Freesound scenarios."""
    
    def test_hub_and_spoke_topology(self, mock_logger):
        """Test connectivity of hub-and-spoke topology (common in Freesound)."""
        # Create hub-and-spoke graph (popular sample with many similar samples)
        graph = nx.DiGraph()
        
        # Hub sample (very popular)
        hub_id = 12345
        graph.add_node(
            hub_id,
            name='popular_sample.wav',
            type='sample',
            num_downloads=50000,
            tags=['popular', 'sound'],
            username='popular_user'
        )
        
        # Spoke samples (similar to hub)
        for i in range(1, 21):
            spoke_id = 12400 + i
            graph.add_node(
                spoke_id,
                name=f'similar{i}.wav',
                type='sample',
                num_downloads=1000 + (i * 50),
                tags=['similar', 'sound'],
                username=f'user{i}'
            )
            # Connect spoke to hub
            graph.add_edge(hub_id, spoke_id, weight=0.9 - (i * 0.02))
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        validation = validate_connectivity(graph, mock_logger)
        
        # Should be connected
        assert metrics['is_connected'] is True
        assert validation['is_connected'] is True
        
        # Hub-and-spoke has low clustering (no triangles)
        assert metrics['avg_clustering'] == 0.0
    
    def test_community_structure(self, mock_logger):
        """Test connectivity of graph with community structure."""
        # Create DIRECTED graph (as in real Freesound) with two communities connected by bridge
        graph = nx.DiGraph()
        
        # Community 1: Electronic music samples
        for i in range(1, 11):
            sample_id = 12300 + i
            graph.add_node(
                sample_id,
                name=f'electronic{i}.wav',
                type='sample',
                tags=['electronic', 'music'],
                username=f'electronic_user{i % 3}'
            )
        
        # Dense BIDIRECTIONAL connections within community 1
        for i in range(1, 10):
            # Primary chain
            graph.add_edge(12300 + i, 12300 + i + 1, weight=0.9)
            graph.add_edge(12300 + i + 1, 12300 + i, weight=0.9)
            # Skip connections for density
            if i < 9:
                graph.add_edge(12300 + i, 12300 + i + 2, weight=0.85)
                graph.add_edge(12300 + i + 2, 12300 + i, weight=0.85)
        
        # Community 2: Acoustic samples
        for i in range(1, 11):
            sample_id = 12400 + i
            graph.add_node(
                sample_id,
                name=f'acoustic{i}.wav',
                type='sample',
                tags=['acoustic', 'music'],
                username=f'acoustic_user{i % 3}'
            )
        
        # Dense BIDIRECTIONAL connections within community 2
        for i in range(1, 10):
            # Primary chain
            graph.add_edge(12400 + i, 12400 + i + 1, weight=0.9)
            graph.add_edge(12400 + i + 1, 12400 + i, weight=0.9)
            # Skip connections for density
            if i < 9:
                graph.add_edge(12400 + i, 12400 + i + 2, weight=0.85)
                graph.add_edge(12400 + i + 2, 12400 + i, weight=0.85)
        
        # BIDIRECTIONAL bridge between communities (critical for connectivity)
        graph.add_edge(12305, 12405, weight=0.7)
        graph.add_edge(12405, 12305, weight=0.7)
        
        # Verify it's a directed graph
        assert graph.is_directed()
        assert graph.number_of_nodes() == 20
        
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        validation = validate_connectivity(graph, mock_logger)
        
        # Should be connected via bridge (when viewed as undirected)
        assert metrics['is_connected'] is True
        assert validation['is_connected'] is True
        assert metrics['num_components'] == 1
        assert metrics['largest_component_size'] == 20
        assert metrics['largest_component_pct'] == 100.0
        
        # Should have high clustering due to dense communities
        assert metrics['avg_clustering'] > 0.3
        # Verify density is reasonable for this structure
        assert 0.0 < metrics['density'] < 1.0
    
    def test_growing_graph_connectivity(self, mock_logger):
        """Test connectivity as graph grows (simulating nightly collection).
        
        Note: Uses undirected graph for test simplicity. The connectivity module
        handles directed->undirected conversion internally via get_cached_undirected_graph().
        """
        # Create growing connected graph
        graph = nx.Graph()
        
        # Initial seed sample
        graph.add_node(12345, name='seed.wav', type='sample')
        
        # Track previous sample ID for connections
        prev_sample_id = 12345
        
        # Add samples incrementally (simulating nightly growth)
        for iteration in range(1, 6):
            # Add 5 new samples per iteration
            for i in range(1, 6):
                sample_id = 12345 + (iteration * 10) + i
                graph.add_node(sample_id, name=f'sample_{iteration}_{i}.wav', type='sample')
                
                # Connect to previous sample
                graph.add_edge(prev_sample_id, sample_id, weight=0.9)
                prev_sample_id = sample_id
            
            # Calculate metrics after each iteration
            metrics = calculate_connectivity_metrics(graph, mock_logger)
            
            # Rigorous assertions: Should remain connected as it grows
            assert metrics['is_connected'] is True, f"Graph disconnected at iteration {iteration}"
            assert metrics['num_components'] == 1, f"Expected 1 component, got {metrics['num_components']}"
            assert metrics['largest_component_size'] == graph.number_of_nodes()
            assert metrics['largest_component_pct'] == 100.0
            
            # Verify expected node count
            expected_nodes = 1 + (iteration * 5)  # seed + (iterations * 5 samples)
            assert graph.number_of_nodes() == expected_nodes, \
                f"Expected {expected_nodes} nodes, got {graph.number_of_nodes()}"
            
            # Verify metrics are in valid ranges
            assert 0.0 <= metrics['density'] <= 1.0
            assert 0.0 <= metrics['avg_clustering'] <= 1.0


@pytest.mark.integration
class TestConnectivityPerformance:
    """Test connectivity analysis performance with larger graphs."""
    
    def test_handles_large_connected_graph(self, mock_logger):
        """Test connectivity metrics for large connected graph.
        
        Note: Uses undirected graph for test simplicity and guaranteed connectivity.
        The connectivity module handles directed->undirected conversion internally.
        """
        # Create larger graph (1000 nodes)
        graph = nx.Graph()
        
        # Add nodes
        for i in range(1000):
            graph.add_node(i, name=f'sample{i}.wav', type='sample')
        
        # Create connected graph with random edges
        import random
        random.seed(42)
        
        # Ensure connectivity with path
        for i in range(999):
            graph.add_edge(i, i + 1, weight=0.9)
        
        # Add random edges for density
        for _ in range(2000):
            src = random.randint(0, 999)
            dst = random.randint(0, 999)
            if src != dst and not graph.has_edge(src, dst):
                graph.add_edge(src, dst, weight=random.uniform(0.5, 1.0))
        
        # Verify graph properties
        assert graph.number_of_nodes() == 1000
        assert graph.number_of_edges() >= 999  # At least the path edges
        
        # Should calculate metrics without errors
        metrics = calculate_connectivity_metrics(graph, mock_logger)
        
        # Rigorous assertions
        assert metrics['is_connected'] is True, "Large graph should be connected"
        assert metrics['num_components'] == 1, f"Expected 1 component, got {metrics['num_components']}"
        assert metrics['largest_component_size'] == 1000, \
            f"Expected 1000 nodes in component, got {metrics['largest_component_size']}"
        assert metrics['largest_component_pct'] == 100.0
        assert 0.0 < metrics['density'] < 1.0, f"Density {metrics['density']} out of range"
        assert 0.0 <= metrics['avg_clustering'] <= 1.0, \
            f"Clustering {metrics['avg_clustering']} out of range"
    
    def test_handles_large_disconnected_graph(self, mock_logger):
        """Test connectivity validation for large disconnected graph."""
        # Create larger disconnected graph
        graph = nx.DiGraph()
        
        # Create 10 disconnected components of varying sizes
        node_id = 0
        component_sizes = [100, 80, 60, 40, 30, 20, 15, 10, 5, 5]
        
        for comp_size in component_sizes:
            # Add nodes for this component
            comp_nodes = list(range(node_id, node_id + comp_size))
            for node in comp_nodes:
                graph.add_node(node, name=f'sample{node}.wav', type='sample')
            
            # Connect nodes within component
            for i in range(len(comp_nodes) - 1):
                graph.add_edge(comp_nodes[i], comp_nodes[i + 1], weight=0.9)
            
            node_id += comp_size
        
        # Should validate without errors
        validation = validate_connectivity(graph, mock_logger)
        
        assert validation['is_connected'] is False
        assert validation['num_components'] == 10
        assert validation['component_sizes'] == component_sizes
        # validate_connectivity returns largest_component_pct, not largest_component_size
        assert validation['largest_component_pct'] == pytest.approx(27.4, rel=0.1)
