"""
Failure handling utilities for workflow coordination.

This module provides failure flag management to coordinate workflow execution
and prevent cascading failures.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class FailureHandler:
    """
    Manages failure flags for workflow coordination.

    Failure flags are stored in a JSON file and include:
    - workflow_name: Name of the workflow that failed
    - run_id: GitHub Actions run ID
    - error_message: Error description
    - timestamp: When the failure occurred
    - data_preserved: Whether data was saved before failing
    """

    def __init__(self, flag_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Initialize failure handler.

        Args:
            flag_dir: Directory to store failure flags
            logger: Optional logger instance
        """
        self.flag_dir = flag_dir
        self.flag_dir.mkdir(parents=True, exist_ok=True)
        self.flag_file = self.flag_dir / "failure_flags.json"
        self.logger = logger or logging.getLogger(__name__)

    def set_failure_flag(
        self,
        workflow_name: str,
        run_id: str,
        error_message: str,
        data_preserved: bool = False,
        additional_info: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Set a failure flag for workflow coordination.

        Args:
            workflow_name: Name of the workflow that failed
            run_id: GitHub Actions run ID
            error_message: Error description
            data_preserved: Whether data was saved before failing
            additional_info: Optional additional diagnostic information
        """
        flag_data = {
            "workflow_name": workflow_name,
            "run_id": run_id,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_preserved": data_preserved,
        }

        if additional_info:
            flag_data["additional_info"] = additional_info

        try:
            with open(self.flag_file, "w") as f:
                json.dump(flag_data, f, indent=2)
            self.logger.error(f"🚩 Failure flag set: {workflow_name} (run: {run_id})")
        except Exception as e:
            self.logger.error(f"Failed to set failure flag: {e}")

    def check_failure_flag(self) -> tuple[bool, Optional[dict[str, Any]]]:
        """
        Check if a failure flag exists.

        Returns:
            Tuple of (flag_exists: bool, flag_data: Optional[dict])
        """
        if not self.flag_file.exists():
            return False, None

        try:
            with open(self.flag_file) as f:
                flag_data = json.load(f)
            return True, flag_data
        except Exception as e:
            self.logger.error(f"Failed to read failure flag: {e}")
            return False, None

    def clear_failure_flag(self) -> None:
        """Clear the failure flag after successful recovery."""
        if self.flag_file.exists():
            try:
                self.flag_file.unlink()
                self.logger.info("✅ Failure flag cleared")
            except Exception as e:
                self.logger.error(f"Failed to clear failure flag: {e}")

    def get_skip_reason(self) -> Optional[str]:
        """
        Get a formatted skip reason if failure flag exists.

        Returns:
            Skip reason string or None if no flag exists
        """
        flag_exists, flag_data = self.check_failure_flag()

        if not flag_exists or not flag_data:
            return None

        workflow_name = flag_data.get("workflow_name", "unknown")
        error_message = flag_data.get("error_message", "unknown error")
        timestamp = flag_data.get("timestamp", "unknown time")
        data_preserved = flag_data.get("data_preserved", False)

        skip_reason = (
            f"Skipping execution due to upstream failure in {workflow_name}\n"
            f"Error: {error_message}\n"
            f"Time: {timestamp}\n"
            f"Data preserved: {data_preserved}"
        )

        return skip_reason
