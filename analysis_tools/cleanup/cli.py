"""
Command-line interface for repository cleanup operations.

Provides a comprehensive CLI for executing cleanup phases, managing
configuration, and monitoring progress. Supports dry-run mode, phase
selection, and configuration file loading.

Usage:
    python -m analysis_tools.cleanup --help
    python -m analysis_tools.cleanup analyze
    python -m analysis_tools.cleanup execute --phase root_cleanup
    python -m analysis_tools.cleanup execute --all --dry-run
    python -m analysis_tools.cleanup rollback --phase root_cleanup
    python -m analysis_tools.cleanup validate
"""

import argparse
import json
import logging
import sys
from datetime import timedelta
from pathlib import Path
from typing import Optional

from .models import CleanupConfig, CleanupPhase
from .orchestrator import CleanupOrchestrator

# Import EmojiFormatter from FollowWeb package if available
try:
    from FollowWeb.FollowWeb_Visualizor.output.formatters import EmojiFormatter
    from FollowWeb.FollowWeb_Visualizor.utils.progress import ProgressTracker
    
    EMOJI_AVAILABLE = True
except ImportError:
    EMOJI_AVAILABLE = False
    
    # Fallback implementations
    class EmojiFormatter:
        """Minimal fallback emoji formatter."""
        
        @classmethod
        def format(cls, emoji_key: str, message: str) -> str:
            """Format message without emojis."""
            return message
        
        @classmethod
        def safe_print(cls, emoji_key: str, message: str) -> None:
            """Print message without emojis."""
            print(message)
    
    class ProgressTracker:
        """Minimal fallback progress tracker."""
        
        def __init__(self, total: int, title: str = "Progress"):
            self.total = total
            self.title = title
            self.current = 0
        
        def __enter__(self):
            print(f"{self.title}: 0/{self.total}")
            return self
        
        def __exit__(self, *args):
            print(f"{self.title}: {self.current}/{self.total} - Complete")
        
        def update(self, current: int):
            self.current = current
            if current % 100 == 0 or current == self.total:
                print(f"{self.title}: {current}/{self.total}")


