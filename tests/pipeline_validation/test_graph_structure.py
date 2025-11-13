"""
Tests for graph structure validation.

Verifies that the graph has valid structure with no orphaned edges,
all nodes have required attributes, and edge relationships are consistent.
"""

import pickle

import networkx as nx
import pytest


@pytest.fixture
def valid_graph():
    """Create a valid graph with proper structure."""
    graph = nx.DiGraph()
    
    # Add nodes with required attributes
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    graph.add_node(2, name="sample2", audio_url="http://example.com/2.mp3")
    graph.add_node(3, name="sample3", audio_url="http://example.com/3.mp3")
    
    # Add edges with weights
    graph.add_edge(1, 2, weight=0.8, type="similar")
    graph.add_edge(2, 3, weight=0.6, type="similar")
    graph.add_edge(1, 3, weight=0.5, type="similar")
    
    return graph


@pytest.fixture
def graph_with_orphaned_edges():
    """Create a graph with orphaned edges (edges referencing non-existent nodes)."""
    graph = nx.DiGraph()
    
    # Add nodes
    graph.add_node(1, name="sample1")
    graph.add_node(2, name="sample2")
    
    # Add edge to non-existent node (this shouldn't happen in NetworkX normally,
    # but we simulate the check)
    graph.add_edge(1, 2, weight=0.8)
    
    # Manually track a "missing" node reference for testing
    graph.graph['orphaned_references'] = [999]
    
    return graph


@pytest.fixture
def graph_with_missing_attributes():
    """Create a graph with nodes missing required attributes."""
    graph = nx.DiGraph()
    
    # Node with all attributes
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    
    # Node missing audio_url
    graph.add_node(2, name="sample2")
    
    # Node missing name
    graph.add_node(3, audio_url="http://example.com/3.mp3")
    
    return graph


@pytest.fixture
def graph_with_self_loops():
    """Create a graph with self-loops."""
    graph = nx.DiGraph()
    
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    graph.add_node(2, name="sample2", audio_url="http://example.com/2.mp3")
    
    # Add self-loop
    graph.add_edge(1, 1, weight=1.0, type="similar")
    graph.add_edge(1, 2, weight=0.8, type="similar")
    
    return graph


