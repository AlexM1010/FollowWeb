#!/usr/bin/env python3
"""
Generate Freesound network visualization using the incremental loader.

This script fetches Freesound data with recursive similar sounds discovery
and generates an interactive Sigma.js visualization.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file (optional, for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available (e.g., in CI/CD), skip loading .env file
    pass

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.loaders.incremental_freesound import IncrementalFreesoundLoader  # noqa: E402
from FollowWeb_Visualizor.output.formatters import EmojiFormatter  # noqa: E402
from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer  # noqa: E402


def setup_logging():
    """Configure logging with emoji support and Windows console compatibility."""
    # Configure UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f'freesound_viz_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
                encoding='utf-8'
            )
        ]
    )
    return logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments with environment variable fallbacks."""
    parser = argparse.ArgumentParser(
        description='Generate Freesound network visualization with edge-based relationships',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Get defaults from environment variables or use hardcoded defaults
    default_seed_sample_id = os.environ.get('FREESOUND_SEED_SAMPLE_ID', None)
    default_max_requests = int(os.environ.get('FREESOUND_MAX_REQUESTS', '1950'))
    default_discovery_mode = os.environ.get('FREESOUND_DISCOVERY_MODE', 'search')
    
    parser.add_argument(
        '--seed-sample-id',
        type=int,
        default=int(default_seed_sample_id) if default_seed_sample_id else None,
        help='Seed sample ID (default: None = use checkpoint-aware selection or most downloaded sample)'
    )
    
    parser.add_argument(
        '--max-requests',
        type=int,
        default=default_max_requests,
        help='Maximum API requests (circuit breaker, default: 1950 before 2000 limit)'
    )
    
    parser.add_argument(
        '--discovery-mode',
        type=str,
        default=default_discovery_mode,
        choices=['search', 'relationships', 'mixed'],
        help='Sample discovery strategy: search (API search), relationships (pending nodes), or mixed'
    )
    
    parser.add_argument(
        '--include-user-edges',
        action='store_true',
        default=True,
        help='Create edges between samples by the same user'
    )
    
    parser.add_argument(
        '--include-pack-edges',
        action='store_true',
        default=True,
        help='Create edges between samples in the same pack'
    )
    
    parser.add_argument(
        '--include-tag-edges',
        action='store_true',
        default=True,
        help='Create edges between samples with similar tags'
    )
    
    parser.add_argument(
        '--tag-similarity-threshold',
        type=float,
        default=0.3,
        help='Minimum Jaccard similarity for tag edges (0.0-1.0, default: 0.3)'
    )
    
    parser.add_argument(
        '--use-pagination',
        action='store_true',
        default=False,
        help='Use pagination-based collection (continues from last page in checkpoint)'
    )
    
    parser.add_argument(
        '--sort-order',
        type=str,
        default='downloads_desc',
        choices=['downloads_desc', 'created_desc', 'rating_desc', 'duration_desc'],
        help='Sort order for pagination search (default: downloads_desc)'
    )
    
    parser.add_argument(
        '--skip-visualization',
        action='store_true',
        default=False,
        help='Skip visualization generation (useful for CI/CD data collection only)'
    )
    
    return parser.parse_args()


def get_most_downloaded_sample(api_key: str, logger: logging.Logger) -> tuple[int, str, int]:
    """
    Fetch the most downloaded sample from Freesound with multi-level fallback.
    
    Args:
        api_key: Freesound API key
        logger: Logger instance
    
    Returns:
        Tuple of (sample_id, sample_name, num_downloads)
    """
    import requests
    
    # Level 1: Try most downloaded sample
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        'query': '*',  # Match all samples
        'sort': 'downloads_desc',  # Sort by downloads descending
        'page_size': 1,  # Only need the top result
        'fields': 'id,name,num_downloads',
        'token': api_key
    }
    
    try:
        logger.info("Level 1: Fetching most downloaded sample from Freesound...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['results']:
            sample = data['results'][0]
            logger.info(
                f"✅ Most downloaded sample: {sample['name']} "
                f"(ID: {sample['id']}, Downloads: {sample['num_downloads']})"
            )
            return sample['id'], sample['name'], sample['num_downloads']
        else:
            raise RuntimeError("No samples found in search results")
    
    except Exception as e:
        logger.warning(f"Level 1 failed: {e}")
        
        # Level 2: Try search for "piano" (common, high-quality results)
        try:
            logger.info("Level 2: Trying search for 'piano'...")
            params['query'] = 'piano'
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['results']:
                sample = data['results'][0]
                logger.info(
                    f"✅ Found piano sample: {sample['name']} "
                    f"(ID: {sample['id']}, Downloads: {sample['num_downloads']})"
                )
                return sample['id'], sample['name'], sample['num_downloads']
        except Exception as e2:
            logger.warning(f"Level 2 failed: {e2}")
        
        # Level 3: Try hardcoded ID 2523 (known popular sample)
        logger.info("Level 3: Using hardcoded sample ID 2523...")
        fallback_id = 2523
        fallback_name = "Unknown (fallback ID 2523)"
        logger.warning(f"Using fallback sample ID: {fallback_id}")
        return fallback_id, fallback_name, 0


def get_checkpoint_aware_seed(loader, api_key: str, logger: logging.Logger) -> tuple[int, str, int]:
    """
    Select seed sample with checkpoint awareness using SQL-based priority scoring.
    
    If checkpoint is empty (first run), fetch most downloaded sample from API.
    If checkpoint exists, use SQL query to get best seed (O(1) instant retrieval).
    
    Args:
        loader: IncrementalFreesoundLoader instance
        api_key: Freesound API key
        logger: Logger instance
    
    Returns:
        Tuple of (sample_id, sample_name, num_downloads)
    """
    if loader.graph.number_of_nodes() == 0:
        # Empty checkpoint - fetch from API
        logger.info("Empty checkpoint detected, fetching seed from API...")
        return get_most_downloaded_sample(api_key, logger)
    else:
        # Checkpoint exists - use SQL-based seed selection (O(1) instant retrieval)
        logger.info("Checkpoint exists, selecting seed from SQL query (O(1) instant retrieval)...")
        
        # Get best seed from metadata cache using priority score
        best_seed = loader.metadata_cache.get_best_seed_sample()
        
        if best_seed:
            # Get node data from graph (convert to string key)
            node_id = str(best_seed)
            node_data = loader.graph.nodes[node_id]
            seed_name = node_data.get('name', 'Unknown')
            seed_downloads = node_data.get('num_downloads', 0)
            logger.info(
                f"✅ Selected seed from SQL query: {seed_name} "
                f"(ID: {best_seed}, Downloads: {seed_downloads})"
            )
            return best_seed, seed_name, seed_downloads
        else:
            # Fallback to API if no suitable seed found
            logger.warning("No non-dormant samples found in SQL cache, fetching from API...")
            return get_most_downloaded_sample(api_key, logger)


def main():
    """Main execution function."""
    logger = setup_logging()
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Load API key from environment
    api_key = os.environ.get('FREESOUND_API_KEY')
    if not api_key:
        logger.error(EmojiFormatter.format("error", "FREESOUND_API_KEY not found in environment"))
        logger.info("Please set your API key in .env file or export FREESOUND_API_KEY=your_key")
        return 1
    
    logger.info("=" * 70)
    logger.info(EmojiFormatter.format("rocket", "Freesound Network Visualization"))
    logger.info("=" * 70)
    
    # Configuration from CLI arguments
    seed_sample_id = args.seed_sample_id
    discovery_mode = args.discovery_mode
    max_requests = args.max_requests
    page_size = 150  # Maximum allowed by API
    include_user_edges = args.include_user_edges
    include_pack_edges = args.include_pack_edges
    include_tag_edges = args.include_tag_edges
    tag_similarity_threshold = args.tag_similarity_threshold
    use_pagination = args.use_pagination
    sort_order = args.sort_order
    skip_visualization = args.skip_visualization
    
    # Track seed sample info for logging
    seed_name = None
    seed_downloads = None
    
    # Log collection strategy
    logger.info(f"Discovery mode: {discovery_mode}")
    logger.info(f"Max requests: {max_requests} (circuit breaker)")
    logger.info(f"Page size: {page_size} (API maximum)")
    logger.info(f"Pagination mode: {use_pagination}")
    if use_pagination:
        logger.info(f"Sort order: {sort_order}")
    logger.info(f"Edge generation: user={include_user_edges}, pack={include_pack_edges}, tag={include_tag_edges}")
    if include_tag_edges:
        logger.info(f"Tag similarity threshold: {tag_similarity_threshold}")
    logger.info("=" * 70)
    
    try:
        # Initialize loader with persistent library storage
        logger.info(EmojiFormatter.format("progress", "Initializing Freesound loader..."))
        loader_config = {
            'api_key': api_key,
            'checkpoint_dir': 'data/freesound_library',  # Persistent, Git-committed directory
            'checkpoint_interval': 1,  # Save after EVERY sample for maximum safety
            'max_runtime_hours': None,  # No time limit - let it run as long as needed
            'max_requests': max_requests,  # Circuit breaker
            'page_size': page_size,  # Results per API request
            # Backup configuration (Phase 1 & 2 implementation)
            'backup_interval_nodes': 25,  # Backup every 25 nodes (~1/4 of previous 100)
            'backup_retention_count': 10,  # Keep last 10 backups per tier
            'backup_compression': True,  # Compress backups older than 7 days
            'tiered_backups': True,  # Enable multi-tier backup strategy
            'compression_age_days': 7,  # Compress backups after 7 days
        }
        loader = IncrementalFreesoundLoader(loader_config)
        logger.info("✅ Checkpoint interval: 1 (saving after every sample)")
        logger.info("✅ Persistent storage: data/freesound_library/ (committed to Git)")
        logger.info("✅ Tiered backups: every 25 (frequent), 100 (moderate), 500 (milestone) nodes")
        logger.info("✅ Backup retention: 5 frequent, 10 moderate, unlimited milestone")
        logger.info("✅ Automatic compression: backups older than 7 days")
        logger.info("✅ Circuit breaker: stops at max_requests to prevent API limit")
        logger.info("✅ No time limit - will handle rate limits with exponential backoff")
        
        # Track initial state for statistics
        initial_nodes = loader.graph.number_of_nodes()
        initial_edges = loader.graph.number_of_edges()
        
        # Fetch data with recursive discovery
        logger.info(EmojiFormatter.format("rocket", "Fetching Freesound data..."))
        
        # Determine seed sample with checkpoint awareness
        if seed_sample_id is None:
            # Use checkpoint-aware seed selection (saves 1 API request/day)
            seed_sample_id, seed_name, seed_downloads = get_checkpoint_aware_seed(loader, api_key, logger)
        else:
            logger.info(f"Using provided seed sample ID: {seed_sample_id}")
        
        # For incremental loading, we use a broad query and let the loader
        # handle checkpoint-aware processing with pagination resumption.
        logger.info(f"Fetching Freesound data with discovery mode: {discovery_mode}...")
        
        # The loader will:
        # 1. Resume from the last pagination checkpoint
        # 2. Skip already-processed samples
        # 3. Stop when circuit breaker (max_requests) is hit
        # 4. Save pagination state for next run
        
        # Use a broad query to find samples, loader will skip already-processed ones
        # Note: Freesound API doesn't support wildcard queries, use empty string for all samples
        data = loader.fetch_data(
            query="",  # Empty query matches all samples (per Freesound API docs)
            max_samples=999999,  # Large number - circuit breaker will stop us
            discovery_mode=discovery_mode,
            include_user_edges=include_user_edges,
            include_pack_edges=include_pack_edges,
            include_tag_edges=include_tag_edges,
            tag_similarity_threshold=tag_similarity_threshold,
            use_pagination=use_pagination,
            sort_order=sort_order
        )
        
        # Build graph
        logger.info(EmojiFormatter.format("progress", "Building graph..."))
        graph = loader.build_graph(data)
        
        # Calculate statistics
        final_nodes = graph.number_of_nodes()
        final_edges = graph.number_of_edges()
        nodes_added = final_nodes - initial_nodes
        edges_added = final_edges - initial_edges
        
        logger.info(EmojiFormatter.format("success", f"Graph built: {final_nodes} nodes, {final_edges} edges"))
        
        # Get API request count from loader
        api_requests_used = getattr(loader, 'session_request_count', 0)
        
        # Skip visualization if requested (useful for CI/CD data collection only)
        if skip_visualization:
            logger.info("=" * 70)
            logger.info(EmojiFormatter.format("completion", "Data Collection Complete!"))
            logger.info("=" * 70)
            logger.info(EmojiFormatter.format("chart", f"Seed sample ID: {seed_sample_id}"))
            if seed_name:
                logger.info(EmojiFormatter.format("chart", f"Seed sample name: {seed_name}"))
            logger.info(EmojiFormatter.format("chart", f"Nodes added: {nodes_added}"))
            logger.info(EmojiFormatter.format("chart", f"Edges added: {edges_added}"))
            logger.info(EmojiFormatter.format("chart", f"Total nodes: {final_nodes}"))
            logger.info(EmojiFormatter.format("chart", f"Total edges: {final_edges}"))
            logger.info(EmojiFormatter.format("chart", f"API requests used: {api_requests_used} / {max_requests} limit"))
            logger.info(EmojiFormatter.format("info", "Visualization generation skipped (--skip-visualization)"))
            logger.info("=" * 70)
            return 0
        
        # Create output directory
        output_dir = Path("Output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate visualization
        logger.info(EmojiFormatter.format("progress", "Generating visualization..."))
        
        # Create minimal config for visualization
        
        # Create renderer with required metrics config
        renderer = SigmaRenderer({
            'renderer_type': 'sigma',
            'template_name': 'sigma_samples.html',
            'node_size_metric': 'degree',
            'node_color_metric': 'degree',
            'edge_width_metric': 'weight',
            'node_size_range': [5, 30],
            'edge_width_range': [0.5, 3.0]
        })
        
        # Generate output filename with seed sample ID and discovery mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        seed_id_str = seed_sample_id if seed_sample_id else "unknown"
        output_prefix = f"freesound_seed{seed_id_str}_{discovery_mode}_n{final_nodes}_{timestamp}"
        output_path = output_dir / f"{output_prefix}.html"
        
        # Render visualization
        success = renderer.generate_visualization(
            graph=graph,
            output_filename=str(output_path),
            metrics=None  # Let renderer calculate metrics
        )
        
        if success:
            logger.info("=" * 70)
            logger.info(EmojiFormatter.format("completion", "Visualization Complete!"))
            logger.info("=" * 70)
            logger.info(EmojiFormatter.format("chart", f"Seed sample ID: {seed_sample_id}"))
            if seed_name:
                logger.info(EmojiFormatter.format("chart", f"Seed sample name: {seed_name}"))
            logger.info(EmojiFormatter.format("chart", f"Nodes added: {nodes_added}"))
            logger.info(EmojiFormatter.format("chart", f"Edges added: {edges_added}"))
            logger.info(EmojiFormatter.format("chart", f"Total nodes: {final_nodes}"))
            logger.info(EmojiFormatter.format("chart", f"Total edges: {final_edges}"))
            logger.info(EmojiFormatter.format("chart", f"API requests used: {api_requests_used} / {max_requests} limit"))
            logger.info(EmojiFormatter.format("success", f"Output: {output_path}"))
            logger.info("=" * 70)
            logger.info(f"\nOpen the file in your browser: {output_path.absolute()}")
            return 0
        else:
            logger.error(EmojiFormatter.format("error", "Visualization generation failed"))
            return 1
        
    except Exception as e:
        logger.error(EmojiFormatter.format("error", f"Error: {e}"))
        logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())
