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

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.loaders.incremental_freesound import IncrementalFreesoundLoader  # noqa: E402
from FollowWeb_Visualizor.output.formatters import EmojiFormatter  # noqa: E402
from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer  # noqa: E402


def setup_logging():
    """Configure logging with emoji support."""
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
        description='Generate Freesound network visualization with recursive similar sounds discovery',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Get defaults from environment variables or use hardcoded defaults
    default_seed_sample_id = os.environ.get('FREESOUND_SEED_SAMPLE_ID', None)
    default_max_requests = int(os.environ.get('FREESOUND_MAX_REQUESTS', '1950'))
    default_depth = int(os.environ.get('FREESOUND_DEPTH', '3'))
    
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
        '--depth',
        type=int,
        default=default_depth,
        help='Recursive depth for similar sounds discovery'
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
            # Get node data from graph
            node_data = loader.graph.nodes[best_seed]
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
    depth = args.depth
    max_requests = args.max_requests
    page_size = 150  # Maximum allowed by API
    
    # Track seed sample info for logging
    seed_name = None
    seed_downloads = None
    
    # Log collection strategy
    logger.info(f"Recursive depth: {depth}")
    logger.info(f"Max requests: {max_requests} (circuit breaker)")
    logger.info(f"Page size: {page_size} (API maximum)")
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
        }
        loader = IncrementalFreesoundLoader(loader_config)
        logger.info("✅ Checkpoint interval: 1 (saving after every sample)")
        logger.info("✅ Persistent storage: data/freesound_library/ (committed to Git)")
        logger.info("✅ Automatic backups every 100 nodes")
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
        # handle checkpoint-aware processing. The seed sample is used for
        # priority scoring, not as a direct fetch parameter.
        logger.info(f"Fetching Freesound data with recursive discovery (depth={depth})...")
        
        # Use an empty query to match all samples (per Freesound API docs)
        # Loader will skip already-processed ones from checkpoint
        data = loader.fetch_data(
            query="",  # Empty query matches all samples
            max_samples=max_requests,  # Circuit breaker
            include_similar=True,
            recursive_depth=depth,
            max_total_samples=max_requests
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
        
        # Create output directory
        output_dir = Path("Output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate visualization
        logger.info(EmojiFormatter.format("progress", "Generating visualization..."))
        
        # Create minimal config for visualization
        
        # Create renderer
        renderer = SigmaRenderer({
            'renderer_type': 'sigma',
            'template_name': 'sigma_samples.html'
        })
        
        # Generate output filename with seed sample ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        seed_id_str = seed_sample_id if seed_sample_id else "unknown"
        output_prefix = f"freesound_seed{seed_id_str}_depth{depth}_n{final_nodes}_{timestamp}"
        output_path = output_dir / f"{output_prefix}.html"
        
        # Render visualization
        success = renderer.generate_visualization(
            graph=graph,
            output_filename=str(output_path),
            metrics=None  # Let renderer calculate metrics
        )
        
        if success:
            # Get API request count from loader
            api_requests_used = getattr(loader, 'session_request_count', 0)
            
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
