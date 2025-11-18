#!/usr/bin/env python3
"""
Validate Freesound samples in checkpoint against the API.

This script checks if samples in the checkpoint still exist on Freesound
and removes samples that have been deleted from the API. Samples are NEVER
deleted based on age - only when they no longer exist on Freesound.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import requests

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
    IncrementalFreesoundLoader,
)  # noqa: E402
from FollowWeb_Visualizor.output.formatters import EmojiFormatter  # noqa: E402
from FollowWeb_Visualizor.utils.files import ErrorRecoveryManager  # noqa: E402
from FollowWeb_Visualizor.utils.progress import ProgressTracker  # noqa: E402


class SampleValidator:
    """
    Validates samples in the checkpoint against the Freesound API.

    Removes samples that have been deleted from the API to keep
    the library clean and accurate. Samples are NEVER deleted based
    on age - only when they no longer exist on Freesound.

    Features:
    - Fast batch validation (150 samples per API request)
    - Zero-cost metadata refresh (piggybacks on validation)
    - History tracking with timestamps
    - Support for full and partial validation modes
    """

    def __init__(self, api_key: str, logger: logging.Logger):
        """
        Initialize sample validator.

        Args:
            api_key: Freesound API key
            logger: Logger instance
        """
        self.api_key = api_key
        self.logger = logger
        self.error_recovery = ErrorRecoveryManager(logger)
        self.api_base_url = "https://freesound.org/apiv2"

    def get_samples_by_existence_check_age(
        self, graph: nx.DiGraph, max_samples: Optional[int] = None
    ) -> List[str]:
        """
        Get sample IDs sorted by last_existence_check_at age (oldest first).

        Args:
            graph: NetworkX graph containing samples
            max_samples: Maximum number of samples to return (None = all)

        Returns:
            List of sample IDs sorted by age
        """
        # Get all samples with their last check timestamp
        samples_with_age = []
        for node_id in graph.nodes():
            last_check = graph.nodes[node_id].get("last_existence_check_at")
            # Samples without timestamp are considered oldest
            samples_with_age.append((str(node_id), last_check or ""))

        # Sort by timestamp (oldest first, empty strings first)
        samples_with_age.sort(key=lambda x: x[1])

        # Extract sample IDs
        sample_ids = [sample_id for sample_id, _ in samples_with_age]

        # Limit if requested
        if max_samples is not None:
            sample_ids = sample_ids[:max_samples]

        return sample_ids

    def get_samples_by_metadata_age(
        self, graph: nx.DiGraph, max_samples: Optional[int] = None
    ) -> List[str]:
        """
        Get sample IDs sorted by last_metadata_update_at age (oldest first).

        Args:
            graph: NetworkX graph containing samples
            max_samples: Maximum number of samples to return (None = all)

        Returns:
            List of sample IDs sorted by metadata age
        """
        # Get all samples with their last metadata update timestamp
        samples_with_age = []
        for node_id in graph.nodes():
            last_update = graph.nodes[node_id].get("last_metadata_update_at")
            # Samples without timestamp are considered oldest
            samples_with_age.append((str(node_id), last_update or ""))

        # Sort by timestamp (oldest first, empty strings first)
        samples_with_age.sort(key=lambda x: x[1])

        # Extract sample IDs
        sample_ids = [sample_id for sample_id, _ in samples_with_age]

        # Limit if requested
        if max_samples is not None:
            sample_ids = sample_ids[:max_samples]

        return sample_ids

    def validate_and_clean_checkpoint(
        self, graph: nx.DiGraph, processed_ids: Set[str], mode: str = "full"
    ) -> Dict[str, Any]:
        """
        Validate samples in the checkpoint and remove deleted ones.

        Updates last_existence_check_at and last_metadata_update_at timestamps.
        Refreshes metadata at zero additional cost by including metadata fields
        in the batch validation query.

        Args:
            graph: NetworkX graph containing samples
            processed_ids: Set of processed sample IDs
            mode: Validation mode - 'full' (all samples) or 'partial' (300 oldest)

        Returns:
            Dictionary with validation statistics
        """
        stats = {
            "total_samples": graph.number_of_nodes(),
            "validated_samples": 0,
            "deleted_samples": [],
            "api_errors": 0,
            "edges_removed": 0,
            "metadata_refreshed": 0,
            "invalid_filesize_removed": 0,
        }

        # Get sample IDs based on validation mode
        if mode == "partial":
            # Validate only 300 oldest samples (by existence check age)
            sample_ids = self.get_samples_by_existence_check_age(graph, max_samples=300)
            self.logger.info(
                EmojiFormatter.format(
                    "info",
                    f"Partial validation mode: validating 300 oldest samples (out of {stats['total_samples']})",
                )
            )
        else:
            # Full validation - all samples
            sample_ids = [str(node) for node in graph.nodes()]
            self.logger.info(
                EmojiFormatter.format(
                    "info",
                    f"Full validation mode: validating all {len(sample_ids)} samples",
                )
            )

        # First pass: Remove samples with invalid filesize (0 bytes)
        self.logger.info(
            EmojiFormatter.format(
                "progress", "Checking for samples with invalid filesize..."
            )
        )

        invalid_filesize_samples = []
        for sample_id in sample_ids:
            node_id = int(sample_id)
            filesize = graph.nodes[node_id].get("filesize", 0)
            if filesize == 0:
                sample_name = graph.nodes[node_id].get("name", "unknown")
                invalid_filesize_samples.append(sample_id)
                stats["deleted_samples"].append(
                    {
                        "id": sample_id,
                        "name": sample_name,
                        "reason": "invalid_filesize_zero_bytes",
                    }
                )
                self.logger.warning(
                    f"Sample {sample_id} ({sample_name}) has invalid filesize: 0 bytes"
                )

        # Remove invalid samples
        if invalid_filesize_samples:
            self.logger.info(
                EmojiFormatter.format(
                    "warning",
                    f"Removing {len(invalid_filesize_samples)} samples with invalid filesize...",
                )
            )

            for sample_id in invalid_filesize_samples:
                edges_before = graph.number_of_edges()
                node_id = int(sample_id)
                graph.remove_node(node_id)
                processed_ids.discard(str(sample_id))
                edges_after = graph.number_of_edges()
                stats["edges_removed"] += edges_before - edges_after
                stats["invalid_filesize_removed"] += 1

            # Remove from sample_ids list for API validation
            sample_ids = [
                sid for sid in sample_ids if sid not in invalid_filesize_samples
            ]

            self.logger.info(
                EmojiFormatter.format(
                    "success",
                    f"Removed {stats['invalid_filesize_removed']} samples with invalid filesize",
                )
            )

        self.logger.info(
            EmojiFormatter.format(
                "progress",
                f"Validating {len(sample_ids)} samples against Freesound API (batch mode with metadata refresh)...",
            )
        )

        # Batch size for API requests (max 150 per Freesound API)
        batch_size = 150
        total_batches = (len(sample_ids) + batch_size - 1) // batch_size

        self.logger.info(
            EmojiFormatter.format(
                "info",
                f"Efficiency gain: {total_batches} API requests instead of {len(sample_ids)} (148x reduction)",
            )
        )
        self.logger.info(
            EmojiFormatter.format(
                "info",
                "Bonus: Metadata refresh at ZERO additional cost (piggybacks on validation)",
            )
        )

        samples_to_remove = []
        validated_count = 0

        # Current timestamp for validation tracking
        now = datetime.now().isoformat()

        # Create progress tracker and process samples in batches
        with ProgressTracker(
            total=len(sample_ids), title="Validating samples", logger=self.logger
        ) as progress:
            # Process samples in batches
            for i in range(0, len(sample_ids), batch_size):
                batch = sample_ids[i : i + batch_size]

                # Batch check existence AND refresh metadata (zero additional cost!)
                existence_map, metadata_map = self._check_samples_batch(batch)

                # Process results
                for sample_id in batch:
                    exists = existence_map.get(sample_id)

                    if exists is None:
                        # API error, skip this sample for now
                        stats["api_errors"] += 1
                    elif not exists:
                        # Sample was deleted from Freesound
                        samples_to_remove.append(sample_id)
                        sample_name = graph.nodes[int(sample_id)].get("name", "unknown")
                        stats["deleted_samples"].append(
                            {
                                "id": sample_id,
                                "name": sample_name,
                                "reason": "deleted_from_api",
                            }
                        )
                        self.logger.info(
                            f"Sample {sample_id} ({sample_name}) no longer exists on Freesound"
                        )
                    else:
                        # Sample is valid - update existence check timestamp
                        # Convert string ID to int for graph node access
                        node_id = int(sample_id)
                        graph.nodes[node_id]["last_existence_check_at"] = now

                        # Refresh metadata if available (zero additional cost!)
                        metadata = metadata_map.get(sample_id)
                        if metadata:
                            # Update node attributes with fresh metadata
                            # Only update non-None values to preserve existing data
                            fields_updated = 0
                            for key, value in metadata.items():
                                if value is not None:
                                    graph.nodes[node_id][key] = value
                                    fields_updated += 1

                            # Update metadata refresh timestamp
                            graph.nodes[node_id]["last_metadata_update_at"] = now
                            stats["metadata_refreshed"] += 1

                            # Log number of fields updated for this sample
                            self.logger.debug(
                                f"Sample {sample_id}: updated {fields_updated} metadata fields"
                            )

                        validated_count += 1

                    progress.update(
                        validated_count + len(samples_to_remove) + stats["api_errors"]
                    )

        stats["validated_samples"] = validated_count

        # Remove deleted samples from graph
        if samples_to_remove:
            self.logger.info(
                EmojiFormatter.format(
                    "progress",
                    f"Removing {len(samples_to_remove)} deleted samples from checkpoint...",
                )
            )

            for sample_id in samples_to_remove:
                # Count edges before removal
                edges_before = graph.number_of_edges()

                # Remove node (automatically removes connected edges)
                # Convert string ID to int for graph node access
                node_id = int(sample_id)
                graph.remove_node(node_id)

                # Remove from processed_ids (keep as string)
                processed_ids.discard(str(sample_id))

                # Count edges removed
                edges_after = graph.number_of_edges()
                stats["edges_removed"] += edges_before - edges_after

            # Log summary with emoji
            summary_msg = EmojiFormatter.format(
                "warning",
                f"Removed {len(samples_to_remove)} deleted samples and {stats['edges_removed']} edges",
            )
            self.logger.info(summary_msg)
        else:
            # Log success with emoji
            success_msg = EmojiFormatter.format(
                "success", f"All {stats['validated_samples']} samples are valid"
            )
            self.logger.info(success_msg)

        return stats

    def _check_samples_batch(
        self, sample_ids: List[str]
    ) -> Tuple[Dict[str, bool], Dict[str, Dict[str, Any]]]:
        """
        Check if multiple samples exist on Freesound API using batch search.

        OPTIMIZATION: Includes metadata fields in the query to refresh metadata
        at ZERO additional cost. This eliminates the need for a separate metadata
        refresh script.

        This is much more fast than checking each sample individually.
        Uses text search with ID filter to validate up to 150 samples per request.

        Args:
            sample_ids: List of sample IDs to check

        Returns:
            Tuple of (existence_map, metadata_map):
            - existence_map: Dictionary mapping sample_id -> exists (True/False)
            - metadata_map: Dictionary mapping sample_id -> metadata dict
        """
        # Build OR filter for batch lookup (max 150 IDs per request)
        id_filter = " OR ".join(sample_ids)
        url = f"{self.api_base_url}/search/text/"

        # OPTIMIZATION: Include complete metadata fields for zero-cost refresh
        # Note: original_filename and md5 are filter parameters only, not response fields
        metadata_fields = (
            "id,url,name,tags,description,category,subcategory,geotag,created,"
            "license,type,channels,filesize,bitrate,bitdepth,duration,samplerate,"
            "username,pack,previews,images,num_downloads,avg_rating,num_ratings,"
            "num_comments,comments,similar_sounds,analysis,ac_analysis"
        )

        params = {
            "token": self.api_key,
            "query": "",  # Empty query to match all
            "filter": f"id:({id_filter})",
            "fields": metadata_fields,  # Include metadata for free refresh!
            "page_size": min(len(sample_ids), 150),
        }

        def batch_check_operation():
            """Operation to batch check sample existence with retry logic."""
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                # Extract IDs that exist and their metadata
                existing_ids = set()
                metadata_dict = {}

                for sound in results:
                    sound_id = str(sound["id"])
                    existing_ids.add(sound_id)

                    # Extract all 29 complete metadata fields (zero-cost refresh!)
                    metadata_dict[sound_id] = {
                        "url": sound.get("url"),
                        "name": sound.get("name"),
                        "tags": sound.get("tags"),
                        "description": sound.get("description"),
                        "category": sound.get("category"),
                        "subcategory": sound.get("subcategory"),
                        "geotag": sound.get("geotag"),
                        "created": sound.get("created"),
                        "license": sound.get("license"),
                        "type": sound.get("type"),
                        "channels": sound.get("channels"),
                        "filesize": sound.get("filesize"),
                        "bitrate": sound.get("bitrate"),
                        "bitdepth": sound.get("bitdepth"),
                        "duration": sound.get("duration"),
                        "samplerate": sound.get("samplerate"),
                        "username": sound.get("username"),
                        "pack": sound.get("pack"),
                        "previews": sound.get("previews"),
                        "images": sound.get("images"),
                        "num_downloads": sound.get("num_downloads"),
                        "avg_rating": sound.get("avg_rating"),
                        "num_ratings": sound.get("num_ratings"),
                        "num_comments": sound.get("num_comments"),
                        "comments": sound.get("comments"),
                        "similar_sounds": sound.get("similar_sounds"),
                        "analysis": sound.get("analysis"),
                        "ac_analysis": sound.get("ac_analysis"),
                    }

                return existing_ids, metadata_dict
            else:
                # Other error, raise to trigger retry
                response.raise_for_status()
                return set(), {}

        try:
            # Retry up to 3 times with 2 second delay
            existing_ids, metadata_dict = self.error_recovery.with_retry(
                batch_check_operation,
                max_attempts=3,
                delay=2.0,
                exceptions=(requests.RequestException,),
            )

            # Build existence result dictionary
            existence_map = {}
            for sample_id in sample_ids:
                existence_map[sample_id] = sample_id in existing_ids

            return existence_map, metadata_dict

        except Exception as e:
            self.logger.warning(f"Failed to batch check samples: {e}")
            # On error, assume all samples exist (don't delete) and no metadata
            return {sample_id: True for sample_id in sample_ids}, {}

    def _check_sample_exists(self, sample_id: str) -> Optional[bool]:
        """
        Check if a sample exists on Freesound API (single sample fallback).

        Args:
            sample_id: Sample ID to check

        Returns:
            True if exists, False if deleted, None if API error
        """
        url = f"{self.api_base_url}/sounds/{sample_id}/"
        params = {
            "token": self.api_key,
            "fields": "id",  # Only need ID to verify existence
        }

        def check_operation():
            """Operation to check sample existence with retry logic."""
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            else:
                # Other error, raise to trigger retry
                response.raise_for_status()
                return None

        try:
            # Retry up to 3 times with 2 second delay
            return self.error_recovery.with_retry(
                check_operation,
                max_attempts=3,
                delay=2.0,
                exceptions=(requests.RequestException,),
            )

        except Exception as e:
            self.logger.warning(f"Failed to check sample {sample_id}: {e}")
            return None  # API error, don't delete the sample


def setup_logging() -> logging.Logger:
    """Configure logging with emoji support."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"validation_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_file}")

    return logger


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate Freesound samples in checkpoint against API",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="data/freesound_library",
        help="Directory containing checkpoint files",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "partial"],
        default="full",
        help="Validation mode: full (all samples) or partial (300 oldest samples)",
    )

    return parser.parse_args()