def load_config_file(config_path: str) -> CleanupConfig:
    """
    Load cleanup configuration from JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        CleanupConfig instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(path, 'r') as f:
            config_data = json.load(f)
        
        # Convert phase names to list if needed
        if 'phases_to_execute' in config_data:
            phases = config_data['phases_to_execute']
            if isinstance(phases, str):
                config_data['phases_to_execute'] = [phases]
        
        return CleanupConfig(**config_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except TypeError as e:
        raise ValueError(f"Invalid configuration format: {e}")


def create_default_config(output_path: str) -> None:
    """
    Create a default configuration file.
    
    Args:
        output_path: Path where config file should be created
    """
    config = CleanupConfig()
    
    # Convert to dictionary
    config_dict = {
        'dry_run': config.dry_run,
        'create_backup_branch': config.create_backup_branch,
        'backup_branch_name': config.backup_branch_name,
        'phases_to_execute': config.phases_to_execute,
        'skip_validation': config.skip_validation,
        'auto_commit': config.auto_commit,
        'docs_structure': config.docs_structure,
        'scripts_structure': config.scripts_structure,
        'empty_files': config.empty_files,
        'obsolete_files': config.obsolete_files,
        'gitignore_patterns': config.gitignore_patterns,
        'workflow_schedule_offset_minutes': config.workflow_schedule_offset_minutes,
        'required_secrets': config.required_secrets,
        'git_batch_size': config.git_batch_size,
        'max_workers': config.max_workers,
        'file_batch_size': config.file_batch_size,
        'parallel_chunk_size': config.parallel_chunk_size,
        'large_scale_threshold': config.large_scale_threshold,
        'use_state_db': config.use_state_db,
        'enable_checkpoints': config.enable_checkpoints,
        'checkpoint_interval': config.checkpoint_interval,
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    EmojiFormatter.safe_print("success", f"Default configuration created: {output_path}")
    print("\nEdit this file to customize cleanup behavior, then run:")
    print(f"  python -m analysis_tools.cleanup execute --config {output_path}")


def analyze_command(args: argparse.Namespace) -> int:
    """
    Execute analyze command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    EmojiFormatter.safe_print("search", "Analyzing repository for cleanup opportunities...")
    
    try:
        # Load configuration
        if args.config:
            config = load_config_file(args.config)
        else:
            config = CleanupConfig(dry_run=True)  # Analysis is always dry-run
        
        # Initialize orchestrator
        orchestrator = CleanupOrchestrator(
            config=config,
            project_root=args.project_root,
        )
        
        # Run analysis
        EmojiFormatter.safe_print("progress", "Scanning repository structure...")
        analysis_result = orchestrator.analyze_repository()
        
        # Display results
        print("\n" + "=" * 60)
        print("CLEANUP ANALYSIS RESULTS")
        print("=" * 60)
        
        print("\nRoot Directory:")
        print(f"  Files: {analysis_result['root_file_count']}")
        print("  Target: < 15 files")
        print(f"  Reduction needed: {max(0, analysis_result['root_file_count'] - 15)} files")
        
        print("\nCache Directories:")
        print(f"  Size: {analysis_result['cache_size_mb']:.1f} MB")
        print(f"  Directories: {len(analysis_result['cache_dirs'])}")
        
        print("\nUtility Scripts:")
        print(f"  Count: {analysis_result['script_count']}")
        print(f"  Uncategorized: {analysis_result['uncategorized_scripts']}")
        
        print("\nDocumentation:")
        print(f"  Files: {analysis_result['doc_count']}")
        print(f"  Duplicates: {analysis_result['duplicate_docs']}")
        
        print("\nBranches:")
        print(f"  Total: {analysis_result['branch_count']}")
        print(f"  Merged: {analysis_result['merged_branches']}")
        print(f"  Stale: {analysis_result['stale_branches']}")
        
        print("\nWorkflows:")
        print(f"  Total: {analysis_result['workflow_count']}")
        print(f"  Failing: {analysis_result['failing_workflows']}")
        print(f"  Path updates needed: {analysis_result['workflows_needing_updates']}")
        
        print("\n" + "=" * 60)
        print(f"Report saved to: {analysis_result['report_path']}")
        print("=" * 60)
        
        EmojiFormatter.safe_print("success", "Analysis complete!")
        return 0
        
    except Exception as e:
        EmojiFormatter.safe_print("error", f"Analysis failed: {e}")
        logging.exception("Analysis error")
        return 1


