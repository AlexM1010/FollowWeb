"""
Integration tests for validation workflow.

Tests end-to-end validation with both full and partial modes,
checkpoint cleaning, report generation, timestamp updates, and metadata refresh.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from validate_freesound_samples import SampleValidator, write_validation_report


@pytest.fixture
def test_checkpoint_dir(tmp_path):
    """Fixture providing temporary checkpoint directory."""
    checkpoint_dir = tmp_path / "data" / "freesound_library"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.fixture
def sample_validator(mock_logger):
    """Fixture providing SampleValidator instance."""
    return SampleValidator(api_key="test_api_key", logger=mock_logger)


@pytest.fixture
def test_graph_with_mixed_samples():
    """Fixture providing test graph with valid and deleted samples."""
    graph = nx.DiGraph()
    
    # Add sample nodes
    for i in range(1, 11):
        sample_id = 12340 + i
        graph.add_node(
            sample_id,
            name=f'sample{i}.wav',
            type='sample',
            num_downloads=1000 - (i * 50),
            avg_rating=4.5 - (i * 0.1),
            num_ratings=100 - (i * 5),
            num_comments=20 - i
        )
    
    # Add edges
    for i in range(1, 10):
        graph.add_edge(12340 + i, 12340 + i + 1, weight=0.9 - (i * 0.05))
    
    return graph


@pytest.mark.integration
class TestFullValidationWorkflow:
    """Test full validation workflow end-to-end."""
    
    def test_full_validation_with_checkpoint_cleaning(
        self,
        sample_validator,
        test_graph_with_mixed_samples
    ):
        """Test full validation that removes deleted samples and updates checkpoint."""
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        # Mock API: samples 12343, 12346, 12349 are deleted
        def mock_get(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            
            # Return all samples except deleted ones
            results = []
            for i in [1, 2, 4, 5, 7, 8, 10]:  # Skip 3, 6, 9
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 1100 - (i * 50),
                    'avg_rating': 4.6 - (i * 0.1),
                    'num_ratings': 110 - (i * 5),
                    'num_comments': 25 - i
                })
            
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            stats = sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='full'
            )
        
        # Verify stats
        assert stats['validated_samples'] == 7
        assert len(stats['deleted_samples']) == 3
        assert stats['metadata_refreshed'] == 7
        
        # Verify deleted sample IDs
        deleted_ids = {s['id'] for s in stats['deleted_samples']}
        assert deleted_ids == {'12343', '12346', '12349'}
        
        # Verify graph was cleaned
        assert test_graph_with_mixed_samples.number_of_nodes() == 7
        assert 12343 not in test_graph_with_mixed_samples.nodes
        assert 12346 not in test_graph_with_mixed_samples.nodes
        assert 12349 not in test_graph_with_mixed_samples.nodes
        
        # Verify processed_ids was updated
        assert '12343' not in processed_ids
        assert '12346' not in processed_ids
        assert '12349' not in processed_ids
        
        # Verify metadata was refreshed for valid samples
        assert test_graph_with_mixed_samples.nodes[12341]['num_downloads'] == 1050
        assert test_graph_with_mixed_samples.nodes[12342]['avg_rating'] == pytest.approx(4.4, rel=0.01)
        
        # Verify timestamps were updated
        for node_id in test_graph_with_mixed_samples.nodes:
            assert 'last_existence_check_at' in test_graph_with_mixed_samples.nodes[node_id]
            assert 'last_metadata_update_at' in test_graph_with_mixed_samples.nodes[node_id]
    
    def test_full_validation_with_report_generation(
        self,
        sample_validator,
        test_graph_with_mixed_samples,
        tmp_path
    ):
        """Test full validation generates correct report."""
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        # Mock API: all samples valid
        def mock_get(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            results = []
            for i in range(1, 11):
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 1100 - (i * 50),
                    'avg_rating': 4.6 - (i * 0.1),
                    'num_ratings': 110 - (i * 5),
                    'num_comments': 25 - i
                })
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            stats = sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='full'
            )
        
        # Write report
        report_path = tmp_path / "validation_report.json"
        write_validation_report(stats, report_path, mode='full')
        
        # Verify report was created
        assert report_path.exists()
        
        # Verify report contents
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        assert report['validation_mode'] == 'full'
        assert report['total_samples'] == 10
        assert report['validated_samples'] == 10
        assert report['metadata_refreshed'] == 10
        assert len(report['deleted_samples']) == 0
        assert 'timestamp' in report


@pytest.mark.integration
class TestPartialValidationWorkflow:
    """Test partial validation workflow end-to-end."""
    
    def test_partial_validation_validates_oldest_samples(
        self,
        sample_validator,
        test_graph_with_mixed_samples
    ):
        """Test partial validation only validates oldest samples."""
        # Add timestamps to simulate age
        for i in range(1, 11):
            sample_id = 12340 + i
            # Older samples have older timestamps
            test_graph_with_mixed_samples.nodes[sample_id]['last_existence_check_at'] = \
                f'2024-01-{i:02d}T00:00:00'
        
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        # Mock API: return all samples as valid
        def mock_get(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            results = []
            for i in range(1, 11):
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 1100 - (i * 50),
                    'avg_rating': 4.6 - (i * 0.1),
                    'num_ratings': 110 - (i * 5),
                    'num_comments': 25 - i
                })
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            stats = sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='partial'
            )
        
        # In partial mode with only 10 samples, all should be validated
        # (partial mode validates up to 300 oldest)
        assert stats['validated_samples'] == 10
        assert len(stats['deleted_samples']) == 0
        assert stats['metadata_refreshed'] == 10
    
    def test_partial_validation_with_report_generation(
        self,
        sample_validator,
        test_graph_with_mixed_samples,
        tmp_path
    ):
        """Test partial validation generates correct report."""
        # Add timestamps
        for i in range(1, 11):
            sample_id = 12340 + i
            test_graph_with_mixed_samples.nodes[sample_id]['last_existence_check_at'] = \
                f'2024-01-{i:02d}T00:00:00'
        
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        # Mock API: samples 12342 and 12345 are deleted
        def mock_get(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            results = []
            for i in [1, 3, 4, 6, 7, 8, 9, 10]:  # Skip 2, 5
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 1100 - (i * 50),
                    'avg_rating': 4.6 - (i * 0.1),
                    'num_ratings': 110 - (i * 5),
                    'num_comments': 25 - i
                })
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            stats = sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='partial'
            )
        
        # Write report
        report_path = tmp_path / "validation_report_partial.json"
        write_validation_report(stats, report_path, mode='partial')
        
        # Verify report
        assert report_path.exists()
        
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        assert report['validation_mode'] == 'partial'
        assert report['validated_samples'] == 8
        assert len(report['deleted_samples']) == 2
        assert report['metadata_refreshed'] == 8


@pytest.mark.integration
class TestMetadataRefreshIntegration:
    """Test metadata refresh integration with validation."""
    
    def test_metadata_refresh_updates_node_attributes(
        self,
        sample_validator,
        test_graph_with_mixed_samples
    ):
        """Test that metadata refresh updates node attributes correctly."""
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        # Store original values
        original_downloads = test_graph_with_mixed_samples.nodes[12341]['num_downloads']
        original_rating = test_graph_with_mixed_samples.nodes[12342]['avg_rating']
        
        # Mock API with updated metadata
        def mock_get(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            results = []
            for i in range(1, 11):
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 2000 + (i * 100),  # Significantly different
                    'avg_rating': 4.8 - (i * 0.05),     # Significantly different
                    'num_ratings': 200 + (i * 10),
                    'num_comments': 50 + i
                })
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            stats = sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='full'
            )
        
        # Verify metadata was refreshed
        assert stats['metadata_refreshed'] == 10
        
        # Verify values were updated
        assert test_graph_with_mixed_samples.nodes[12341]['num_downloads'] != original_downloads
        assert test_graph_with_mixed_samples.nodes[12341]['num_downloads'] == 2100
        
        assert test_graph_with_mixed_samples.nodes[12342]['avg_rating'] != original_rating
        assert test_graph_with_mixed_samples.nodes[12342]['avg_rating'] == 4.7
        
        # Verify all metadata fields were updated
        assert test_graph_with_mixed_samples.nodes[12343]['num_ratings'] == 230
        assert test_graph_with_mixed_samples.nodes[12344]['num_comments'] == 54
    
    def test_metadata_refresh_at_zero_cost(
        self,
        sample_validator,
        test_graph_with_mixed_samples
    ):
        """Test that metadata refresh happens during validation (zero additional API calls)."""
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        api_call_count = [0]
        
        def mock_get(*args, **kwargs):
            api_call_count[0] += 1
            response = Mock()
            response.status_code = 200
            results = []
            for i in range(1, 11):
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 2000 + (i * 100),
                    'avg_rating': 4.8 - (i * 0.05),
                    'num_ratings': 200 + (i * 10),
                    'num_comments': 50 + i
                })
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            stats = sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='full'
            )
        
        # Should only make 1 API call (batch validation with metadata)
        # Not 10 separate calls for validation + 10 for metadata
        assert api_call_count[0] == 1
        
        # But metadata should still be refreshed
        assert stats['metadata_refreshed'] == 10


@pytest.mark.integration
class TestTimestampUpdates:
    """Test timestamp updates during validation."""
    
    def test_existence_check_timestamp_updated(
        self,
        sample_validator,
        test_graph_with_mixed_samples
    ):
        """Test that last_existence_check_at is updated for all validated samples."""
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        # Set old timestamps
        for i in range(1, 11):
            sample_id = 12340 + i
            test_graph_with_mixed_samples.nodes[sample_id]['last_existence_check_at'] = \
                '2023-01-01T00:00:00'
        
        # Mock API
        def mock_get(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            results = []
            for i in range(1, 11):
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 1000,
                    'avg_rating': 4.5,
                    'num_ratings': 100,
                    'num_comments': 20
                })
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='full'
            )
        
        # Verify timestamps were updated to recent values
        for i in range(1, 11):
            sample_id = 12340 + i
            timestamp = test_graph_with_mixed_samples.nodes[sample_id]['last_existence_check_at']
            # Should be updated to 2024 or later
            assert timestamp.startswith('202')
            assert timestamp > '2023-01-01T00:00:00'
    
    def test_metadata_update_timestamp_set(
        self,
        sample_validator,
        test_graph_with_mixed_samples
    ):
        """Test that last_metadata_update_at is set when metadata is refreshed."""
        processed_ids = {str(12340 + i) for i in range(1, 11)}
        
        # Mock API
        def mock_get(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            results = []
            for i in range(1, 11):
                sample_id = 12340 + i
                results.append({
                    'id': sample_id,
                    'num_downloads': 1000,
                    'avg_rating': 4.5,
                    'num_ratings': 100,
                    'num_comments': 20
                })
            response.json.return_value = {'results': results}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            sample_validator.validate_and_clean_checkpoint(
                test_graph_with_mixed_samples,
                processed_ids,
                mode='full'
            )
        
        # Verify metadata update timestamps were set
        for i in range(1, 11):
            sample_id = 12340 + i
            assert 'last_metadata_update_at' in test_graph_with_mixed_samples.nodes[sample_id]
            timestamp = test_graph_with_mixed_samples.nodes[sample_id]['last_metadata_update_at']
            assert timestamp.startswith('202')
