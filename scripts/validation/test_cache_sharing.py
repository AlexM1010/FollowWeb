#!/usr/bin/env python3
"""
Cache Sharing End-to-End Test Script

Tests cache sharing between workflows to verify:
- Repair workflow can restore from cache
- Validation workflow can restore from cache
- All three files present and valid

Requirements: 3.2, 3.3, 4.1
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CacheSharingTester:
    """Tests cache sharing between workflows."""
    
    REQUIRED_FILES = [
        'graph_topology.gpickle',
        'metadata_cache.db',
        'checkpoint_metadata.json'
    ]
    
    def __init__(self, checkpoint_dir: Path, cache_dir: Path):
        """
        Initialize tester.
        
        Args:
            checkpoint_dir: Path to checkpoint directory
            cache_dir: Path to simulated cache directory
        """
        self.checkpoint_dir = checkpoint_dir
        self.cache_dir = cache_dir
        self.results = {
            'tests_passed': 0,
            'tests_failed': 0,
            'tests': []
        }
    
    def test_checkpoint_exists(self) -> bool:
        """Test that checkpoint directory exists with all files."""
        test_name = "Checkpoint Directory Exists"
        
        if not self.checkpoint_dir.exists():
            self._record_failure(test_name, "Checkpoint directory not found")
            return False
        
        missing_files = []
        for filename in self.REQUIRED_FILES:
            file_path = self.checkpoint_dir / filename
            if not file_path.exists():
                missing_files.append(filename)
        
        if missing_files:
            self._record_failure(
                test_name,
                f"Missing files: {', '.join(missing_files)}"
            )
            return False
        
        self._record_success(test_name, "All checkpoint files present")
        return True
    
    def test_cache_save(self) -> bool:
        """Test saving checkpoint to cache."""
        test_name = "Cache Save"
        
        try:
            # Create cache directory if it doesn't exist
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy checkpoint files to cache
            cache_checkpoint_dir = self.cache_dir / 'freesound_library'
            cache_checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            for filename in self.REQUIRED_FILES:
                src = self.checkpoint_dir / filename
                dst = cache_checkpoint_dir / filename
                
                if not src.exists():
                    self._record_failure(
                        test_name,
                        f"Source file missing: {filename}"
                    )
                    return False
                
                shutil.copy2(src, dst)
            
            self._record_success(test_name, "Checkpoint saved to cache")
            return True
            
        except Exception as e:
            self._record_failure(test_name, f"Failed to save to cache: {e}")
            return False
    
    def test_cache_restore(self) -> bool:
        """Test restoring checkpoint from cache."""
        test_name = "Cache Restore"
        
        try:
            cache_checkpoint_dir = self.cache_dir / 'freesound_library'
            
            if not cache_checkpoint_dir.exists():
                self._record_failure(test_name, "Cache checkpoint directory not found")
                return False
            
            # Verify all files can be read from cache
            for filename in self.REQUIRED_FILES:
                file_path = cache_checkpoint_dir / filename
                
                if not file_path.exists():
                    self._record_failure(test_name, f"Missing file in cache: {filename}")
                    return False
                
                # Try to read file
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                        if len(data) == 0:
                            self._record_failure(test_name, f"Empty file in cache: {filename}")
                            return False
                except Exception as e:
                    self._record_failure(test_name, f"Cannot read file from cache: {filename} - {e}")
                    return False
            
            self._record_success(test_name, "Checkpoint restored from cache")
            return True
            
        except Exception as e:
            self._record_failure(test_name, f"Failed to restore from cache: {e}")
            return False
    
    def test_file_integrity(self) -> bool:
        """Test file integrity after cache round-trip."""
        test_name = "File Integrity"
        
        try:
            cache_checkpoint_dir = self.cache_dir / 'freesound_library'
            
            for filename in self.REQUIRED_FILES:
                original = self.checkpoint_dir / filename
                cached = cache_checkpoint_dir / filename
                
                if not original.exists() or not cached.exists():
                    self._record_failure(test_name, f"File missing: {filename}")
                    return False
                
                # Compare file sizes
                original_size = original.stat().st_size
                cached_size = cached.stat().st_size
                
                if original_size != cached_size:
                    self._record_failure(
                        test_name,
                        f"Size mismatch for {filename}: {original_size} vs {cached_size}"
                    )
                    return False
                
                # Compare file contents
                with open(original, 'rb') as f1, open(cached, 'rb') as f2:
                    if f1.read() != f2.read():
                        self._record_failure(test_name, f"Content mismatch for {filename}")
                        return False
            
            self._record_success(test_name, "All files match after cache round-trip")
            return True
            
        except Exception as e:
            self._record_failure(test_name, f"Failed to verify integrity: {e}")
            return False
    
    def test_metadata_validity(self) -> bool:
        """Test that checkpoint metadata is valid JSON."""
        test_name = "Metadata Validity"
        
        try:
            cache_checkpoint_dir = self.cache_dir / 'freesound_library'
            metadata_file = cache_checkpoint_dir / 'checkpoint_metadata.json'
            
            if not metadata_file.exists():
                self._record_failure(test_name, "Metadata file not found")
                return False
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check required fields
            has_nodes = 'nodes' in metadata or 'total_nodes' in metadata
            has_edges = 'edges' in metadata or 'total_edges' in metadata
            has_timestamp = 'timestamp' in metadata or 'last_updated' in metadata
            
            if not has_nodes:
                self._record_failure(test_name, "Missing node count field")
                return False
            
            if not has_edges:
                self._record_failure(test_name, "Missing edge count field")
                return False
            
            if not has_timestamp:
                self._record_failure(test_name, "Missing timestamp field")
                return False
            
            self._record_success(test_name, "Metadata is valid")
            return True
            
        except json.JSONDecodeError as e:
            self._record_failure(test_name, f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self._record_failure(test_name, f"Failed to validate metadata: {e}")
            return False
    
    def test_repair_workflow_restore(self) -> bool:
        """Simulate repair workflow restoring from cache."""
        test_name = "Repair Workflow Restore"
        
        try:
            # Simulate repair workflow cache key pattern
            # Repair restores: checkpoint-${{ github.event.workflow_run.id }}
            # This should match nightly save: checkpoint-${{ github.run_id }}
            
            cache_checkpoint_dir = self.cache_dir / 'freesound_library'
            
            if not cache_checkpoint_dir.exists():
                self._record_failure(test_name, "Cache not found for repair workflow")
                return False
            
            # Verify all files accessible
            for filename in self.REQUIRED_FILES:
                file_path = cache_checkpoint_dir / filename
                if not file_path.exists() or file_path.stat().st_size == 0:
                    self._record_failure(
                        test_name,
                        f"Repair workflow cannot access: {filename}"
                    )
                    return False
            
            self._record_success(test_name, "Repair workflow can restore from cache")
            return True
            
        except Exception as e:
            self._record_failure(test_name, f"Repair workflow restore failed: {e}")
            return False
    
    def test_validation_workflow_restore(self) -> bool:
        """Simulate validation workflow restoring from cache."""
        test_name = "Validation Workflow Restore"
        
        try:
            # Simulate validation workflow cache key pattern
            # Validation restores: checkpoint-repaired-${{ github.event.workflow_run.id }}
            # This should match repair save: checkpoint-repaired-${{ github.run_id }}
            
            # For this test, we'll use the same cache since we're simulating
            cache_checkpoint_dir = self.cache_dir / 'freesound_library'
            
            if not cache_checkpoint_dir.exists():
                self._record_failure(test_name, "Cache not found for validation workflow")
                return False
            
            # Verify all files accessible
            for filename in self.REQUIRED_FILES:
                file_path = cache_checkpoint_dir / filename
                if not file_path.exists() or file_path.stat().st_size == 0:
                    self._record_failure(
                        test_name,
                        f"Validation workflow cannot access: {filename}"
                    )
                    return False
            
            self._record_success(test_name, "Validation workflow can restore from cache")
            return True
            
        except Exception as e:
            self._record_failure(test_name, f"Validation workflow restore failed: {e}")
            return False
    
    def _record_success(self, test_name: str, message: str):
        """Record a successful test."""
        self.results['tests_passed'] += 1
        self.results['tests'].append({
            'name': test_name,
            'status': 'PASSED',
            'message': message
        })
    
    def _record_failure(self, test_name: str, message: str):
        """Record a failed test."""
        self.results['tests_failed'] += 1
        self.results['tests'].append({
            'name': test_name,
            'status': 'FAILED',
            'message': message
        })
    
    def run_all_tests(self) -> bool:
        """
        Run all cache sharing tests.
        
        Returns:
            True if all tests passed, False otherwise
        """
        print("=" * 80)
        print("CACHE SHARING END-TO-END TEST")
        print("=" * 80)
        print()
        
        # Run tests in order
        tests = [
            self.test_checkpoint_exists,
            self.test_cache_save,
            self.test_cache_restore,
            self.test_file_integrity,
            self.test_metadata_validity,
            self.test_repair_workflow_restore,
            self.test_validation_workflow_restore
        ]
        
        for test_func in tests:
            test_func()
        
        # Print results
        self.print_results()
        
        return self.results['tests_failed'] == 0
    
    def print_results(self):
        """Print test results."""
        print()
        print("=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        print()
        
        for test in self.results['tests']:
            status_emoji = '✅' if test['status'] == 'PASSED' else '❌'
            print(f"{status_emoji} {test['name']}: {test['status']}")
            print(f"   {test['message']}")
            print()
        
        print("-" * 80)
        print(f"Total Tests: {self.results['tests_passed'] + self.results['tests_failed']}")
        print(f"Passed: {self.results['tests_passed']}")
        print(f"Failed: {self.results['tests_failed']}")
        print()
        
        if self.results['tests_failed'] == 0:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        
        print("=" * 80)
    
    def save_results(self, output_file: Path):
        """Save test results to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)
            print(f"✅ Results saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test cache sharing between workflows'
    )
    parser.add_argument(
        'checkpoint_dir',
        type=Path,
        nargs='?',
        default=Path('data/freesound_library'),
        help='Path to checkpoint directory (default: data/freesound_library)'
    )
    parser.add_argument(
        '--cache-dir',
        type=Path,
        help='Path to cache directory (default: temp directory)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Save results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Use temp directory for cache if not specified
    if args.cache_dir:
        cache_dir = args.cache_dir
        cleanup_cache = False
    else:
        cache_dir = Path(tempfile.mkdtemp(prefix='cache_test_'))
        cleanup_cache = True
    
    try:
        # Run tests
        tester = CacheSharingTester(args.checkpoint_dir, cache_dir)
        all_passed = tester.run_all_tests()
        
        # Save results if requested
        if args.output:
            tester.save_results(args.output)
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
        
    finally:
        # Cleanup temp cache directory
        if cleanup_cache and cache_dir.exists():
            shutil.rmtree(cache_dir)


if __name__ == '__main__':
    main()
