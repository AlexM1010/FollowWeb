#!/usr/bin/env python3
"""
Execute multiple cleanup phases in sequence.

Usage:
    python execute_cleanup_phases.py backup cache_cleanup
    python execute_cleanup_phases.py --dry-run backup cache_cleanup root_cleanup
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
    parser = argparse.ArgumentParser(description="Execute cleanup phases")
    parser.add_argument(
        "phases",
        type=str,
        nargs="+",
        help="Phases to execute (backup, cache_cleanup, root_cleanup, etc.)",
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
        # Parse phases
        phases = []
        for phase_name in args.phases:
            try:
                phase = CleanupPhase(phase_name.lower())
                phases.append(phase)
            except ValueError:
                logger.error(f"Invalid phase: {phase_name}")
                logger.error(f"Valid phases: {', '.join([p.value for p in CleanupPhase])}")
                sys.exit(1)
        
        # Create configuration
        config = CleanupConfig(
            dry_run=args.dry_run,
            create_backup_branch=True,
            backup_branch_name="backup/pre-cleanup",
            phases_to_execute=[p.value for p in phases],
        )
        
        # Create orchestrator
        orchestrator = CleanupOrchestrator(
            config=config,
            project_root=args.project_root,
        )
        
        # Execute phases
        logger.info(f"Executing {len(phases)} phases: {', '.join([p.value for p in phases])}")
        
        for phase in phases:
            logger.info(f"\n{'='*80}")
            logger.info(f"Executing phase: {phase.value}")
            logger.info(f"{'='*80}\n")
            
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
                
                logger.error("Stopping execution due to phase failure")
                sys.exit(1)
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info(f"All {len(phases)} phases completed successfully!")
        logger.info(f"{'='*80}\n")
            
    except Exception as e:
        logger.error(f"Error executing phases: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
