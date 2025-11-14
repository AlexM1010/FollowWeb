"""
Unit tests for MetadataCache SQL-based seed selection.

Tests get_best_seed_sample() with various priority scenarios,
dormant node filtering, and edge cases.
"""

import logging
import sqlite3
import tempfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.data]

from FollowWeb_Visualizor.data.storage.metadata_cache import MetadataCache


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.fixture
def temp_db():
    """Fixture providing temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def metadata_cache(temp_db, mock_logger):
    """Fixture providing MetadataCache instance."""
    cache = MetadataCache(db_path=temp_db, logger=mock_logger)
    yield cache
    cache.close()


def insert_sample(cache, sample_id, priority_score, is_dormant=False):
    """Helper to insert a sample with priority and dormant status."""
    cache.set(
        sample_id=sample_id,
        metadata={"priority_score": priority_score, "is_dormant": is_dormant},
    )


@pytest.mark.unit
class TestGetBestSeedSample:
    """Test get_best_seed_sample method."""

    def test_get_best_seed_with_single_sample(self, metadata_cache):
        """Test getting best seed with single non-dormant sample."""
        insert_sample(metadata_cache, 12345, 100.0, False)
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        assert best_seed == 12345

    def test_get_best_seed_with_multiple_samples(self, metadata_cache):
        """Test getting best seed with multiple samples of different priorities."""
        # Insert samples with different priority scores
        insert_sample(metadata_cache, 10001, 50.0, False)  # Medium priority
        insert_sample(metadata_cache, 10002, 100.0, False)  # Highest priority
        insert_sample(metadata_cache, 10003, 25.0, False)  # Low priority
        insert_sample(metadata_cache, 10004, 75.0, False)  # High priority
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return sample with highest priority (100.0)
        assert best_seed == 10002

    def test_get_best_seed_filters_dormant_nodes(self, metadata_cache):
        """Test that dormant nodes are filtered out."""
        # Insert samples, some dormant
        insert_sample(
            metadata_cache, 20001, 150.0, True
        )  # Highest priority but dormant
        insert_sample(
            metadata_cache, 20002, 100.0, False
        )  # Second highest, not dormant
        insert_sample(metadata_cache, 20003, 75.0, True)  # Dormant
        insert_sample(metadata_cache, 20004, 50.0, False)  # Not dormant
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return highest priority non-dormant sample (20002)
        assert best_seed == 20002

    def test_get_best_seed_all_dormant(self, metadata_cache):
        """Test when all samples are dormant."""
        # Insert only dormant samples
        insert_sample(metadata_cache, 30001, 100.0, True)
        insert_sample(metadata_cache, 30002, 75.0, True)
        insert_sample(metadata_cache, 30003, 50.0, True)
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return None when all samples are dormant
        assert best_seed is None

    def test_get_best_seed_empty_cache(self, metadata_cache):
        """Test when cache is empty."""
        best_seed = metadata_cache.get_best_seed_sample()

        # Should return None for empty cache
        assert best_seed is None

    def test_get_best_seed_with_equal_priorities(self, metadata_cache):
        """Test behavior when multiple samples have same priority."""
        # Insert samples with same priority
        insert_sample(metadata_cache, 40001, 100.0, False)
        insert_sample(metadata_cache, 40002, 100.0, False)
        insert_sample(metadata_cache, 40003, 100.0, False)
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return one of the samples with highest priority
        assert best_seed in [40001, 40002, 40003]

    def test_get_best_seed_with_negative_priorities(self, metadata_cache):
        """Test with negative priority scores."""
        # Insert samples with negative priorities
        insert_sample(metadata_cache, 50001, -10.0, False)
        insert_sample(metadata_cache, 50002, -5.0, False)  # Highest (least negative)
        insert_sample(metadata_cache, 50003, -20.0, False)
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return sample with highest priority (-5.0)
        assert best_seed == 50002

    def test_get_best_seed_with_zero_priority(self, metadata_cache):
        """Test with zero priority scores."""
        # Insert samples with zero and positive priorities
        insert_sample(metadata_cache, 60001, 0.0, False)
        insert_sample(metadata_cache, 60002, 10.0, False)  # Highest
        insert_sample(metadata_cache, 60003, 0.0, False)
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return sample with highest priority (10.0)
        assert best_seed == 60002

    def test_get_best_seed_performance(self, metadata_cache):
        """Test that seed selection is fast even with many samples."""
        # Insert many samples
        for i in range(1000):
            insert_sample(
                metadata_cache,
                70000 + i,
                float(i),
                is_dormant=(i % 2 == 1),  # Half dormant
            )
        metadata_cache.flush()

        # Should complete quickly (O(1) with index)
        import time

        start = time.time()
        best_seed = metadata_cache.get_best_seed_sample()
        elapsed = time.time() - start

        # Should return highest priority non-dormant sample
        assert best_seed == 70998  # i=998, priority=998.0, not dormant

        # Should be very fast (< 0.1 seconds)
        assert elapsed < 0.1


@pytest.mark.unit
class TestDormantNodeFiltering:
    """Test dormant node filtering in various scenarios."""

    def test_dormant_flag_false_vs_true(self, metadata_cache):
        """Test that is_dormant=False and is_dormant=True are correctly filtered."""
        insert_sample(metadata_cache, 80001, 100.0, False)  # Not dormant
        insert_sample(metadata_cache, 80002, 90.0, True)  # Dormant
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should only consider is_dormant=False
        assert best_seed == 80001

    def test_dormant_status_update(self, metadata_cache):
        """Test that updating dormant status affects seed selection."""
        # Insert sample as not dormant
        insert_sample(metadata_cache, 90001, 100.0, False)
        metadata_cache.flush()

        # Should be selected
        assert metadata_cache.get_best_seed_sample() == 90001

        # Update to dormant
        insert_sample(metadata_cache, 90001, 100.0, True)
        metadata_cache.flush()

        # Should no longer be selected
        assert metadata_cache.get_best_seed_sample() is None

    def test_mixed_dormant_states(self, metadata_cache):
        """Test with mix of dormant and non-dormant samples."""
        insert_sample(metadata_cache, 95001, 50.0, True)  # Dormant
        insert_sample(metadata_cache, 95002, 75.0, False)  # Not dormant
        insert_sample(metadata_cache, 95003, 100.0, True)  # Dormant (highest priority)
        insert_sample(metadata_cache, 95004, 60.0, False)  # Not dormant
        insert_sample(metadata_cache, 95005, 25.0, True)  # Dormant
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return highest priority non-dormant (95002 with 75.0)
        assert best_seed == 95002


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_best_seed_after_close(self, temp_db, mock_logger):
        """Test behavior after closing cache."""
        cache = MetadataCache(db_path=temp_db, logger=mock_logger)

        # Insert sample
        insert_sample(cache, 100001, 100.0, False)
        cache.flush()

        # Close cache
        cache.close()

        # Attempting to get best seed after close should raise error
        with pytest.raises(Exception):
            cache.get_best_seed_sample()

    def test_get_best_seed_with_null_priority(self, metadata_cache):
        """Test handling of NULL priority scores."""
        # Manually insert sample with NULL priority using SQL
        conn = metadata_cache._conn
        conn.execute(
            """
            INSERT OR REPLACE INTO metadata (sample_id, priority_score, is_dormant, data, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """,
            (110001, None, 0, "{}", "2025-11-11T00:00:00Z"),
        )
        conn.commit()

        # Insert sample with valid priority
        insert_sample(metadata_cache, 110002, 50.0, False)
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should return sample with valid priority
        assert best_seed == 110002

    def test_get_best_seed_with_very_large_priority(self, metadata_cache):
        """Test with very large priority scores."""
        insert_sample(metadata_cache, 120001, 1e10, False)  # Very large
        insert_sample(metadata_cache, 120002, 1e9, False)
        insert_sample(metadata_cache, 120003, 1e8, False)
        metadata_cache.flush()

        best_seed = metadata_cache.get_best_seed_sample()

        # Should handle large numbers correctly
        assert best_seed == 120001

    def test_get_best_seed_idempotent(self, metadata_cache):
        """Test that calling get_best_seed_sample multiple times returns same result."""
        # Insert samples
        insert_sample(metadata_cache, 130001, 100.0, False)
        insert_sample(metadata_cache, 130002, 75.0, False)
        insert_sample(metadata_cache, 130003, 50.0, False)
        metadata_cache.flush()

        # Call multiple times
        result1 = metadata_cache.get_best_seed_sample()
        result2 = metadata_cache.get_best_seed_sample()
        result3 = metadata_cache.get_best_seed_sample()

        # Should return same result each time
        assert result1 == result2 == result3 == 130001
