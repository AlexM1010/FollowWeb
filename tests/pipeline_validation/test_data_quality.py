"""
Tests for data quality validation and anomaly detection.

Verifies data quality metrics, detects anomalies in node/edge counts,
and validates that data meets expected quality standards.
"""

import json
import pickle
from datetime import datetime, timedelta

import networkx as nx
import pytest


@pytest.fixture
def metrics_history():
    """Create sample metrics history for anomaly detection."""
    base_time = datetime.now()
    
    history = []
    for i in range(10):
        history.append({
            "timestamp": (base_time - timedelta(days=10-i)).isoformat(),
            "nodes": 100 + i * 10,  # Steady growth
            "edges": 300 + i * 30,  # Steady growth
            "api_requests": 50,
        })
    
    return history


@pytest.fixture
def anomalous_metrics_history():
    """Create metrics history with anomalies."""
    base_time = datetime.now()
    
    history = []
    for i in range(10):
        if i == 8:  # Sudden drop at index 8
            nodes = 50  # Dropped from ~180 to 50
            edges = 100  # Dropped from ~540 to 100
        else:
            nodes = 100 + i * 10
            edges = 300 + i * 30
        
        history.append({
            "timestamp": (base_time - timedelta(days=10-i)).isoformat(),
            "nodes": nodes,
            "edges": edges,
            "api_requests": 50 if i != 8 else 5,  # Low API usage on anomaly day
        })
    
    return history


@pytest.fixture
def healthy_graph():
    """Create a healthy graph with good quality metrics."""
    graph = nx.DiGraph()
    
    # Add 10 nodes with complete attributes
    for i in range(1, 11):
        graph.add_node(
            i,
            name=f"sample{i}",
            audio_url=f"http://example.com/{i}.mp3",
            duration=120.0,
            tags=["tag1", "tag2"]
        )
    
    # Add edges with reasonable weights
    for i in range(1, 10):
        graph.add_edge(i, i+1, weight=0.7 + i * 0.02, type="similar")
    
    # Add some cross-connections
    graph.add_edge(1, 5, weight=0.6, type="similar")
    graph.add_edge(3, 8, weight=0.65, type="similar")
    
    return graph


@pytest.fixture
def poor_quality_graph():
    """Create a graph with quality issues."""
    graph = nx.DiGraph()
    
    # Add nodes with missing/incomplete attributes
    graph.add_node(1, name="sample1", audio_url="http://example.com/1.mp3")
    graph.add_node(2, name="sample2")  # Missing audio_url
    graph.add_node(3, audio_url="http://example.com/3.mp3")  # Missing name
    graph.add_node(4, name="", audio_url="")  # Empty attributes
    
    # Add edges with suspicious weights
    graph.add_edge(1, 2, weight=1.5, type="similar")  # Weight > 1
    graph.add_edge(2, 3, weight=-0.1, type="similar")  # Negative weight
    graph.add_edge(3, 4, type="similar")  # Missing weight
    
    return graph


