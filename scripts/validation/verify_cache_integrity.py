#!/usr/bin/env python3
"""
Cache Integrity Verification Script

Verifies that all required checkpoint files are present after cache save.
Adds checksums and file size verification.
Fails if cache save is incomplete.

Requirements: 13.2, 13.6
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CacheIntegrityVerifier:
    """Verifies cache integrity for checkpoint files."""

    REQUIRED_FILES = [
        "graph_topology.gpickle",
        "metadata_cache.db",
        "checkpoint_metadata.json",
    ]

    def __init__(self, checkpoint_dir: Path):
        """
        Initialize verifier.

        Args:
            checkpoint_dir: Path to checkpoint directory
        """
        self.checkpoint_dir = checkpoint_dir
        self.results = {
            "directory_exists": False,
            "all_files_present": False,
            "all_files_valid": False,
            "files": {},
            "total_size": 0,
            "checksums": {},
            "errors": [],
            "warnings": [],
        }

    def calculate_checksum(self, file_path: Path, algorithm: str = "sha256") -> str:
        """
        Calculate file checksum.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm (default: sha256)

        Returns:
            Hex digest of file checksum
        """
        hash_obj = hashlib.new(algorithm)

        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            self.results["errors"].append(
                f"Failed to calculate checksum for {file_path.name}: {e}"
            )
            return ""

    def verify_file(self, filename: str) -> Dict[str, any]:
        """
        Verify a single file.

        Args:
            filename: Name of file to verify

        Returns:
            Dictionary with file verification results
        """
        file_path = self.checkpoint_dir / filename

        file_info = {
            "exists": False,
            "size": 0,
            "readable": False,
            "non_empty": False,
            "checksum": "",
            "valid": False,
        }

        # Check existence
        if not file_path.exists():
            self.results["errors"].append(f"Missing file: {filename}")
            return file_info

        file_info["exists"] = True

        # Check size
        try:
            stat_info = file_path.stat()
            file_info["size"] = stat_info.st_size

            if stat_info.st_size == 0:
                self.results["errors"].append(f"Empty file: {filename}")
                file_info["non_empty"] = False
            else:
                file_info["non_empty"] = True
        except Exception as e:
            self.results["errors"].append(f"Failed to stat {filename}: {e}")
            return file_info

        # Check readability
        try:
            file_info["readable"] = file_path.is_file() and file_path.stat().st_size > 0
        except Exception as e:
            self.results["errors"].append(
                f"Failed to check readability of {filename}: {e}"
            )
            return file_info

        # Calculate checksum
        if file_info["non_empty"]:
            file_info["checksum"] = self.calculate_checksum(file_path)

        # File is valid if it exists, is non-empty, and is readable
        file_info["valid"] = (
            file_info["exists"] and file_info["non_empty"] and file_info["readable"]
        )

        return file_info

    def verify_checkpoint_metadata(self) -> bool:
        """
        Verify checkpoint metadata file contains required fields.

        Returns:
            True if metadata is valid, False otherwise
        """
        metadata_file = self.checkpoint_dir / "checkpoint_metadata.json"

        if not metadata_file.exists():
            return False

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Check required fields
            has_nodes = "nodes" in metadata
            has_edges = "edges" in metadata
            has_timestamp = "timestamp" in metadata

            if not has_nodes:
                self.results["warnings"].append(
                    "Checkpoint metadata missing node count field"
                )
                return False

            if not has_edges:
                self.results["warnings"].append(
                    "Checkpoint metadata missing edge count field"
                )
                return False

            if not has_timestamp:
                self.results["warnings"].append(
                    "Checkpoint metadata missing timestamp field"
                )
                return False

            # Validate node count
            node_count = metadata.get("nodes", 0)
            if node_count == 0:
                self.results["warnings"].append("Checkpoint has zero nodes")

            return True

        except json.JSONDecodeError as e:
            self.results["errors"].append(
                f"Invalid JSON in checkpoint_metadata.json: {e}"
            )
            return False
        except Exception as e:
            self.results["errors"].append(
                f"Failed to read checkpoint_metadata.json: {e}"
            )
            return False

    def verify(self) -> bool:
        """
        Verify cache integrity.

        Returns:
            True if cache is valid, False otherwise
        """
        # Check directory exists
        if not self.checkpoint_dir.exists():
            self.results["errors"].append(
                f"Checkpoint directory not found: {self.checkpoint_dir}"
            )
            return False

        self.results["directory_exists"] = True

        # Verify each required file
        all_present = True
        all_valid = True
        total_size = 0

        for filename in self.REQUIRED_FILES:
            file_info = self.verify_file(filename)
            self.results["files"][filename] = file_info

            if not file_info["exists"]:
                all_present = False
                all_valid = False
            elif not file_info["valid"]:
                all_valid = False
            else:
                total_size += file_info["size"]
                if file_info["checksum"]:
                    self.results["checksums"][filename] = file_info["checksum"]

        self.results["all_files_present"] = all_present
        self.results["all_files_valid"] = all_valid
        self.results["total_size"] = total_size

        # Verify metadata content
        if all_valid:
            metadata_valid = self.verify_checkpoint_metadata()
            if not metadata_valid:
                all_valid = False

        return all_valid

    def get_results(self) -> Dict[str, any]:
        """Get verification results."""
        return self.results

    def print_report(self, verbose: bool = True):
        """
        Print verification report.

        Args:
            verbose: If True, print detailed information
        """
        print("=" * 80)
        print("CACHE INTEGRITY VERIFICATION REPORT")
        print("=" * 80)
        print()

        # Overall status
        if self.results["all_files_valid"]:
            print("✅ CACHE INTEGRITY: VALID")
        else:
            print("❌ CACHE INTEGRITY: INVALID")
        print()

        # Directory status
        print(f"Directory: {self.checkpoint_dir}")
        print(f"Exists: {'✅' if self.results['directory_exists'] else '❌'}")
        print()

        # File status
        if self.results["directory_exists"]:
            print("Files:")
            for filename, info in self.results["files"].items():
                status = "✅" if info["valid"] else "❌"
                print(f"  {status} {filename}")

                if verbose and info["exists"]:
                    print(f"     Size: {self._format_size(info['size'])}")
                    print(f"     Readable: {'✅' if info['readable'] else '❌'}")
                    print(f"     Non-empty: {'✅' if info['non_empty'] else '❌'}")
                    if info["checksum"]:
                        print(f"     Checksum: {info['checksum'][:16]}...")
                print()

            print(f"Total Size: {self._format_size(self.results['total_size'])}")
            print()

        # Errors
        if self.results["errors"]:
            print("Errors:")
            for error in self.results["errors"]:
                print(f"  ❌ {error}")
            print()

        # Warnings
        if self.results["warnings"]:
            print("Warnings:")
            for warning in self.results["warnings"]:
                print(f"  ⚠️  {warning}")
            print()

        print("=" * 80)

    def save_results(self, output_file: Path):
        """
        Save verification results to JSON file.

        Args:
            output_file: Path to output file
        """
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2)
            print(f"✅ Results saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify cache integrity for checkpoint files"
    )
    parser.add_argument(
        "checkpoint_dir",
        type=Path,
        nargs="?",
        default=Path("data/freesound_library"),
        help="Path to checkpoint directory (default: data/freesound_library)",
    )
    parser.add_argument("--output", type=Path, help="Save results to JSON file")
    parser.add_argument(
        "--quiet", action="store_true", help="Only print summary, not detailed report"
    )

    args = parser.parse_args()

    # Verify cache integrity
    verifier = CacheIntegrityVerifier(args.checkpoint_dir)
    is_valid = verifier.verify()

    # Print report
    verifier.print_report(verbose=not args.quiet)

    # Save results if requested
    if args.output:
        verifier.save_results(args.output)

    # Exit with appropriate code
    if is_valid:
        print("✅ Cache integrity verification PASSED")
        sys.exit(0)
    else:
        print("❌ Cache integrity verification FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
