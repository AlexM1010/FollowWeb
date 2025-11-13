#!/usr/bin/env python3
"""
Execute cleanup phase script.

Usage:
    python execute_cleanup_phase.py backup
    python execute_cleanup_phase.py cache_cleanup
    python execute_cleanup_phase.py --dry-run backup
"""

import argparse
import logging
import sys
from pathlib import Path

# Add analysis_tools to path
sys.path.insert(0, str(Path(__file__).parent))

from analysis_tools.cleanup.models import CleanupConfig, CleanupPhase
from analysis_tools.cleanup.orchestrator import CleanupOrchestrator


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Execute cleanup phase")
    parser.add_argument(
        "phase",
        type=str,
        help="Phase to execute (backup, cache_cleanup, root_cleanup, etc.)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Path to project root",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Parse phase
        phase = CleanupPhase(args.phase.lower())
        
        # Create configuration
        config = CleanupConfig(
            dry_run=args.dry_run,
            create_backup_branch=True,
            backup_branch_name="backup/pre-cleanup",
        )
        
        # Create orchestrator
        orchestrator = CleanupOrchestrator(
            config=config,
            project_root=args.project_root,
        )
        
        # Execute phase
        logger.info(f"Executing phase: {phase.value}")
        result = orchestrator.execute_phase(phase, dry_run=args.dry_run)
        
        # Print result
        if result.success:
            logger.info(f"✓ Phase {phase.value} completed successfully")
            logger.info(f"  Duration: {result.duration.total_seconds():.2f}s")
            logger.info(f"  Operations: {len(result.operations)}")
            
            if result.warnings:
                logger.warning(f"  Warnings: {len(result.warnings)}")
                for warning in result.warnings:
                    logger.warning(f"    - {warning}")
        else:
            logger.error(f"✗ Phase {phase.value} failed")
            logger.error(f"  Errors: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"    - {error}")
            sys.exit(1)
            
    except ValueError as e:
        logger.error(f"Invalid phase: {args.phase}")
        logger.error(f"Valid phases: {', '.join([p.value for p in CleanupPhase])}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error executing phase: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
