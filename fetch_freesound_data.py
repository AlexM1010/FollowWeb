#!/usr/bin/env python3
"""
Standalone script for fetching and saving Freesound graphs with recursive discovery.

This script provides a command-line interface for building Freesound audio sample
graphs using recursive similarity-based discovery. It leverages the IncrementalFreesoundLoader
with queue-based BFS and two-pass processing to ensure all edges are preserved correctly.

Features:
    - Recursive similar sounds discovery (snowball sampling)
    - Queue-based breadth-first traversal for predictable memory usage
    - Two-pass processing to preserve all edges correctly
    - Checkpoint-based resumable fetching for crash recovery
    - Configurable depth limits and sample counts
    - Time-limited execution with graceful stopping
    - Saves graphs to standard output directory for later visualization

Basic Usage:
    # Fetch jungle samples with 1 level of recursion (20 total samples)
    python fetch_freesound_data.py --query "jungle" --depth 1 --max-samples 20
    
    # Fetch drum samples with 2 levels of recursion (100 total samples)
    python fetch_freesound_data.py --query "drum" --depth 2 --max-samples 100

Advanced Usage:
    # Custom checkpoint directory for resumable fetching
    python fetch_freesound_data.py --query "ambient" --depth 1 --max-samples 50 \\
        --checkpoint-dir "my_checkpoints"
    
    # Time-limited fetch (stops gracefully after 1.5 hours)
    python fetch_freesound_data.py --query "bass" --depth 2 --max-samples 200 \\
        --max-runtime 1.5
    
    # Custom output directory and checkpoint interval
    python fetch_freesound_data.py --query "synth" --depth 1 --max-samples 100 \\
        --output-dir "Output/freesound_graphs" \\
        --checkpoint-interval 25
    
    # Provide API key via command line
    python fetch_freesound_data.py --query "percussion" --depth 1 --max-samples 30 \\
        --api-key "your_api_key_here"

Recursive Depth Explanation:
    - depth=0: No recursion, only fetch seed samples from search query
    - depth=1: Fetch seed samples + their similar sounds (2 levels total)
    - depth=2: Fetch seed + similar + similar-to-similar (3 levels total)
    - depth=N: Fetch N+1 levels of samples via similarity relationships

Output:
    Saves a NetworkX DiGraph to Output/ directory with filename format:
        freesound_{query}_depth{depth}_k{max_samples}_{timestamp}.pkl
    
    Load the graph for visualization:
        import joblib
        graph = joblib.load('Output/freesound_jungle_depth1_k20_20251110_123456.pkl')

Requirements:
    - Freesound API key (via --api-key, FREESOUND_API_KEY env var, or GitHub Secrets)
    - FollowWeb package installed (pip install -e FollowWeb/)
    - Python 3.9+ with networkx, joblib, and other dependencies

API Key Setup:
    # Option 1: Environment variable (recommended)
    export FREESOUND_API_KEY="your_api_key_here"
    python fetch_freesound_data.py --query "drum" --depth 1 --max-samples 20
    
    # Option 2: Command-line argument
    python fetch_freesound_data.py --query "drum" --depth 1 --max-samples 20 \\
        --api-key "your_api_key_here"
    
    # Option 3: GitHub Secrets (for CI/CD)
    # Set FREESOUND_API_KEY in repository secrets, automatically available in workflows

Checkpoint Recovery:
    If the script is interrupted (Ctrl+C, crash, time limit), it saves a checkpoint.
    Simply re-run the same command to resume from the last checkpoint:
    
    # First run (interrupted after 50 samples)
    python fetch_freesound_data.py --query "drum" --depth 2 --max-samples 100
    
    # Resume from checkpoint (continues from sample 51)
    python fetch_freesound_data.py --query "drum" --depth 2 --max-samples 100
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional

import joblib

# Import validation utilities
from FollowWeb.FollowWeb_Visualizor.utils.validation import (
    validate_non_empty_string,
    validate_path_string,
    validate_positive_integer,
)

# Import file utilities
from FollowWeb.FollowWeb_Visualizor.utils.files import (
    ensure_output_directory,
    error_context,
    generate_output_filename,
)

# Import math utilities
from FollowWeb.FollowWeb_Visualizor.utils.math import format_time_duration

# Import EmojiFormatter
from FollowWeb.FollowWeb_Visualizor.output.formatters import EmojiFormatter

# Import IncrementalFreesoundLoader
from FollowWeb.FollowWeb_Visualizor.data.loaders.incremental_freesound import (
    IncrementalFreesoundLoader,
)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure logging for the fetch script.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    # Create handlers with UTF-8 encoding for emoji support
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set UTF-8 encoding for Windows console
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    file_handler = logging.FileHandler(
        f'fetch_freesound_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    
    return logger


def load_api_key(cli_key: Optional[str] = None) -> str:
    """
    Load Freesound API key from multiple sources in priority order.
    
    Priority:
        1. Command-line argument (--api-key)
        2. Environment variable (FREESOUND_API_KEY)
        3. GitHub Secrets (for CI/CD environments)
    
    Args:
        cli_key: API key from command-line argument
    
    Returns:
        API key string
    
    Raises:
        ValueError: If no API key found in any source
    """
    # Priority 1: CLI argument
    if cli_key:
        return cli_key
    
    # Priority 2: Environment variable
    env_key = os.environ.get('FREESOUND_API_KEY')
    if env_key:
        return env_key
    
    # Priority 3: GitHub Secrets (same env var name in CI)
    # GitHub Actions automatically sets secrets as environment variables
    github_key = os.environ.get('FREESOUND_API_KEY')
    if github_key:
        return github_key
    
    raise ValueError(
        "Freesound API key not found. Please provide via:\n"
        "  1. --api-key command-line argument\n"
        "  2. FREESOUND_API_KEY environment variable\n"
        "  3. GitHub Secrets (for CI/CD)"
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Fetch and save Freesound audio sample graphs with recursive discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic fetch with 1 level of recursion
  python fetch_freesound_data.py --query "jungle" --depth 1 --max-samples 20

  # Deep fetch with custom checkpoint directory
  python fetch_freesound_data.py --query "drum" --depth 2 --max-samples 100 \\
      --checkpoint-dir "my_checkpoints"

  # Fetch with time limit and custom output directory
  python fetch_freesound_data.py --query "ambient" --depth 1 --max-samples 50 \\
      --max-runtime 1.5 --output-dir "Output/freesound_graphs"

  # Fetch with API key from command line
  python fetch_freesound_data.py --query "bass" --depth 1 --max-samples 30 \\
      --api-key "your_api_key_here"
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--query',
        type=str,
        required=True,
        help='Search query for Freesound samples (e.g., "jungle", "drum")'
    )
    
    # Recursive fetching parameters
    parser.add_argument(
        '--depth',
        type=int,
        default=1,
        help='Recursive depth for similar sounds discovery (default: 1)'
    )
    
    parser.add_argument(
        '--max-samples',
        type=int,
        default=100,
        help='Maximum total samples to fetch including recursive discovery (default: 100)'
    )
    
    # Checkpoint configuration
    parser.add_argument(
        '--checkpoint-dir',
        type=str,
        default='checkpoints',
        help='Directory for checkpoint files (default: checkpoints)'
    )
    
    parser.add_argument(
        '--checkpoint-interval',
        type=int,
        default=50,
        help='Number of samples between checkpoint saves (default: 50)'
    )
    
    # Output configuration
    parser.add_argument(
        '--output-dir',
        type=str,
        default='Output',
        help='Directory for output graph files (default: Output)'
    )
    
    # Runtime limits
    parser.add_argument(
        '--max-runtime',
        type=float,
        default=None,
        help='Maximum runtime in hours before graceful stop (default: no limit)'
    )
    
    # API configuration
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='Freesound API key (or use FREESOUND_API_KEY env var)'
    )
    
    # Logging configuration
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    return parser.parse_args()


def validate_arguments(args: argparse.Namespace, logger: logging.Logger) -> None:
    """
    Validate command-line arguments using existing validators.
    
    Args:
        args: Parsed arguments
        logger: Logger instance
    
    Raises:
        ValueError: If any argument is invalid
    """
    with error_context("argument validation", logger):
        # Validate query
        validate_non_empty_string(args.query, "query")
        
        # Validate depth
        validate_positive_integer(args.depth, "depth")
        
        # Validate max_samples
        validate_positive_integer(args.max_samples, "max_samples")
        
        # Validate checkpoint_interval
        validate_positive_integer(args.checkpoint_interval, "checkpoint_interval")
        
        # Validate paths
        validate_path_string(args.checkpoint_dir, "checkpoint_dir")
        validate_path_string(args.output_dir, "output_dir")
        
        # Validate max_runtime if provided
        if args.max_runtime is not None:
            if args.max_runtime <= 0:
                raise ValueError("max_runtime must be positive")
        
        logger.info(EmojiFormatter.format("success", "All arguments validated"))


def main() -> int:
    """
    Main entry point for the fetch script.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    try:
        # Display startup banner
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("rocket", "Freesound Graph Fetch Script"))
        logger.info("=" * 70)
        logger.info(f"Query: {args.query}")
        logger.info(f"Recursive depth: {args.depth}")
        logger.info(f"Max samples: {args.max_samples}")
        logger.info(f"Checkpoint directory: {args.checkpoint_dir}")
        logger.info(f"Output directory: {args.output_dir}")
        logger.info("=" * 70)
        
        # Validate arguments
        validate_arguments(args, logger)
        
        # Load API key
        logger.info(EmojiFormatter.format("search", "Loading API key..."))
        api_key = load_api_key(args.api_key)
        logger.info(EmojiFormatter.format("success", "API key loaded"))
        
        # Ensure output directory exists
        logger.info(EmojiFormatter.format("progress", "Ensuring output directory exists..."))
        output_dir = ensure_output_directory(args.output_dir, create_if_missing=True)
        logger.info(EmojiFormatter.format("success", f"Output directory ready: {output_dir}"))
        
        # Initialize IncrementalFreesoundLoader
        logger.info(EmojiFormatter.format("progress", "Initializing Freesound loader..."))
        config = {
            'api_key': api_key,
            'checkpoint_dir': args.checkpoint_dir,
            'checkpoint_interval': args.checkpoint_interval,
            'max_runtime_hours': args.max_runtime,
        }
        loader = IncrementalFreesoundLoader(config)
        logger.info(EmojiFormatter.format("success", "Loader initialized"))
        
        # Execute fetch with recursive parameters
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("rocket", "Starting recursive fetch..."))
        logger.info("=" * 70)
        
        start_time = time.time()
        
        data = loader.fetch_data(
            query=args.query,
            max_samples=args.max_samples,
            include_similar=True,
            recursive_depth=args.depth,
            max_total_samples=args.max_samples
        )
        
        # Build final graph
        logger.info(EmojiFormatter.format("progress", "Building final graph..."))
        graph = loader.build_graph(data)
        
        elapsed_seconds = time.time() - start_time
        
        # Generate output filename
        logger.info(EmojiFormatter.format("progress", "Generating output filename..."))
        
        # Create a sanitized query for filename (replace spaces with underscores)
        sanitized_query = args.query.replace(' ', '_').replace('/', '_')
        
        # Use generate_output_filename for consistent naming
        output_filename = generate_output_filename(
            prefix=f"{output_dir}/freesound_{sanitized_query}",
            strategy=f"depth{args.depth}",
            k_value=args.max_samples,
            extension="pkl"
        )
        
        # Save graph to Output directory
        logger.info(EmojiFormatter.format("progress", f"Saving graph to {output_filename}..."))
        
        with error_context("graph save", logger):
            joblib.dump(graph, output_filename)
        
        # Log statistics and output file path
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("completion", "Fetch Complete!"))
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("chart", f"Total nodes: {graph.number_of_nodes():,}"))
        logger.info(EmojiFormatter.format("chart", f"Total edges: {graph.number_of_edges():,}"))
        logger.info(EmojiFormatter.format("timer", f"Elapsed time: {format_time_duration(elapsed_seconds)}"))
        logger.info(EmojiFormatter.format("success", f"Graph saved to: {output_filename}"))
        logger.info("=" * 70)
        
        return 0
    
    except ValueError as e:
        logger.error(EmojiFormatter.format("error", f"Validation error: {e}"))
        return 1
    
    except Exception as e:
        logger.error(EmojiFormatter.format("error", f"Unexpected error: {e}"))
        logger.exception("Full traceback:")
        return 2


if __name__ == '__main__':
    sys.exit(main())