def execute_command(args: argparse.Namespace) -> int:
    """
    Execute cleanup phases.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Load configuration
    try:
        if args.config:
            config = load_config_file(args.config)
        else:
            config = CleanupConfig()
        
        # Override config with command-line arguments
        if args.dry_run:
            config.dry_run = True
        if args.no_backup:
            config.create_backup_branch = False
        if args.skip_validation:
            config.skip_validation = True
        if args.no_commit:
            config.auto_commit = False
        
        # Determine phases to execute
        if args.all:
            config.phases_to_execute = ["all"]
        elif args.phase:
            config.phases_to_execute = [args.phase]
        
    except Exception as e:
        EmojiFormatter.safe_print("error", f"Configuration error: {e}")
        return 1
    
    # Display execution plan
    print("\n" + "=" * 60)
    print("CLEANUP EXECUTION PLAN")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if config.dry_run else 'LIVE EXECUTION'}")
    print(f"Backup branch: {'Yes' if config.create_backup_branch else 'No'}")
    print(f"Auto-commit: {'Yes' if config.auto_commit else 'No'}")
    print(f"Validation: {'Skipped' if config.skip_validation else 'Enabled'}")
    
    if config.phases_to_execute == ["all"]:
        print("Phases: All phases")
    else:
        print(f"Phases: {', '.join(config.phases_to_execute)}")
    
    print("=" * 60)
    
    if not config.dry_run and not args.yes:
        response = input("\nProceed with cleanup? [y/N]: ")
        if response.lower() != 'y':
            print("Cleanup cancelled.")
            return 0
    
    # Execute cleanup
    try:
        EmojiFormatter.safe_print("rocket", "Starting cleanup operations...")
        
        orchestrator = CleanupOrchestrator(
            config=config,
            project_root=args.project_root,
        )
        
        # Execute phases
        if config.phases_to_execute == ["all"]:
            result = orchestrator.execute_all_phases()
        else:
            results = []
            for phase_name in config.phases_to_execute:
                try:
                    phase = CleanupPhase(phase_name)
                    result = orchestrator.execute_phase(phase)
                    results.append(result)
                except ValueError:
                    EmojiFormatter.safe_print("error", f"Invalid phase: {phase_name}")
                    return 1
            
            # Combine results
            result = {
                'success': all(r.success for r in results),
                'phases': results,
                'total_duration': sum((r.duration for r in results), start=timedelta()),
            }
        
        # Display results
        print("\n" + "=" * 60)
        print("CLEANUP RESULTS")
        print("=" * 60)
        
        if result['success']:
            EmojiFormatter.safe_print("success", "All phases completed successfully!")
        else:
            EmojiFormatter.safe_print("warning", "Some phases failed or had warnings")
        
        print(f"\nTotal duration: {result['total_duration']}")
        print(f"Report: {result.get('report_path', 'N/A')}")
        
        if config.dry_run:
            print("\nDRY RUN MODE: No changes were made")
            print("Run without --dry-run to apply changes")
        
        print("=" * 60)
        
        return 0 if result['success'] else 1
        
    except Exception as e:
        EmojiFormatter.safe_print("error", f"Cleanup failed: {e}")
        logging.exception("Cleanup error")
        return 1


def rollback_command(args: argparse.Namespace) -> int:
    """
    Rollback a cleanup phase.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not args.phase:
        EmojiFormatter.safe_print("error", "Error: --phase required for rollback")
        return 1
    
    try:
        phase = CleanupPhase(args.phase)
    except ValueError:
        EmojiFormatter.safe_print("error", f"Invalid phase: {args.phase}")
        return 1
    
    EmojiFormatter.safe_print("progress", f"Rolling back phase: {phase.value}")
    
    if not args.yes:
        response = input(f"\nRollback {phase.value}? This will revert all changes. [y/N]: ")
        if response.lower() != 'y':
            print("Rollback cancelled.")
            return 0
    
    try:
        config = CleanupConfig()
        orchestrator = CleanupOrchestrator(
            config=config,
            project_root=args.project_root,
        )
        
        success = orchestrator.rollback_phase(phase)
        
        if success:
            EmojiFormatter.safe_print("success", f"Phase {phase.value} rolled back successfully")
            return 0
        else:
            EmojiFormatter.safe_print("error", f"Rollback failed for phase {phase.value}")
            return 1
            
    except Exception as e:
        EmojiFormatter.safe_print("error", f"Rollback failed: {e}")
        logging.exception("Rollback error")
        return 1