class TestGraphStructure:
    """Test suite for graph structure validation."""
    
    def test_valid_graph_has_no_orphaned_edges(self, valid_graph):
        """Test that valid graph has no orphaned edges."""
        # Check that all edges reference existing nodes
        for source, target in valid_graph.edges():
            assert source in valid_graph.nodes()
            assert target in valid_graph.nodes()
    
    def test_all_nodes_have_required_attributes(self, valid_graph):
        """Test that all nodes have required attributes."""
        required_attrs = ["name", "audio_url"]
        
        for node_id, attrs in valid_graph.nodes(data=True):
            for attr in required_attrs:
                assert attr in attrs, f"Node {node_id} missing attribute: {attr}"
    
    def test_graph_is_directed(self, valid_graph):
        """Test that graph is a directed graph."""
        assert isinstance(valid_graph, nx.DiGraph)
        assert valid_graph.is_directed()
    
    def test_graph_has_nodes(self, valid_graph):
        """Test that graph has at least one node."""
        assert valid_graph.number_of_nodes() > 0
    
    def test_graph_has_edges(self, valid_graph):
        """Test that graph has at least one edge."""
        assert valid_graph.number_of_edges() > 0
    
    def test_all_edges_have_weights(self, valid_graph):
        """Test that all edges have weight attributes."""
        for source, target, attrs in valid_graph.edges(data=True):
            assert "weight" in attrs, f"Edge ({source}, {target}) missing weight"
            assert isinstance(attrs["weight"], (int, float))
            assert 0 <= attrs["weight"] <= 1, "Weight should be between 0 and 1"
    
    def test_no_duplicate_edges(self, valid_graph):
        """Test that there are no duplicate edges."""
        edges = list(valid_graph.edges())
        unique_edges = set(edges)
        
        assert len(edges) == len(unique_edges), "Graph contains duplicate edges"
    
    def test_node_ids_are_integers(self, valid_graph):
        """Test that all node IDs are integers."""
        for node_id in valid_graph.nodes():
            assert isinstance(node_id, int), f"Node ID {node_id} is not an integer"
    
    def test_graph_with_missing_attributes_detected(self, graph_with_missing_attributes):
        """Test that nodes with missing attributes are detected."""
        required_attrs = ["name", "audio_url"]
        missing_attrs = []
        
        for node_id, attrs in graph_with_missing_attributes.nodes(data=True):
            for attr in required_attrs:
                if attr not in attrs:
                    missing_attrs.append((node_id, attr))
        
        # Should detect 2 missing attributes (node 2 missing audio_url, node 3 missing name)
        assert len(missing_attrs) == 2
    
    def test_self_loops_detected(self, graph_with_self_loops):
        """Test that self-loops are detected."""
        self_loops = list(nx.selfloop_edges(graph_with_self_loops))
        
        assert len(self_loops) > 0, "Self-loops should be detected"
        assert (1, 1) in self_loops
    
    def test_graph_connectivity(self, valid_graph):
        """Test basic graph connectivity properties."""
        # Convert to undirected for connectivity check
        undirected = valid_graph.to_undirected()
        
        # Check if graph is connected
        is_connected = nx.is_connected(undirected)
        
        # For a valid Freesound graph, we expect it to be connected
        # (or have a large connected component)
        if not is_connected:
            # Check that largest component is significant
            components = list(nx.connected_components(undirected))
            largest_component = max(components, key=len)
            
            # Largest component should contain most nodes
            assert len(largest_component) >= undirected.number_of_nodes() * 0.5
    
    def test_no_isolated_nodes(self, valid_graph):
        """Test that there are no isolated nodes (nodes with no edges)."""
        isolated_nodes = list(nx.isolates(valid_graph))
        
        # For a similarity graph, isolated nodes might indicate data issues
        assert len(isolated_nodes) == 0, f"Found {len(isolated_nodes)} isolated nodes"
    
    def test_edge_types_are_valid(self, valid_graph):
        """Test that edge types are from expected set."""
        valid_types = {"similar", "by_same_user", "in_same_pack"}
        
        for source, target, attrs in valid_graph.edges(data=True):
            if "type" in attrs:
                assert attrs["type"] in valid_types, \
                    f"Invalid edge type: {attrs['type']}"
    
    def test_graph_density_is_reasonable(self, valid_graph):
        """Test that graph density is within reasonable bounds."""
        density = nx.density(valid_graph)
        
        # Density should be between 0 and 1
        assert 0 <= density <= 1
        
        # For a similarity graph, very high density might indicate issues
        # (every sample similar to every other sample is unlikely)
        assert density < 0.9, "Graph density suspiciously high"
    
    def test_node_degrees_are_reasonable(self, valid_graph):
        """Test that node degrees are within reasonable bounds."""
        degrees = dict(valid_graph.degree())
        
        for node_id, degree in degrees.items():
            # Each node should have at least some connections
            assert degree > 0, f"Node {node_id} has degree 0"
            
            # Degree shouldn't exceed total nodes - 1
            assert degree < valid_graph.number_of_nodes(), \
                f"Node {node_id} has invalid degree {degree}"
    
    def test_graph_has_no_multi_edges(self, valid_graph):
        """Test that graph has no multi-edges (multiple edges between same nodes)."""
        # DiGraph doesn't support multi-edges by default, but verify
        assert not valid_graph.is_multigraph()
    
    def test_audio_urls_are_valid_format(self, valid_graph):
        """Test that audio URLs have valid format."""
        for node_id, attrs in valid_graph.nodes(data=True):
            if "audio_url" in attrs:
                url = attrs["audio_url"]
                # Basic URL validation
                assert isinstance(url, str)
                assert len(url) > 0
                # Should start with http:// or https://
                assert url.startswith(("http://", "https://")) or url == "", \
                    f"Invalid audio URL format for node {node_id}: {url}"
    
    def test_node_names_are_non_empty(self, valid_graph):
        """Test that node names are non-empty strings."""
        for node_id, attrs in valid_graph.nodes(data=True):
            if "name" in attrs:
                name = attrs["name"]
                assert isinstance(name, str)
                assert len(name) > 0, f"Node {node_id} has empty name"
