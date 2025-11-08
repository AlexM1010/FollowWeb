"""
Freesound data loader for FollowWeb audio sample network analysis.

This module provides the FreesoundLoader class for loading and parsing audio sample
data from the Freesound API with rate limiting, caching, and error handling.
"""

# Standard library imports
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports
import freesound
import networkx as nx

# Local imports
from ...core.exceptions import DataProcessingError
from ...output.formatters import EmojiFormatter
from ...utils import ProgressTracker
from ...utils.rate_limiter import RateLimiter
from .base import DataLoader


class FreesoundLoader(DataLoader):
    """
    Loader for Freesound API audio sample data.
    
    This loader handles audio sample data from the Freesound API, creating networks
    where nodes represent audio samples and edges represent similarity relationships.
    It uses the official freesound-python library for API access with additional
    rate limiting and caching.
    
    The loader supports:
    - Text search queries
    - Tag-based filtering
    - Similar sounds relationships (MVP: only edge type)
    - Rate limiting (60 requests/minute)
    - Response caching
    - Batch processing with progress tracking
    
    Attributes:
        config: Configuration dictionary
        logger: Logger instance for this loader
        cache_manager: Centralized cache manager
        client: Freesound API client
        rate_limiter: Rate limiter for API requests
    
    Example:
        loader = FreesoundLoader(config={'api_key': 'your_api_key'})
        graph = loader.load(query='drum', max_samples=100)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Freesound loader.
        
        Args:
            config: Configuration dictionary with optional keys:
                   - api_key: Freesound API key (or use FREESOUND_API_KEY env var)
                   - requests_per_minute: Rate limit (default: 60)
        
        Raises:
            DataProcessingError: If API key is not provided
        """
        super().__init__(config)
        
        # Get API key from config or environment
        api_key = self.config.get('api_key') or os.getenv('FREESOUND_API_KEY')
        if not api_key:
            raise DataProcessingError(
                "Freesound API key required. Provide via config['api_key'] "
                "or FREESOUND_API_KEY environment variable"
            )
        
        # Initialize Freesound client
        self.client = freesound.FreesoundClient()
        self.client.set_token(api_key)
        
        # Initialize rate limiter
        requests_per_minute = self.config.get('requests_per_minute', 60)
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
        
        self.logger.info(
            f"FreesoundLoader initialized with rate limit: "
            f"{requests_per_minute} requests/minute"
        )
    
    def fetch_data(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_samples: int = 1000,
        include_similar: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch sample data from Freesound API.
        
        Searches for audio samples based on query and/or tags, then optionally
        fetches similar sounds relationships for each sample.
        
        Args:
            query: Text search query (e.g., "drum", "synth")
            tags: List of tags to filter by (e.g., ["percussion", "loop"])
            max_samples: Maximum number of samples to fetch (default: 1000)
            include_similar: Fetch similar sounds relationships (default: True)
        
        Returns:
            Dictionary with keys:
            - 'samples': List of sample dictionaries with metadata
            - 'relationships': Dict with 'similar' key containing similarity data
        
        Raises:
            DataProcessingError: If API request fails or returns invalid data
        """
        if not query and not tags:
            raise DataProcessingError(
                "Must provide either query or tags for Freesound search"
            )
        
        # Search for samples
        self.logger.info(
            f"Searching Freesound: query='{query}', tags={tags}, "
            f"max_samples={max_samples}"
        )
        samples = self._search_samples(query, tags, max_samples)
        
        if not samples:
            self.logger.warning("No samples found matching search criteria")
            return {'samples': [], 'relationships': {'similar': {}}}
        
        progress_msg = EmojiFormatter.format(
            "progress", f"Found {len(samples)} samples"
        )
        self.logger.info(progress_msg)
        
        # Fetch similar sounds relationships (MVP: only edge type)
        relationships = {}
        if include_similar:
            relationships['similar'] = self._fetch_similar_sounds(samples)
        else:
            relationships['similar'] = {}
        
        return {
            'samples': samples,
            'relationships': relationships
        }
    
    def _search_samples(
        self,
        query: Optional[str],
        tags: Optional[List[str]],
        max_samples: int
    ) -> List[Dict[str, Any]]:
        """
        Search for audio samples using Freesound API.
        
        Args:
            query: Text search query
            tags: List of tags to filter by
            max_samples: Maximum number of samples to fetch
        
        Returns:
            List of sample dictionaries with metadata
        
        Raises:
            DataProcessingError: If API request fails
        """
        samples = []
        
        try:
            # Build search filter
            search_filter = ""
            if tags:
                tag_filter = " ".join(f"tag:{tag}" for tag in tags)
                search_filter = tag_filter
            
            # Perform search with rate limiting
            self.rate_limiter.acquire()
            
            # Use text_search with pagination
            page_size = min(150, max_samples)  # Freesound max page size is 150
            
            results = self.client.text_search(
                query=query or "",
                filter=search_filter if search_filter else None,
                page_size=page_size,
                fields="id,name,tags,duration,username,previews"
            )
            
            # Collect samples from first page
            for sound in results:
                if len(samples) >= max_samples:
                    break
                
                sample_data = self._extract_sample_metadata(sound)
                samples.append(sample_data)
            
            # Fetch additional pages if needed
            while len(samples) < max_samples and results.more:
                self.rate_limiter.acquire()
                results = results.next_page()
                
                for sound in results:
                    if len(samples) >= max_samples:
                        break
                    
                    sample_data = self._extract_sample_metadata(sound)
                    samples.append(sample_data)
        
        except Exception as e:
            raise DataProcessingError(
                f"Failed to search Freesound API: {e}"
            ) from e
        
        return samples
    
    def _extract_sample_metadata(self, sound) -> Dict[str, Any]:
        """
        Extract metadata from Freesound sound object.
        
        Args:
            sound: Freesound sound object from API
        
        Returns:
            Dictionary with sample metadata
        """
        # Extract preview URLs safely
        previews = {}
        if hasattr(sound, 'previews'):
            previews = sound.previews
        
        # Get high-quality MP3 preview URL for audio playback
        audio_url = ""
        if isinstance(previews, dict):
            audio_url = previews.get('preview-hq-mp3', '')
        
        return {
            'id': sound.id,
            'name': sound.name,
            'tags': sound.tags if hasattr(sound, 'tags') else [],
            'duration': sound.duration if hasattr(sound, 'duration') else 0,
            'username': sound.username if hasattr(sound, 'username') else '',
            'audio_url': audio_url
        }
    
    def _fetch_similar_sounds(
        self,
        samples: List[Dict[str, Any]]
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Fetch similar sounds relationships for all samples.
        
        Args:
            samples: List of sample dictionaries
        
        Returns:
            Dictionary mapping sample_id to list of (similar_id, score) tuples
        """
        relationships = {}
        
        self.logger.info(
            f"Fetching similar sounds for {len(samples)} samples..."
        )
        
        # Use progress tracking for fetching similar sounds
        with ProgressTracker(
            total=len(samples),
            title="Fetching similar sounds relationships",
            logger=self.logger
        ) as tracker:
            for i, sample in enumerate(samples):
                sample_id = sample['id']
                
                try:
                    # Fetch similar sounds with rate limiting
                    similar_list = self._fetch_similar_sounds_for_sample(sample_id)
                    
                    if similar_list:
                        relationships[sample_id] = similar_list
                
                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch similar sounds for sample {sample_id}: {e}"
                    )
                    # Continue processing other samples
                
                tracker.update(i + 1)
        
        success_msg = EmojiFormatter.format(
            "success",
            f"Fetched similar sounds for {len(relationships)} samples"
        )
        self.logger.info(success_msg)
        
        return relationships
    
    def _fetch_similar_sounds_for_sample(
        self,
        sample_id: int
    ) -> List[Tuple[int, float]]:
        """
        Fetch similar sounds for a single sample.
        
        Args:
            sample_id: Freesound sample ID
        
        Returns:
            List of (similar_id, score) tuples
        """
        similar_list = []
        
        try:
            # Rate limit the request
            self.rate_limiter.acquire()
            
            # Get sound object
            sound = self.client.get_sound(sample_id)
            
            # Fetch similar sounds
            similar_sounds = sound.get_similar()
            
            # Extract IDs and scores
            for similar in similar_sounds:
                similar_id = similar.id
                # Freesound doesn't provide explicit similarity scores in the API
                # Use a default weight of 1.0 for MVP
                score = 1.0
                similar_list.append((similar_id, score))
        
        except Exception as e:
            # Log but don't raise - allow processing to continue
            self.logger.debug(
                f"Could not fetch similar sounds for {sample_id}: {e}"
            )
        
        return similar_list
    
    def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
        """
        Build a directed graph from Freesound sample data.
        
        Creates nodes for audio samples and directed edges representing similarity
        relationships. Node attributes include sample metadata (name, tags, duration,
        user, audio_url). Edge attributes include relationship type and weight.
        
        Args:
            data: Dictionary with 'samples' and 'relationships' keys from fetch_data()
        
        Returns:
            NetworkX DiGraph with nodes representing audio samples and edges
            representing similarity relationships. Returns empty graph if no data.
        
        Raises:
            DataProcessingError: If graph construction fails
        """
        samples = data.get('samples', [])
        relationships = data.get('relationships', {})
        similar_sounds = relationships.get('similar', {})
        
        # Initialize graph
        graph = nx.DiGraph()
        
        # Handle empty data
        if not samples:
            self.logger.info("No samples to process, returning empty graph")
            return graph
        
        # Add sample nodes
        self.logger.info(f"Adding {len(samples)} sample nodes to graph...")
        
        for sample in samples:
            graph.add_node(
                str(sample['id']),  # Use string ID for consistency
                name=sample['name'],
                tags=sample.get('tags', []),
                duration=sample.get('duration', 0),
                user=sample.get('username', ''),
                audio_url=sample.get('audio_url', ''),
                type='sample'
            )
        
        # Add similarity edges
        edge_count = 0
        self.logger.info("Adding similarity edges to graph...")
        
        for source_id, similar_list in similar_sounds.items():
            source_node = str(source_id)
            
            # Only add edges if source node exists in graph
            if source_node not in graph:
                continue
            
            for target_id, similarity_score in similar_list:
                target_node = str(target_id)
                
                # Only add edge if target node exists in graph
                if target_node in graph:
                    graph.add_edge(
                        source_node,
                        target_node,
                        type='similar',
                        weight=similarity_score
                    )
                    edge_count += 1
        
        success_msg = EmojiFormatter.format(
            "success",
            f"Graph built: {graph.number_of_nodes():,} nodes, "
            f"{graph.number_of_edges():,} edges"
        )
        self.logger.info(success_msg)
        
        return graph
