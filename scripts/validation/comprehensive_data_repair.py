#!/usr/bin/env python3
"""
Comprehensive Data Quality Repair Script.

This script performs a complete data quality audit and repair:
1. Scans ALL samples in the checkpoint
2. Identifies ALL missing or incomplete fields
3. Queues issues by type (up to 150 samples per batch)
4. Fetches missing data using efficient batch API calls
5. Applies fixes across the entire dataset
6. Marks samples as checked if data is unavailable from API

Usage:
    python comprehensive_data_repair.py
    python comprehensive_data_repair.py --checkpoint-dir data/freesound_library
    python comprehensive_data_repair.py --api-key YOUR_KEY --max-requests 100
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import freesound

# Configuration
UPLOADER_ID_PATTERN = re.compile(r"_(\d+)-")
BATCH_SIZE = 150  # Freesound API max page size
REQUESTS_PER_MINUTE = 60

# Define expected fields and their types
EXPECTED_FIELDS = {
    # Critical fields for visualization
    "uploader_id": int,
    "name": str,
    "tags": list,
    "duration": (int, float),
    "username": str,
    
    # Important metadata
    "license": str,
    "created": str,
    "url": str,
    "category": str,
    "type": str,
    "channels": int,
    "filesize": int,
    "samplerate": (int, float),
    
    # Engagement metrics
    "num_downloads": int,
    "num_ratings": int,
    "avg_rating": (int, float),
    "num_comments": int,
    
    # Optional fields
    "description": str,
    "pack": (str, type(None)),
    "geotag": (str, type(None)),
}


class DataQualityIssue:
    """Represents a data quality issue for a sample."""
    
    def __init__(self, sample_id: int, issue_type: str, field_name: str = None):
        self.sample_id = sample_id
        self.issue_type = issue_type  # 'missing_field', 'empty_value', 'invalid_type'
        self.field_name = field_name
    
    def __repr__(self):
        if self.field_name:
            return f"Issue({self.sample_id}, {self.issue_type}, {self.field_name})"
        return f"Issue({self.sample_id}, {self.issue_type})"


class ComprehensiveDataRepairer:
    """Comprehensive data quality checker and repairer."""
    
    def __init__(
        self,
        checkpoint_dir: str,
        api_key: str,
        max_requests: int = 100,
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.db_path = self.checkpoint_dir / "metadata_cache.db"
        self.api_key = api_key
        self.max_requests = max_requests
        self.api_requests_made = 0
        
        # Initialize Freesound client
        self.client = freesound.FreesoundClient()
        self.client.set_token(api_key)
        
        # Statistics
        self.stats = {
            "total_samples": 0,
            "samples_checked": 0,
            "issues_found": 0,
            "issues_fixed": 0,
            "samples_marked_unavailable": 0,
            "api_requests_used": 0,
        }
        
        # Issue queues by type
        self.issue_queues: Dict[str, List[DataQualityIssue]] = defaultdict(list)
    
    def load_env(self):
        """Load environment variables from .env file."""
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
    
    def check_sample_data_quality(self, sample_id: int, data: Dict[str, Any]) -> List[DataQualityIssue]:
        """
        Check a single sample for data quality issues.
        
        Returns list of issues found.
        """
        issues = []
        
        # Skip if already marked as checked and unavailable
        if data.get("data_quality_checked") and data.get("api_data_unavailable"):
            return issues
        
        # Get list of fields marked as missing from Freesound (intentionally empty)
        missing_from_freesound = data.get("_missing_from_freesound", [])
        
        # Check each expected field
        for field_name, expected_type in EXPECTED_FIELDS.items():
            # Skip if field is marked as missing from Freesound
            if field_name in missing_from_freesound:
                continue
            # Check if field exists
            if field_name not in data:
                issues.append(DataQualityIssue(sample_id, "missing_field", field_name))
                continue
            
            value = data[field_name]
            
            # Check if value is empty/None (but not for optional fields)
            if value is None or value == "" or value == [] or value == {}:
                # Some fields can be None
                if expected_type == (str, type(None)) or expected_type == type(None):
                    continue
                issues.append(DataQualityIssue(sample_id, "empty_value", field_name))
                continue
            
            # Check type (basic validation)
            if not isinstance(value, expected_type if isinstance(expected_type, type) else expected_type):
                issues.append(DataQualityIssue(sample_id, "invalid_type", field_name))
        
        return issues
    
    def scan_all_samples(self) -> Tuple[Set[int], Dict[str, Set[int]]]:
        """
        Scan all samples and categorize issues.
        
        First checks if validation already scanned and saved results.
        If so, uses those results to avoid double scanning.
        
        Returns:
            - Set of sample IDs that need repair
            - Dict mapping field names to sample IDs with issues in that field
        """
        print("\n" + "=" * 70)
        print("Phase 1: Data Quality Scan")
        print("=" * 70)
        
        # Check if validation already scanned and saved results
        scan_results_file = self.checkpoint_dir / "data_quality_scan.json"
        if scan_results_file.exists():
            print("\n✓ Using validation scan results (avoiding double scan)")
            with open(scan_results_file) as f:
                scan_data = json.load(f)
            
            samples_needing_repair = set(scan_data["samples_needing_repair"])
            self.stats["total_samples"] = len(samples_needing_repair)
            self.stats["samples_checked"] = len(samples_needing_repair)
            self.stats["issues_found"] = scan_data["total_issues"]
            
            # Convert issues_by_field to proper format
            issues_by_field = {}
            for field, count in scan_data["issues_by_field"].items():
                issues_by_field[field] = set()  # We don't have individual IDs, but that's ok
            
            print(f"\n✓ Loaded scan results: {len(samples_needing_repair)} samples need repair")
            print(f"  Total issues found: {self.stats['issues_found']}")
            print(f"\nIssues by field:")
            for field_name, count in scan_data["issues_by_field"].items():
                print(f"  - {field_name}: {count} samples")
            
            print(f"\n💡 Efficiency: {len(samples_needing_repair)} samples = {(len(samples_needing_repair) + BATCH_SIZE - 1) // BATCH_SIZE} API requests")
            print(f"   (Each request fetches ALL fields for up to {BATCH_SIZE} samples)")
            
            return samples_needing_repair, issues_by_field
        
        # No validation results - do full scan
        print("\n⚠️  No validation scan results found, performing full scan...")
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT sample_id, data FROM metadata")
        rows = cursor.fetchall()
        
        self.stats["total_samples"] = len(rows)
        print(f"\nScanning {len(rows)} samples for data quality issues...")
        
        # Track which samples need repair (efficient: one API call gets ALL fields)
        samples_needing_repair: Set[int] = set()
        
        # Also track issues by field for reporting
        issues_by_field: Dict[str, Set[int]] = defaultdict(set)
        
        for sample_id, data_json in rows:
            data = json.loads(data_json)
            issues = self.check_sample_data_quality(sample_id, data)
            
            if issues:
                # This sample needs repair - add to queue
                samples_needing_repair.add(sample_id)
                
                # Track which fields have issues (for reporting)
                for issue in issues:
                    issues_by_field[issue.field_name].add(sample_id)
            
            self.stats["samples_checked"] += 1
            self.stats["issues_found"] += len(issues)
        
        conn.close()
        
        # Print summary
        print(f"\n✓ Scan complete: {self.stats['samples_checked']} samples checked")
        print(f"  Total issues found: {self.stats['issues_found']}")
        print(f"  Samples needing repair: {len(samples_needing_repair)}")
        print(f"\nIssues by field:")
        for field_name, sample_ids in sorted(issues_by_field.items()):
            print(f"  - {field_name}: {len(sample_ids)} samples")
        
        print(f"\n💡 Efficiency: {len(samples_needing_repair)} samples = {(len(samples_needing_repair) + BATCH_SIZE - 1) // BATCH_SIZE} API requests")
        print(f"   (Each request fetches ALL fields for up to {BATCH_SIZE} samples)")
        
        return samples_needing_repair, issues_by_field
    
    def fetch_batch_data(self, sample_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Fetch data for a batch of samples using efficient batch API.
        
        Returns dict mapping sample_id to fetched data.
        """
        if self.api_requests_made >= self.max_requests:
            print(f"⚠️  Reached max API requests limit ({self.max_requests})")
            return {}
        
        # Build space-separated ID list for batch search
        id_filter = " ".join(str(sid) for sid in sample_ids)
        
        try:
            # Fetch comprehensive metadata fields
            results = self.client.text_search(
                query="",
                filter=f"id:({id_filter})",
                page_size=min(len(sample_ids), BATCH_SIZE),
                fields="id,name,tags,description,duration,username,pack,license,created,url,"
                       "category,type,channels,filesize,samplerate,previews,images,"
                       "num_downloads,avg_rating,num_ratings,num_comments,geotag"
            )
            
            self.api_requests_made += 1
            self.stats["api_requests_used"] += 1
            
            # Extract data from results
            fetched_data = {}
            for sound in results:
                sound_dict = sound.as_dict()
                sample_id = sound.id
                
                # Extract uploader_id from preview URL if available
                if "previews" in sound_dict and sound_dict["previews"]:
                    preview_url = sound_dict["previews"].get("preview-hq-mp3", "")
                    match = UPLOADER_ID_PATTERN.search(preview_url)
                    if match:
                        sound_dict["uploader_id"] = int(match.group(1))
                
                fetched_data[sample_id] = sound_dict
            
            return fetched_data
            
        except Exception as e:
            print(f"  ✗ Batch fetch error: {e}")
            return {}
    
    def apply_fixes(self, samples_needing_repair: Set[int], issues_by_field: Dict[str, Set[int]]):
        """
        Apply fixes for all identified issues using batch API calls.
        
        EFFICIENCY: Groups by sample ID, not field type.
        One API call fetches ALL fields for up to 150 samples.
        
        Example:
        - Node 1 missing fields: 1, 5, 6, 7
        - Node 2 missing fields: 3
        - Node 3 missing fields: 3, 4, 5
        
        Result: 3/150 of one batch (1 API request gets all fields for all 3 nodes)
        """
        print("\n" + "=" * 70)
        print("Phase 2: Apply Fixes (Batch by Sample ID)")
        print("=" * 70)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        total_to_fix = len(samples_needing_repair)
        print(f"\nProcessing {total_to_fix} samples with issues...")
        print(f"Max API requests: {self.max_requests}")
        print(f"Batch size: {BATCH_SIZE} samples per request")
        print(f"Estimated requests needed: {(total_to_fix + BATCH_SIZE - 1) // BATCH_SIZE}")
        
        # Process in batches (grouped by sample ID for maximum efficiency)
        sample_id_list = list(samples_needing_repair)
        fixed_count = 0
        unavailable_count = 0
        
        for batch_start in range(0, len(sample_id_list), BATCH_SIZE):
            if self.api_requests_made >= self.max_requests:
                print(f"\n⚠️  Reached max API requests limit")
                print(f"   Processed {fixed_count + unavailable_count}/{total_to_fix} samples")
                print(f"   Remaining samples will be processed in next run")
                break
            
            batch_end = min(batch_start + BATCH_SIZE, len(sample_id_list))
            batch = sample_id_list[batch_start:batch_end]
            
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (len(sample_id_list) + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Batch {batch_num}/{total_batches}: Fetching {len(batch)} samples...")
            
            # Fetch data for this batch
            fetched_data = self.fetch_batch_data(batch)
            
            # Apply fixes for each sample in batch
            batch_fixed = 0
            batch_unavailable = 0
            
            for sample_id in batch:
                # Get current data
                cursor.execute("SELECT data FROM metadata WHERE sample_id = ?", (sample_id,))
                row = cursor.fetchone()
                if not row:
                    continue
                
                data = json.loads(row[0])
                
                # Check if we got fresh data from API
                if sample_id in fetched_data:
                    fresh_data = fetched_data[sample_id]
                    
                    # Update all missing/empty fields
                    updated = False
                    for field_name in EXPECTED_FIELDS:
                        if field_name in fresh_data and fresh_data[field_name]:
                            # Only update if current value is missing/empty
                            if field_name not in data or not data[field_name]:
                                data[field_name] = fresh_data[field_name]
                                updated = True
                    
                    if updated:
                        data["data_quality_checked"] = datetime.now().isoformat()
                        data["data_quality_repaired"] = True
                        
                        # Update database
                        cursor.execute(
                            "UPDATE metadata SET data = ? WHERE sample_id = ?",
                            (json.dumps(data), sample_id)
                        )
                        batch_fixed += 1
                else:
                    # Sample not found in API or data unavailable
                    # Mark which fields are missing from Freesound
                    missing_fields = []
                    for field_name in EXPECTED_FIELDS:
                        if field_name not in data or not data[field_name]:
                            missing_fields.append(field_name)
                    
                    data["data_quality_checked"] = datetime.now().isoformat()
                    data["api_data_unavailable"] = True
                    data["_missing_from_freesound"] = missing_fields
                    
                    # Update database
                    cursor.execute(
                        "UPDATE metadata SET data = ? WHERE sample_id = ?",
                        (json.dumps(data), sample_id)
                    )
                    batch_unavailable += 1
            
            # Commit after each batch
            conn.commit()
            
            fixed_count += batch_fixed
            unavailable_count += batch_unavailable
            
            print(f"  ✓ Fixed: {batch_fixed}, Unavailable: {batch_unavailable}")
            
            # Rate limit
            time.sleep(60.0 / REQUESTS_PER_MINUTE)
        
        conn.close()
        
        self.stats["issues_fixed"] = fixed_count
        self.stats["samples_marked_unavailable"] = unavailable_count
        
        print(f"\n✓ Repair complete:")
        print(f"  - Fixed: {fixed_count} samples")
        print(f"  - Marked unavailable: {unavailable_count} samples")
    
    def generate_report(self):
        """Generate final repair report."""
        print("\n" + "=" * 70)
        print("Repair Summary")
        print("=" * 70)
        
        print(f"\n📊 Statistics:")
        print(f"  Total samples:           {self.stats['total_samples']}")
        print(f"  Samples checked:         {self.stats['samples_checked']}")
        print(f"  Issues found:            {self.stats['issues_found']}")
        print(f"  Issues fixed:            {self.stats['issues_fixed']}")
        print(f"  Marked unavailable:      {self.stats['samples_marked_unavailable']}")
        print(f"  API requests used:       {self.stats['api_requests_used']}/{self.max_requests}")
        
        if self.stats['issues_fixed'] > 0:
            print(f"\n✅ Successfully repaired {self.stats['issues_fixed']} samples")
        
        if self.stats['samples_marked_unavailable'] > 0:
            print(f"\nℹ️  {self.stats['samples_marked_unavailable']} samples marked as unavailable")
            print("   (data not available from Freesound API)")
        
        remaining_issues = self.stats['issues_found'] - self.stats['issues_fixed'] - self.stats['samples_marked_unavailable']
        if remaining_issues > 0:
            print(f"\n⚠️  {remaining_issues} issues remaining (will be processed in next run)")
    
    def run(self):
        """Run the complete repair process."""
        print("=" * 70)
        print("Comprehensive Data Quality Repair")
        print("=" * 70)
        print(f"\nCheckpoint: {self.checkpoint_dir}")
        print(f"Max API requests: {self.max_requests}")
        
        # Phase 1: Scan all samples
        samples_needing_repair, issues_by_field = self.scan_all_samples()
        
        if self.stats['issues_found'] == 0:
            print("\n✅ No data quality issues found!")
            return 0
        
        # Phase 2: Apply fixes (grouped by sample ID for efficiency)
        self.apply_fixes(samples_needing_repair, issues_by_field)
        
        # Phase 3: Generate report
        self.generate_report()
        
        return 0


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Comprehensive data quality checker and repairer"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="data/freesound_library",
        help="Path to checkpoint directory (default: data/freesound_library)",
    )
    parser.add_argument(
        "--api-key",
        help="Freesound API key (default: from FREESOUND_API_KEY env var)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=100,
        help="Maximum number of API requests (default: 100)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Load environment variables
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    
    # Get API key
    api_key = args.api_key or os.getenv("FREESOUND_API_KEY")
    if not api_key:
        print("✗ FREESOUND_API_KEY not found in arguments or environment")
        print("   Use --api-key or set FREESOUND_API_KEY environment variable")
        return 1
    
    # Check database exists
    db_path = Path(args.checkpoint_dir) / "metadata_cache.db"
    if not db_path.exists():
        print(f"✗ Database not found: {db_path}")
        return 1
    
    # Run repair
    repairer = ComprehensiveDataRepairer(
        checkpoint_dir=args.checkpoint_dir,
        api_key=api_key,
        max_requests=args.max_requests,
    )
    
    return repairer.run()


if __name__ == "__main__":
    sys.exit(main())