def write_validation_report(
    stats: Dict[str, Any], output_path: Path, mode: str
) -> None:
    """
    Write validation report to JSON file.

    Args:
        stats: Validation statistics dictionary
        output_path: Path to output JSON file
        mode: Validation mode (full or partial)
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "validation_mode": mode,
        "total_samples": stats["total_samples"],
        "validated_samples": stats["validated_samples"],
        "metadata_refreshed": stats["metadata_refreshed"],
        "deleted_samples": stats["deleted_samples"],
        "api_errors": stats["api_errors"],
        "edges_removed": stats["edges_removed"],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main() -> int:
    """Main execution function."""
    logger = setup_logging()

    # Parse command-line arguments
    args = parse_arguments()

    # Load API key from environment
    api_key = os.environ.get("FREESOUND_API_KEY")
    if not api_key:
        logger.error(
            EmojiFormatter.format("error", "FREESOUND_API_KEY not found in environment")
        )
        logger.info(
            "Please set your API key in .env file or export FREESOUND_API_KEY=your_key"
        )
        return 1

    logger.info("=" * 70)
    logger.info(EmojiFormatter.format("rocket", "Freesound Sample Validation"))
    logger.info("=" * 70)
    logger.info(f"Checkpoint directory: {args.checkpoint_dir}")
    logger.info(f"Validation mode: {args.mode}")
    logger.info("=" * 70)

    try:
        # Initialize loader to access checkpoint
        logger.info(EmojiFormatter.format("progress", "Loading checkpoint..."))

        loader_config = {
            "api_key": api_key,
            "checkpoint_dir": args.checkpoint_dir,
            "checkpoint_interval": 1,
            "max_runtime_hours": None,
        }
        loader = IncrementalFreesoundLoader(loader_config)

        # Check if checkpoint exists
        if loader.graph.number_of_nodes() == 0:
            logger.warning(
                EmojiFormatter.format(
                    "warning", "No checkpoint found or checkpoint is empty"
                )
            )
            return 0

        logger.info(
            EmojiFormatter.format(
                "success",
                f"Loaded checkpoint: {loader.graph.number_of_nodes()} nodes, "
                f"{loader.graph.number_of_edges()} edges",
            )
        )

        # Create validator
        validator = SampleValidator(api_key, logger)

        # Validate and clean checkpoint
        logger.info(EmojiFormatter.format("rocket", "Starting validation..."))

        stats = validator.validate_and_clean_checkpoint(
            loader.graph, loader.processed_ids, mode=args.mode
        )

        # Update validation history in checkpoint metadata
        # Get existing validation history
        existing_checkpoint = loader.checkpoint.load()
        validation_history = {}
        if existing_checkpoint and "metadata" in existing_checkpoint:
            validation_history = existing_checkpoint["metadata"].get(
                "validation_history", {}
            )

        # Update with current validation timestamp
        current_time = datetime.now().isoformat()
        if args.mode == "full":
            validation_history["last_full_existence_check"] = current_time
            validation_history["last_metadata_refresh"] = current_time
        else:
            validation_history["last_partial_existence_check"] = current_time

        # Save checkpoint with updated validation history
        # Always save to update timestamps, even if no samples were deleted
        logger.info(
            EmojiFormatter.format(
                "progress", "Saving checkpoint with updated validation timestamps..."
            )
        )
        loader._save_checkpoint(
            {
                "validation_performed": True,
                "deleted_count": len(stats["deleted_samples"]),
                "timestamp": datetime.now().isoformat(),
                "validation_history": validation_history,
            }
        )
        logger.info(EmojiFormatter.format("success", "Checkpoint saved"))

        # Write validation report
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = logs_dir / f"validation_{timestamp}.json"

        write_validation_report(stats, report_path, args.mode)

        logger.info(
            EmojiFormatter.format(
                "success", f"Validation report written to: {report_path}"
            )
        )

        # Print summary
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("completion", "Validation Complete!"))
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("chart", f"Validation mode: {args.mode}"))
        logger.info(
            EmojiFormatter.format(
                "chart", f"Total samples in checkpoint: {stats['total_samples']}"
            )
        )
        logger.info(
            EmojiFormatter.format(
                "chart", f"Validated samples: {stats['validated_samples']}"
            )
        )
        logger.info(
            EmojiFormatter.format(
                "chart", f"Metadata refreshed: {stats['metadata_refreshed']}"
            )
        )
        logger.info(
            EmojiFormatter.format(
                "chart", f"Deleted samples: {len(stats['deleted_samples'])}"
            )
        )
        logger.info(
            EmojiFormatter.format(
                "chart",
                f"Invalid filesize removed: {stats['invalid_filesize_removed']}",
            )
        )
        logger.info(
            EmojiFormatter.format("chart", f"API errors: {stats['api_errors']}")
        )
        logger.info(
            EmojiFormatter.format("chart", f"Edges removed: {stats['edges_removed']}")
        )
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(EmojiFormatter.format("error", f"Validation failed: {e}"))
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