def validate_command(args: argparse.Namespace) -> int:
    """
    Validate cleanup environment and prerequisites.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    EmojiFormatter.safe_print("search", "Validating cleanup environment...")
    
    try:
        config = CleanupConfig()
        orchestrator = CleanupOrchestrator(
            config=config,
            project_root=args.project_root,
        )
        
        validation_result = orchestrator.validate_environment()
        
        print("\n" + "=" * 60)
        print("ENVIRONMENT VALIDATION")
        print("=" * 60)
        
        print("\nGit Repository:")
        print(f"  Status: {'✓' if validation_result['git_repo'] else '✗'}")
        print(f"  Clean working tree: {'✓' if validation_result['clean_working_tree'] else '✗'}")
        
        print("\nRequired Tools:")
        for tool, available in validation_result['tools'].items():
            print(f"  {tool}: {'✓' if available else '✗'}")
        
        print("\nSecrets:")
        for secret, configured in validation_result['secrets'].items():
            print(f"  {secret}: {'✓' if configured else '✗'}")
        
        print("\nDisk Space:")
        print(f"  Available: {validation_result['disk_space_gb']:.1f} GB")
        print("  Required: 1.0 GB")
        print(f"  Status: {'✓' if validation_result['disk_space_gb'] >= 1.0 else '✗'}")
        
        print("\n" + "=" * 60)
        
        if validation_result['success']:
            EmojiFormatter.safe_print("success", "Environment validation passed!")
            return 0
        else:
            EmojiFormatter.safe_print("warning", "Environment validation failed")
            print("\nFix the issues above before running cleanup.")
            return 1
            
    except Exception as e:
        EmojiFormatter.safe_print("error", f"Validation failed: {e}")
        logging.exception("Validation error")
        return 1


def list_phases_command(args: argparse.Namespace) -> int:
    """
    List all available cleanup phases.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (always 0)
    """
    print("\n" + "=" * 60)
    print("AVAILABLE CLEANUP PHASES")
    print("=" * 60)
    
    phases = [
        ("backup", "Create backup branch before cleanup"),
        ("cache_cleanup", "Remove cache directories from version control"),
        ("root_cleanup", "Move documentation files to organized structure"),
        ("script_organization", "Organize utility scripts by category"),
        ("doc_consolidation", "Eliminate duplicate documentation"),
        ("branch_cleanup", "Remove stale and merged branches"),
        ("workflow_update", "Update workflow files with new paths"),
        ("workflow_optimization", "Fix workflow failures and optimize schedules"),
        ("ci_parallelization", "Optimize CI matrix parallelization"),
        ("code_quality", "Remediate code quality issues"),
        ("code_review_integration", "Integrate automated code review tools"),
        ("validation", "Comprehensive validation of all changes"),
        ("documentation", "Generate comprehensive documentation"),
    ]
    
    for phase_name, description in phases:
        print(f"\n{phase_name}")
        print(f"  {description}")
    
    print("\n" + "=" * 60)
    print("\nUsage:")
    print("  python -m analysis_tools.cleanup execute --phase <phase_name>")
    print("  python -m analysis_tools.cleanup execute --all")
    print("=" * 60)
    
    return 0


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for cleanup CLI.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Repository cleanup and organization tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze repository
  python -m analysis_tools.cleanup analyze
  
  # Execute specific phase (dry-run)
  python -m analysis_tools.cleanup execute --phase root_cleanup --dry-run
  
  # Execute all phases
  python -m analysis_tools.cleanup execute --all --yes
  
  # Rollback a phase
  python -m analysis_tools.cleanup rollback --phase root_cleanup
  
  # Validate environment
  python -m analysis_tools.cleanup validate
  
  # List available phases
  python -m analysis_tools.cleanup list-phases
  
  # Create default config
  python -m analysis_tools.cleanup create-config cleanup_config.json
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze repository for cleanup opportunities'
    )
    analyze_parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    analyze_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)'
    )
    
    # Execute command
    execute_parser = subparsers.add_parser(
        'execute',
        help='Execute cleanup phases'
    )
    execute_parser.add_argument(
        '--phase',
        type=str,
        help='Specific phase to execute'
    )
    execute_parser.add_argument(
        '--all',
        action='store_true',
        help='Execute all phases'
    )
    execute_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate operations without making changes'
    )
    execute_parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    execute_parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backup branch creation'
    )
    execute_parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation checks'
    )
    execute_parser.add_argument(
        '--no-commit',
        action='store_true',
        help='Do not auto-commit changes'
    )
    execute_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompts'
    )
    execute_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)'
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser(
        'rollback',
        help='Rollback a cleanup phase'
    )
    rollback_parser.add_argument(
        '--phase',
        type=str,
        required=True,
        help='Phase to rollback'
    )
    rollback_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )
    rollback_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate cleanup environment and prerequisites'
    )
    validate_parser.add_argument(
        '--project-root',
        type=str,
        help='Project root directory (default: current directory)'
    )
    
    # List phases command
    subparsers.add_parser(
        'list-phases',
        help='List all available cleanup phases'
    )
    
    # Create config command
    config_parser = subparsers.add_parser(
        'create-config',
        help='Create default configuration file'
    )
    config_parser.add_argument(
        'output',
        type=str,
        help='Output path for configuration file'
    )
    
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """
    Main entry point for cleanup CLI.
    
    Args:
        argv: Command-line arguments (None = sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Execute command
    if not args.command:
        parser.print_help()
        return 0
    
    if args.command == 'analyze':
        return analyze_command(args)
    elif args.command == 'execute':
        return execute_command(args)
    elif args.command == 'rollback':
        return rollback_command(args)
    elif args.command == 'validate':
        return validate_command(args)
    elif args.command == 'list-phases':
        return list_phases_command(args)
    elif args.command == 'create-config':
        create_default_config(args.output)
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