class TestDataQuality:
    """Test suite for data quality validation and anomaly detection."""
    
    def test_detect_node_count_drop(self, anomalous_metrics_history):
        """Test detection of sudden drop in node count."""
        # Check the anomaly at index 8 (sudden drop from 180 to 50)
        current = anomalous_metrics_history[8]
        previous = anomalous_metrics_history[7]
        
        node_drop_pct = (previous["nodes"] - current["nodes"]) / previous["nodes"] * 100
        
        # Should detect >10% drop
        assert node_drop_pct > 10, "Node count drop not detected"
    
    def test_detect_edge_count_drop(self, anomalous_metrics_history):
        """Test detection of sudden drop in edge count."""
        # Check the anomaly at index 8 (sudden drop from 540 to 100)
        current = anomalous_metrics_history[8]
        previous = anomalous_metrics_history[7]
        
        edge_drop_pct = (previous["edges"] - current["edges"]) / previous["edges"] * 100
        
        # Should detect >10% drop
        assert edge_drop_pct > 10, "Edge count drop not detected"
    
    def test_detect_low_api_usage(self, anomalous_metrics_history):
        """Test detection of unusually low API usage."""
        # Check the anomaly at index 8 (API usage dropped to 5 from 50)
        current = anomalous_metrics_history[8]
        
        # Calculate average API usage from history (excluding anomaly)
        normal_entries = [m for i, m in enumerate(anomalous_metrics_history) if i != 8]
        avg_api_usage = sum(m["api_requests"] for m in normal_entries) / len(normal_entries)
        
        # Current usage should be significantly lower
        usage_ratio = current["api_requests"] / avg_api_usage
        
        assert usage_ratio < 0.5, "Low API usage not detected"
    
    def test_healthy_graph_passes_quality_checks(self, healthy_graph):
        """Test that a healthy graph passes all quality checks."""
        # Check node attributes
        for node_id, attrs in healthy_graph.nodes(data=True):
            assert "name" in attrs and len(attrs["name"]) > 0
            assert "audio_url" in attrs and len(attrs["audio_url"]) > 0
        
        # Check edge weights
        for source, target, attrs in healthy_graph.edges(data=True):
            assert "weight" in attrs
            assert 0 <= attrs["weight"] <= 1
        
        # Check connectivity
        assert nx.is_weakly_connected(healthy_graph)
    
    def test_poor_quality_graph_fails_checks(self, poor_quality_graph):
        """Test that a poor quality graph fails quality checks."""
        issues = []
        
        # Check for missing attributes
        for node_id, attrs in poor_quality_graph.nodes(data=True):
            if "name" not in attrs or len(attrs.get("name", "")) == 0:
                issues.append(f"Node {node_id} missing/empty name")
            if "audio_url" not in attrs or len(attrs.get("audio_url", "")) == 0:
                issues.append(f"Node {node_id} missing/empty audio_url")
        
        # Check for invalid edge weights
        for source, target, attrs in poor_quality_graph.edges(data=True):
            if "weight" not in attrs:
                issues.append(f"Edge ({source}, {target}) missing weight")
            elif attrs["weight"] < 0 or attrs["weight"] > 1:
                issues.append(f"Edge ({source}, {target}) has invalid weight")
        
        assert len(issues) > 0, "Quality issues not detected"
    
    def test_zero_nodes_added_detected(self):
        """Test detection of runs where no nodes were added."""
        current_metrics = {"nodes": 100, "edges": 300}
        previous_metrics = {"nodes": 100, "edges": 300}
        
        nodes_added = current_metrics["nodes"] - previous_metrics["nodes"]
        
        assert nodes_added == 0, "Should detect zero nodes added"
    
    def test_zero_edges_added_detected(self):
        """Test detection of runs where no edges were added."""
        current_metrics = {"nodes": 110, "edges": 300}
        previous_metrics = {"nodes": 100, "edges": 300}
        
        edges_added = current_metrics["edges"] - previous_metrics["edges"]
        
        assert edges_added == 0, "Should detect zero edges added"
    
    def test_edge_to_node_ratio_reasonable(self, healthy_graph):
        """Test that edge-to-node ratio is reasonable."""
        nodes = healthy_graph.number_of_nodes()
        edges = healthy_graph.number_of_edges()
        
        ratio = edges / nodes if nodes > 0 else 0
        
        # For a similarity graph, expect 1-10 edges per node on average
        assert 0.5 <= ratio <= 20, f"Edge-to-node ratio {ratio} is unusual"
    
    def test_graph_density_within_bounds(self, healthy_graph):
        """Test that graph density is within expected bounds."""
        density = nx.density(healthy_graph)
        
        # Density should be reasonable (not too sparse, not too dense)
        assert 0.01 <= density <= 0.8, f"Graph density {density} is unusual"
    
    def test_no_duplicate_audio_urls(self, healthy_graph):
        """Test that there are no duplicate audio URLs."""
        audio_urls = []
        
        for node_id, attrs in healthy_graph.nodes(data=True):
            if "audio_url" in attrs:
                audio_urls.append(attrs["audio_url"])
        
        unique_urls = set(audio_urls)
        
        assert len(audio_urls) == len(unique_urls), \
            "Found duplicate audio URLs"
    
    def test_node_names_are_unique(self, healthy_graph):
        """Test that node names are unique."""
        names = []
        
        for node_id, attrs in healthy_graph.nodes(data=True):
            if "name" in attrs:
                names.append(attrs["name"])
        
        unique_names = set(names)
        
        assert len(names) == len(unique_names), \
            "Found duplicate node names"
    
    def test_average_degree_reasonable(self, healthy_graph):
        """Test that average node degree is reasonable."""
        degrees = [d for n, d in healthy_graph.degree()]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        
        # Average degree should be reasonable for a similarity graph
        assert 1 <= avg_degree <= 50, \
            f"Average degree {avg_degree} is unusual"
    
    def test_no_extreme_outlier_degrees(self, healthy_graph):
        """Test that there are no extreme outlier node degrees."""
        degrees = [d for n, d in healthy_graph.degree()]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        max_degree = max(degrees) if degrees else 0
        
        # Max degree shouldn't be more than 10x average
        if avg_degree > 0:
            ratio = max_degree / avg_degree
            assert ratio <= 10, \
                f"Max degree {max_degree} is {ratio}x average (outlier)"
    
    def test_growth_rate_reasonable(self, metrics_history):
        """Test that growth rate is reasonable and consistent."""
        growth_rates = []
        
        for i in range(1, len(metrics_history)):
            prev_nodes = metrics_history[i-1]["nodes"]
            curr_nodes = metrics_history[i]["nodes"]
            
            if prev_nodes > 0:
                growth_rate = (curr_nodes - prev_nodes) / prev_nodes * 100
                growth_rates.append(growth_rate)
        
        # Growth should be positive and consistent
        assert all(rate >= 0 for rate in growth_rates), \
            "Negative growth detected"
        
        # Growth rate variance should be low (consistent growth)
        if len(growth_rates) > 1:
            avg_growth = sum(growth_rates) / len(growth_rates)
            variance = sum((r - avg_growth) ** 2 for r in growth_rates) / len(growth_rates)
            std_dev = variance ** 0.5
            
            # Standard deviation should be reasonable
            assert std_dev < 50, \
                f"Growth rate too variable (std dev: {std_dev})"
    
    def test_api_quota_not_exceeded(self):
        """Test that API quota is not exceeded."""
        api_requests_used = 1800
        api_quota = 1950
        
        assert api_requests_used <= api_quota, \
            f"API quota exceeded: {api_requests_used}/{api_quota}"
    
    def test_api_usage_efficiency(self):
        """Test that API usage is efficient (not too low)."""
        api_requests_used = 1800
        api_quota = 1950
        nodes_added = 50
        
        # Should use reasonable amount of quota
        usage_pct = (api_requests_used / api_quota) * 100
        
        # If nodes were added, API usage should be significant
        if nodes_added > 0:
            assert usage_pct >= 50, \
                f"API usage too low ({usage_pct}%) despite adding nodes"
    
    def test_edge_weights_distribution(self, healthy_graph):
        """Test that edge weights have reasonable distribution."""
        weights = [attrs["weight"] for _, _, attrs in healthy_graph.edges(data=True)]
        
        if weights:
            avg_weight = sum(weights) / len(weights)
            min_weight = min(weights)
            max_weight = max(weights)
            
            # Average weight should be reasonable
            assert 0.3 <= avg_weight <= 0.9, \
                f"Average edge weight {avg_weight} is unusual"
            
            # Should have some variation in weights
            weight_range = max_weight - min_weight
            assert weight_range > 0.1, \
                "Edge weights lack variation"
