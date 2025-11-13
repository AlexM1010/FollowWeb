"""
Freesound data loader for FollowWeb audio sample network analysis.

This module provides the FreesoundLoader class for loading and parsing audio sample
data from the Freesound API with rate limiting, caching, and error handling.

The loader creates networks where nodes represent audio samples and edges represent
similarity relationships based on acoustic analysis. It supports recursive fetching
(snowball sampling) to discover related samples beyond the initial search results.

Classes:
    FreesoundLoader: Loader for Freesound API audio sample data

Example:
    Basic usage::

        from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader

        # Initialize with API key
        loader = FreesoundLoader(config={
            'api_key': 'your_freesound_api_key',
            'requests_per_minute': 60
        })

        # Load samples and build graph
        graph = loader.load(
            query='drum',
            max_samples=100,
            recursive_depth=1,
            max_total_samples=500
        )

        print(f"Loaded {graph.number_of_nodes()} samples")
        print(f"Found {graph.number_of_edges()} similarity relationships")

    With environment variable::

        import os
        os.environ['FREESOUND_API_KEY'] = 'your_api_key'

        loader = FreesoundLoader()
        graph = loader.load(query='synth', tags=['loop'], max_samples=50)

See Also:
    :class:`~FollowWeb_Visualizor.data.loaders.base.DataLoader`: Base class interface
    :class:`~FollowWeb_Visualizor.utils.rate_limiter.RateLimiter`: Rate limiting utility
    :mod:`freesound`: Official Freesound Python client library

Notes:
    Requires a Freesound API key. Get one at https://freesound.org/apiv2/apply/
    
    The loader respects Freesound's rate limits (60 requests/minute by default)
    and implements exponential backoff for 429 (rate limit) errors.
"""

# Standard library imports
import os
import time
from typing import Any, Callable, Optional, Union

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
    - Rate limiting (60 requests/minute default)
    - Response caching with hit/miss tracking
    - Batch processing with progress tracking
    - Recursive fetching (snowball sampling)
    - Exponential backoff for rate limit errors

    Attributes
    ----------
    config : dict[str, Any]
        Configuration dictionary
    logger : logging.Logger
        Logger instance for this loader
    cache_manager : CacheManager
        Centralized cache manager
    client : freesound.FreesoundClient
        Official Freesound API client
    rate_limiter : RateLimiter
        Rate limiter for API requests

    Notes
    -----
    The loader creates directed graphs where:
    
    - Nodes represent audio samples with attributes:
        - id: Freesound sample ID
        - name: Sample name
        - tags: List of tags
        - duration: Duration in seconds
        - user: Username of uploader
        - audio_url: High-quality MP3 preview URL
        - num_downloads: Download count (popularity metric)
        - avg_rating: Average rating (quality metric)
    
    - Edges represent similarity relationships:
        - type: 'similar' (based on acoustic analysis)
        - weight: Similarity score (1.0 default)
    
    The loader uses the Freesound API's similarity endpoint which is based
    on acoustic analysis (timbre, rhythm, pitch) rather than metadata.

    Examples
    --------
    Basic search::

        loader = FreesoundLoader(config={'api_key': 'xxx'})
        graph = loader.load(query='drum', max_samples=100)

    Tag-based search::

        graph = loader.load(
            tags=['percussion', 'loop'],
            max_samples=50
        )

    Recursive fetching (snowball sampling)::

        graph = loader.load(
            query='ambient',
            max_samples=50,           # Initial seed samples
            recursive_depth=2,        # Fetch similar sounds 2 levels deep
            max_total_samples=500     # Total limit including recursive
        )

    With custom rate limit::

        loader = FreesoundLoader(config={
            'api_key': 'xxx',
            'requests_per_minute': 30  # More conservative rate
        })
        graph = loader.load(query='synth')

    See Also
    --------
    DataLoader : Base class interface
    RateLimiter : Rate limiting implementation
    IncrementalFreesoundLoader : Loader with checkpoint support
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the Freesound loader.

        Parameters
        ----------
        config : dict[str, Any], optional
            Configuration dictionary with optional keys:
            
            - api_key : str
                Freesound API key. If not provided, reads from
                FREESOUND_API_KEY environment variable.
            - requests_per_minute : int
                Rate limit for API requests (default: 60).
                Freesound's limit is 60 requests/minute for standard accounts.

        Raises
        ------
        DataProcessingError
            If API key is not provided via config or environment variable.

        Notes
        -----
        The loader initializes:
        
        - Official freesound-python client for API access
        - Custom rate limiter for request throttling
        - Internal sound cache for reducing API calls
        - Cache hit/miss counters for monitoring

        Get a Freesound API key at: https://freesound.org/apiv2/apply/

        Examples
        --------
        With config::

            loader = FreesoundLoader(config={
                'api_key': 'your_api_key_here',
                'requests_per_minute': 60
            })

        With environment variable::

            import os
            os.environ['FREESOUND_API_KEY'] = 'your_api_key_here'
            loader = FreesoundLoader()

        Conservative rate limit::

            loader = FreesoundLoader(config={
                'api_key': 'xxx',
                'requests_per_minute': 30  # Half the default rate
            })
        """
        super().__init__(config)

        # Get API key from config or environment
        api_key = self.config.get("api_key") or os.getenv("FREESOUND_API_KEY")
        if not api_key:
            raise DataProcessingError(
                "Freesound API key required. Provide via config['api_key'] "
                "or FREESOUND_API_KEY environment variable"
            )

        # Initialize Freesound client
        self.client = freesound.FreesoundClient()
        self.client.set_token(api_key)

        # Initialize rate limiter
        requests_per_minute = self.config.get("requests_per_minute", 60)
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)

        # Persistent cache to avoid re-fetching same samples across runs
        # This will be loaded from checkpoint in IncrementalFreesoundLoader
        self._sound_cache: dict[int, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0

        self.logger.info(
            f"FreesoundLoader initialized with rate limit: "
            f"{requests_per_minute} requests/minute"
        )

    def _retry_with_backoff(
        self,
        func: Callable,
        *args,
        max_retries: int = 3,
        initial_wait: float = 0.0,
        **kwargs,
    ) -> Any:
        """
        Retry a function on rate limit errors.

        Since we already have a rate limiter preventing us from exceeding limits,
        429 errors are rare and usually transient. Just retry immediately - the
        rate limiter will handle proper spacing.

        Args:
            func: Function to call
            *args: Positional arguments for func
            max_retries: Maximum number of retry attempts (default: 3)
            initial_wait: Initial wait time in seconds (default: 0 - no wait)
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            Exception: If all retries are exhausted
        """
        wait_time = initial_wait

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except freesound.FreesoundException as e:
                # Check if it's a rate limit error (429)
                if hasattr(e, "code") and e.code == 429:
                    if attempt < max_retries - 1:
                        # Calculate wait time in minutes for better readability
                        wait_time / 60

                        self.logger.warning(
                            f"⏳ Rate limit (429) - attempt {attempt + 1}/{max_retries}. "
                            f"Waiting {wait_time:.0f}s..."
                        )

                        # Simple wait without countdown for shorter times
                        time.sleep(wait_time)

                        # Exponential backoff: double the wait time (max 5 minutes)
                        wait_time = min(wait_time * 2, 300)
                        continue
                    else:
                        self.logger.error(
                            f"❌ Rate limit hit after {max_retries} retries. "
                            f"You may have hit the daily limit (2000 requests/day). "
                            f"Try again tomorrow or contact Freesound for higher limits."
                        )
                        raise
                else:
                    # Not a rate limit error, re-raise immediately
                    raise
            except Exception:
                # Other exceptions, re-raise immediately
                raise

        # Should never reach here, but just in case
        raise DataProcessingError(f"Failed after {max_retries} retries")

    def fetch_data(  # type: ignore[override]
        self,
        query: Optional[str] = None,
        tags: Optional[list[str]] = None,
        max_samples: int = 1000,
        include_similar: bool = True,
        recursive_depth: int = 0,
        max_total_samples: int = 100,
    ) -> dict[str, Any]:
        """
        Fetch sample data from Freesound API with optional recursive similar sounds.

        Searches for audio samples based on query and/or tags, then optionally
        fetches similar sounds relationships. If recursive_depth > 0, will also
        fetch metadata for similar sounds and their relationships (snowball sampling).

        Args:
            query: Text search query (e.g., "drum", "synth")
            tags: List of tags to filter by (e.g., ["percussion", "loop"])
            max_samples: Maximum number of seed samples to fetch (default: 1000)
            include_similar: Fetch similar sounds relationships (default: True)
            recursive_depth: How many levels deep to fetch similar sounds (0=no recursion)
            max_total_samples: Maximum total samples including recursive fetches

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

        # Search for seed samples
        self.logger.info(
            f"Searching Freesound: query='{query}', tags={tags}, "
            f"max_samples={max_samples}, recursive_depth={recursive_depth}"
        )
        samples = self._search_samples(query, tags, max_samples)

        if not samples:
            self.logger.warning("No samples found matching search criteria")
            return {"samples": [], "relationships": {"similar": {}}}

        progress_msg = EmojiFormatter.format(
            "progress", f"Found {len(samples)} seed samples"
        )
        self.logger.info(progress_msg)

        # Fetch similar sounds relationships (MVP: only edge type)
        relationships = {}
        if include_similar:
            relationships["similar"] = self._fetch_similar_sounds_recursive(
                samples, recursive_depth, max_total_samples
            )
        else:
            relationships["similar"] = {}

        return {"samples": samples, "relationships": relationships}

    def _search_samples(
        self, query: Optional[str], tags: Optional[list[str]], max_samples: int
    ) -> list[dict[str, Any]]:
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

            # Perform search with rate limiting and retry on 429
            self.rate_limiter.acquire()

            # Use text_search with pagination
            # Sort by popularity (downloads, ratings) to get most useful samples first
            page_size = min(150, max_samples)  # Freesound max page size is 150

            # Wrap API call with retry logic
            def _do_search():
                return self.client.text_search(
                    query=query or "",
                    filter=search_filter if search_filter else None,
                    page_size=page_size,
                    sort="downloads_desc",  # Sort by most downloaded (most popular)
                    fields="id,name,tags,duration,username,previews,num_downloads,avg_rating",
                )

            results = self._retry_with_backoff(_do_search)

            # Collect sample IDs from first page
            sample_ids: list[int] = []
            for sound in results:
                if len(sample_ids) >= max_samples:
                    break
                sample_ids.append(sound.id)

            # Fetch additional pages if needed
            while len(sample_ids) < max_samples and results.next:
                self.rate_limiter.acquire()
                results = self._retry_with_backoff(results.next_page)

                for sound in results:
                    if len(sample_ids) >= max_samples:
                        break
                    sample_ids.append(sound.id)

            # Now fetch full metadata for each sample (including preview URLs)
            for sample_id in sample_ids:
                try:
                    self.rate_limiter.acquire()
                    full_sound = self._retry_with_backoff(
                        self.client.get_sound, sample_id
                    )
                    sample_data = self._extract_sample_metadata(full_sound)
                    samples.append(sample_data)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch full metadata for sample {sample_id}: {e}"
                    )
                    # Continue with other samples

        except Exception as e:
            raise DataProcessingError(f"Failed to search Freesound API: {e}") from e

        return samples

    def _extract_sample_metadata(self, sound) -> dict[str, Any]:
        """
        Extract metadata from Freesound sound object.

        Args:
            sound: Freesound sound object from API (must be full object from get_sound())

        Returns:
            Dictionary with sample metadata including audio preview URL
        """
        # Extract preview URLs from full sound object
        # Note: sound.previews is a FreesoundObject, need to convert to dict
        audio_url = ""
        if hasattr(sound, "previews"):
            # Get the dict representation of previews
            sound_dict = sound.as_dict()
            previews = sound_dict.get("previews", {})

            if isinstance(previews, dict):
                # Try high-quality MP3 first, then fallback to other formats
                # Note: Keys use underscores, not hyphens!
                audio_url = (
                    previews.get("preview_hq_mp3", "")
                    or previews.get("preview_lq_mp3", "")
                    or previews.get("preview_hq_ogg", "")
                )

        # Get full metadata dict - this contains EVERYTHING from the API
        sound_dict = sound.as_dict()

        # Start with the complete API response (saves everything!)
        metadata = sound_dict.copy()

        # Add our processed audio_url for convenience
        metadata["audio_url"] = audio_url

        # Ensure critical fields are present (for backward compatibility)
        metadata.setdefault("id", sound.id)
        metadata.setdefault("name", sound.name)
        metadata.setdefault("tags", sound.tags if hasattr(sound, "tags") else [])
        metadata.setdefault(
            "duration", sound.duration if hasattr(sound, "duration") else 0
        )
        metadata.setdefault(
            "username", sound.username if hasattr(sound, "username") else ""
        )

        return metadata

    def _fetch_similar_sounds_recursive(
        self,
        seed_samples: list[dict[str, Any]],
        depth: int = 0,
        max_total_samples: int = 100,
    ) -> dict[int, list[tuple[int, float]]]:
        """
        Fetch similar sounds with optional recursive expansion (snowball sampling).

        If depth=0: Only fetches similar sounds for seed samples (no recursion)
        If depth>0: Recursively fetches metadata for similar sounds and their relationships

        Args:
            seed_samples: Initial list of sample dictionaries
            depth: How many levels deep to recurse (0=no recursion, just seed samples)
            max_total_samples: Maximum total samples to fetch (only used if depth>0)

        Returns:
            Dictionary mapping sample_id to list of (similar_id, score) tuples
        """
        relationships = {}
        all_samples = {s["id"]: s for s in seed_samples}  # Track all samples by ID
        samples_to_process = list(seed_samples)
        processed_ids = set()
        current_depth = 0

        if depth == 0:
            self.logger.info(
                f"Fetching similar sounds for {len(seed_samples)} samples (no recursion)..."
            )
        else:
            self.logger.info(
                f"Starting recursive similar sounds fetch: "
                f"depth={depth}, max_total={max_total_samples}"
            )

        while samples_to_process and current_depth <= depth:
            batch_size = len(samples_to_process)
            self.logger.info(f"Processing depth {current_depth}: {batch_size} samples")

            next_batch = []

            with ProgressTracker(
                total=batch_size,
                title=f"Depth {current_depth}: Fetching similar sounds",
                logger=self.logger,
            ) as tracker:
                for i, sample in enumerate(samples_to_process):
                    sample_id = sample["id"]

                    # Skip if already processed
                    if sample_id in processed_ids:
                        tracker.update(i + 1)
                        continue

                    # Check if we've hit the max total samples limit
                    if len(all_samples) >= max_total_samples:
                        self.logger.info(
                            f"Reached max_total_samples limit ({max_total_samples})"
                        )
                        break

                    try:
                        # Fetch similar sounds with rate limiting
                        similar_list = self._fetch_similar_sounds_for_sample(sample_id)

                        if similar_list:
                            relationships[sample_id] = similar_list

                            # If we're not at max depth, fetch metadata for similar sounds
                            if current_depth < depth:
                                for similar_id, _score in similar_list:
                                    # Only fetch if we haven't seen this sample yet
                                    if (
                                        similar_id not in all_samples
                                        and len(all_samples) < max_total_samples
                                    ):
                                        try:
                                            # Fetch metadata for similar sound
                                            similar_sample = (
                                                self._fetch_sample_metadata(similar_id)
                                            )
                                            all_samples[similar_id] = similar_sample
                                            next_batch.append(similar_sample)
                                        except Exception as e:
                                            self.logger.debug(
                                                f"Could not fetch metadata for similar sound {similar_id}: {e}"
                                            )

                        processed_ids.add(sample_id)

                    except Exception as e:
                        self.logger.warning(
                            f"Failed to fetch similar sounds for sample {sample_id}: {e}"
                        )
                        processed_ids.add(sample_id)

                    tracker.update(i + 1)

            # Move to next depth level
            samples_to_process = next_batch
            current_depth += 1

        # Update the samples list in the parent scope (stored in self for access in build_graph)
        self._all_discovered_samples = list(all_samples.values())

        success_msg = EmojiFormatter.format(
            "success",
            f"Recursive fetch complete: {len(all_samples)} total samples, "
            f"{len(relationships)} with relationships",
        )
        self.logger.info(success_msg)

        return relationships

    def _fetch_sample_metadata(
        self, sample_id: int, return_sound: bool = False
    ) -> Union[dict[str, Any], tuple[dict[str, Any], Any]]:
        """
        Fetch metadata for a single sample by ID with caching.

        Args:
            sample_id: Freesound sample ID
            return_sound: If True, returns (metadata, sound_object) tuple

        Returns:
            Dictionary with sample metadata, or tuple if return_sound=True

        Raises:
            Exception: If API request fails
        """
        # Check cache first (saves API call!)
        if sample_id in self._sound_cache:
            self._cache_hits += 1
            self.logger.debug(
                f"Cache hit for sample {sample_id} (hits: {self._cache_hits})"
            )
            sound = self._sound_cache[sample_id]
            metadata = self._extract_sample_metadata(sound)
            if return_sound:
                return metadata, sound
            return metadata

        # Cache miss - need to fetch from API
        self._cache_misses += 1

        # Rate limit the request
        self.rate_limiter.acquire()

        # Get sound object with retry on rate limit
        sound = self._retry_with_backoff(self.client.get_sound, sample_id)

        # Cache the sound object for future use
        self._sound_cache[sample_id] = sound
        self.logger.debug(
            f"Cached sample {sample_id} (cache size: {len(self._sound_cache)})"
        )

        # Extract metadata
        metadata = self._extract_sample_metadata(sound)

        if return_sound:
            return metadata, sound
        return metadata

    def _fetch_sample_with_similar(
        self, sample_id: int
    ) -> tuple[dict[str, Any], list[tuple[int, float]]]:
        """
        Efficiently fetch both metadata and similar sounds in one API call sequence.

        This is more efficient than calling _fetch_sample_metadata and
        _fetch_similar_sounds_for_sample separately, as it reuses the sound object.

        Args:
            sample_id: Freesound sample ID

        Returns:
            Tuple of (metadata_dict, similar_sounds_list)
        """
        # Rate limit the request
        self.rate_limiter.acquire()

        # Get sound object with retry (1 API call)
        sound = self._retry_with_backoff(self.client.get_sound, sample_id)

        # Extract metadata from the sound object
        metadata = self._extract_sample_metadata(sound)

        # Fetch similar sounds using the same sound object (1 API call)
        similar_list = []
        try:
            similar_sounds = self._retry_with_backoff(sound.get_similar)

            # Extract IDs and scores, excluding self-loops
            for similar in similar_sounds:
                similar_id = similar.id

                # Skip self-loops
                if similar_id == sample_id:
                    continue

                score = 1.0
                similar_list.append((similar_id, score))

            if similar_list:
                self.logger.debug(
                    f"Sample {sample_id}: found {len(similar_list)} similar sounds"
                )

        except Exception as e:
            self.logger.debug(f"Could not fetch similar sounds for {sample_id}: {e}")

        return metadata, similar_list

    def _fetch_similar_sounds_for_sample(
        self, sample_id: int
    ) -> list[tuple[int, float]]:
        """
        Fetch similar sounds for a single sample.

        Note: If you need both metadata and similar sounds, use
        _fetch_sample_with_similar() instead to save an API call.

        Args:
            sample_id: Freesound sample ID

        Returns:
            List of (similar_id, score) tuples (excluding self-loops)
        """
        _, similar_list = self._fetch_sample_with_similar(sample_id)
        return similar_list

    def build_graph(self, data: dict[str, Any]) -> nx.DiGraph:
        """
        Build a directed graph from Freesound sample data.

        Creates nodes for audio samples and directed edges representing similarity
        relationships. Node attributes include sample metadata (name, tags, duration,
        user, audio_url). Edge attributes include relationship type and weight.

        If recursive fetching was used, includes all discovered samples as nodes.

        Args:
            data: Dictionary with 'samples' and 'relationships' keys from fetch_data()

        Returns:
            NetworkX DiGraph with nodes representing audio samples and edges
            representing similarity relationships. Returns empty graph if no data.

        Raises:
            DataProcessingError: If graph construction fails
        """
        samples = data.get("samples", [])
        relationships = data.get("relationships", {})
        similar_sounds = relationships.get("similar", {})

        # Use all discovered samples if recursive fetching was used
        if hasattr(self, "_all_discovered_samples"):
            samples = self._all_discovered_samples
            self.logger.info(f"Using {len(samples)} recursively discovered samples")

        # Initialize graph
        graph: nx.DiGraph = nx.DiGraph()

        # Handle empty data
        if not samples:
            self.logger.info("No samples to process, returning empty graph")
            return graph

        # Add sample nodes
        self.logger.info(f"Adding {len(samples)} sample nodes to graph...")

        for sample in samples:
            graph.add_node(
                str(sample["id"]),  # Use string ID for consistency
                name=sample["name"],
                tags=sample.get("tags", []),
                duration=sample.get("duration", 0),
                user=sample.get("username", ""),
                audio_url=sample.get("audio_url", ""),
                # Popularity metrics for node sizing/coloring
                num_downloads=sample.get("num_downloads", 0),
                num_comments=sample.get("num_comments", 0),
                num_ratings=sample.get("num_ratings", 0),
                avg_rating=sample.get("avg_rating", 0.0),
                num_bookmarks=sample.get("num_bookmarks", 0),
                type="sample",
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
                        type="similar",
                        weight=similarity_score,
                    )
                    edge_count += 1

        success_msg = EmojiFormatter.format(
            "success",
            f"Graph built: {graph.number_of_nodes():,} nodes, "
            f"{graph.number_of_edges():,} edges",
        )
        self.logger.info(success_msg)

        return graph
