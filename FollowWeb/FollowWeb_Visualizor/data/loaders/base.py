"""
Abstract base class for data loaders in FollowWeb.

This module defines the DataLoader interface that all data source implementations
must follow. It provides a template method pattern for loading data and building
graphs, with built-in validation and caching support.

Classes:
    DataLoader: Abstract base class defining the standard interface for data loaders

Example:
    Creating a custom data loader::

        from FollowWeb_Visualizor.data.loaders.base import DataLoader
        import networkx as nx

        class MyCustomLoader(DataLoader):
            def fetch_data(self, **params):
                # Fetch data from your source
                return {'nodes': [...], 'edges': [...]}

            def build_graph(self, data):
                # Convert data to NetworkX graph
                graph = nx.DiGraph()
                for node in data['nodes']:
                    graph.add_node(node['id'], **node['attrs'])
                for edge in data['edges']:
                    graph.add_edge(edge['source'], edge['target'])
                return graph

        # Use the loader
        loader = MyCustomLoader(config={'api_key': 'xxx'})
        graph = loader.load(query='example')

See Also:
    :class:`~FollowWeb_Visualizor.data.loaders.instagram.InstagramLoader`: Instagram data loader
    :class:`~FollowWeb_Visualizor.data.loaders.freesound.FreesoundLoader`: Freesound API loader
"""

# Standard library imports
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

# Third-party imports
import networkx as nx

# Local imports
from ...core.exceptions import DataProcessingError
from ..cache import get_cache_manager


class DataLoader(ABC):
    """
    Abstract base class for data loaders.

    This class defines the standard interface for loading data from various sources
    and converting it to NetworkX graphs. Subclasses must implement fetch_data()
    and build_graph() methods to handle source-specific logic.

    The load() method provides a template method pattern that orchestrates the
    complete workflow: fetch data, build graph, validate graph, and log statistics.

    Attributes
    ----------
    config : dict[str, Any]
        Configuration dictionary for the loader. Structure depends on subclass.
    logger : logging.Logger
        Logger instance for this loader, named after the subclass.
    cache_manager : CacheManager
        Centralized cache manager for expensive operations.

    Notes
    -----
    This class uses the Template Method design pattern. The load() method defines
    the algorithm skeleton, while subclasses implement the variable parts
    (fetch_data and build_graph).

    The validation step ensures that all loaders produce consistent output
    (NetworkX DiGraph objects) regardless of the data source.

    Examples
    --------
    Creating a simple file-based loader::

        class JSONLoader(DataLoader):
            def fetch_data(self, filepath):
                with open(filepath) as f:
                    return json.load(f)

            def build_graph(self, data):
                graph = nx.DiGraph()
                for node in data['nodes']:
                    graph.add_node(node['id'], **node['attrs'])
                for edge in data['edges']:
                    graph.add_edge(edge['source'], edge['target'])
                return graph

        loader = JSONLoader()
        graph = loader.load(filepath='data.json')

    See Also
    --------
    fetch_data : Abstract method for fetching raw data
    build_graph : Abstract method for building NetworkX graph
    load : Template method orchestrating the complete workflow
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the data loader.

        Parameters
        ----------
        config : dict[str, Any], optional
            Configuration dictionary for the loader. Subclasses can define
            their own configuration schema. Common keys include:
            
            - 'api_key': API authentication key
            - 'cache_ttl': Cache time-to-live in seconds
            - 'timeout': Request timeout in seconds
            
            Default is None, which initializes an empty config dict.

        Notes
        -----
        The constructor automatically initializes:
        
        - A logger named after the subclass
        - A centralized cache manager for expensive operations
        
        Subclasses should call super().__init__(config) before their own initialization.
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_manager = get_cache_manager()

    @abstractmethod
    def fetch_data(self, **params) -> dict[str, Any]:
        """
        Fetch raw data from the source.

        This method must be implemented by subclasses to handle source-specific
        data fetching logic (API calls, file reading, database queries, etc.).

        Parameters
        ----------
        **params : dict
            Source-specific parameters for data fetching. Common parameters include:
            
            - filepath : str - Path to data file (for file-based loaders)
            - query : str - Search query (for API-based loaders)
            - filters : dict - Filter criteria
            - max_items : int - Maximum items to fetch
            - timeout : float - Request timeout in seconds

        Returns
        -------
        dict[str, Any]
            Dictionary containing raw data in a source-specific format.
            The structure is defined by the subclass implementation.
            Typically includes keys like 'nodes', 'edges', 'metadata'.

        Raises
        ------
        DataProcessingError
            If data fetching fails due to:
            
            - Network errors or timeouts
            - Authentication failures
            - Invalid parameters
            - Missing required data
            - API rate limits exceeded

        Notes
        -----
        This method should handle all source-specific error conditions and
        convert them to DataProcessingError for consistent error handling.

        Implementations should use the cache_manager for expensive operations
        and the logger for progress reporting.

        Examples
        --------
        File-based implementation::

            def fetch_data(self, filepath: str) -> dict[str, Any]:
                try:
                    with open(filepath) as f:
                        return json.load(f)
                except FileNotFoundError as e:
                    raise DataProcessingError(f"File not found: {filepath}") from e

        API-based implementation::

            def fetch_data(self, query: str, max_items: int = 100) -> dict[str, Any]:
                response = requests.get(
                    self.api_url,
                    params={'q': query, 'limit': max_items},
                    headers={'Authorization': f'Bearer {self.api_key}'}
                )
                if response.status_code != 200:
                    raise DataProcessingError(f"API error: {response.status_code}")
                return response.json()
        """
        pass

    @abstractmethod
    def build_graph(self, data: dict[str, Any]) -> nx.DiGraph:
        """
        Convert raw data to a NetworkX directed graph.

        This method must be implemented by subclasses to handle source-specific
        graph construction logic. The method should create nodes with appropriate
        attributes and edges representing relationships.

        Parameters
        ----------
        data : dict[str, Any]
            Raw data dictionary returned by fetch_data().
            The structure depends on the subclass implementation.
            Typically includes keys like 'nodes', 'edges', 'relationships'.

        Returns
        -------
        nx.DiGraph
            NetworkX directed graph with nodes and edges representing the network.
            
            Nodes should have meaningful attributes such as:
            
            - 'name': Display name
            - 'type': Node type/category
            - 'metadata': Additional properties
            
            Edges should have attributes such as:
            
            - 'type': Relationship type
            - 'weight': Relationship strength
            - 'metadata': Additional properties

        Raises
        ------
        DataProcessingError
            If graph construction fails due to:
            
            - Invalid data format
            - Missing required fields
            - Duplicate node IDs
            - Invalid edge references
            - Data type mismatches

        Notes
        -----
        The returned graph must be a NetworkX DiGraph (directed graph).
        Undirected graphs or other graph types will fail validation.

        Node IDs should be strings for consistency across different data sources.
        Use str(node_id) to convert numeric IDs.

        All node and edge attributes should be JSON-serializable for
        compatibility with visualization and export functions.

        Examples
        --------
        Simple graph construction::

            def build_graph(self, data: dict[str, Any]) -> nx.DiGraph:
                graph = nx.DiGraph()
                
                # Add nodes with attributes
                for node in data['nodes']:
                    graph.add_node(
                        str(node['id']),
                        name=node['name'],
                        type=node.get('type', 'default')
                    )
                
                # Add edges with attributes
                for edge in data['edges']:
                    graph.add_edge(
                        str(edge['source']),
                        str(edge['target']),
                        type=edge.get('type', 'default'),
                        weight=edge.get('weight', 1.0)
                    )
                
                return graph

        Graph with validation::

            def build_graph(self, data: dict[str, Any]) -> nx.DiGraph:
                if 'nodes' not in data:
                    raise DataProcessingError("Missing 'nodes' in data")
                
                graph = nx.DiGraph()
                node_ids = set()
                
                # Add nodes and track IDs
                for node in data['nodes']:
                    node_id = str(node['id'])
                    if node_id in node_ids:
                        raise DataProcessingError(f"Duplicate node ID: {node_id}")
                    node_ids.add(node_id)
                    graph.add_node(node_id, **node.get('attrs', {}))
                
                # Add edges with validation
                for edge in data.get('edges', []):
                    source, target = str(edge['source']), str(edge['target'])
                    if source not in node_ids or target not in node_ids:
                        self.logger.warning(f"Skipping invalid edge: {source} -> {target}")
                        continue
                    graph.add_edge(source, target, **edge.get('attrs', {}))
                
                return graph
        """
        pass

    def load(self, **params) -> nx.DiGraph:
        """
        Complete loading workflow: fetch data, build graph, and validate.

        This is the main entry point for pipeline integration. It orchestrates
        the complete data loading process using the template method pattern:
        
        1. Fetch raw data from source (calls fetch_data)
        2. Build NetworkX graph from data (calls build_graph)
        3. Validate graph structure (calls _validate_graph)
        4. Log statistics

        Subclasses should not override this method unless they need to customize
        the workflow. Instead, implement fetch_data() and build_graph().

        Parameters
        ----------
        **params : dict
            Parameters passed to fetch_data(). The specific parameters
            depend on the subclass implementation.

        Returns
        -------
        nx.DiGraph
            Validated NetworkX directed graph ready for analysis.
            The graph is guaranteed to be a valid DiGraph with at least
            one node (unless the data source is empty).

        Raises
        ------
        DataProcessingError
            If any step in the workflow fails:
            
            - Data fetching fails (network, auth, etc.)
            - Graph construction fails (invalid data)
            - Validation fails (wrong graph type)
            - Any unexpected error occurs

        Notes
        -----
        This method implements the Template Method design pattern.
        The algorithm structure is fixed, but subclasses can customize
        the behavior by implementing fetch_data() and build_graph().

        All exceptions are caught and wrapped in DataProcessingError
        for consistent error handling across different data sources.

        The method logs progress at each step for debugging and monitoring.

        Examples
        --------
        Basic usage::

            loader = InstagramLoader()
            graph = loader.load(filepath='followers.json')
            print(f"Loaded {graph.number_of_nodes()} nodes")

        With error handling::

            try:
                loader = FreesoundLoader(config={'api_key': 'xxx'})
                graph = loader.load(query='drum', max_samples=100)
            except DataProcessingError as e:
                print(f"Failed to load data: {e}")

        Pipeline integration::

            def run_pipeline(loader, **params):
                # Load data
                graph = loader.load(**params)
                
                # Analyze
                analyzer = NetworkAnalyzer()
                metrics = analyzer.analyze(graph)
                
                # Visualize
                renderer = SigmaRenderer(config)
                renderer.generate_visualization(graph, 'output.html', metrics)

        See Also
        --------
        fetch_data : Fetches raw data from source
        build_graph : Converts data to NetworkX graph
        _validate_graph : Validates graph structure
        """
        try:
            # Step 1: Fetch raw data
            self.logger.info(f"Fetching data from {self.__class__.__name__}...")
            data = self.fetch_data(**params)

            # Step 2: Build graph from data
            self.logger.info("Building graph from fetched data...")
            graph = self.build_graph(data)

            # Step 3: Validate graph
            self._validate_graph(graph)

            return graph

        except DataProcessingError:
            # Re-raise DataProcessingError as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise DataProcessingError(
                f"Failed to load data with {self.__class__.__name__}: {e}"
            ) from e

    def _validate_graph(self, graph: nx.DiGraph) -> None:
        """
        Validate graph structure and log statistics.

        This method ensures that build_graph() returns a valid NetworkX DiGraph
        and logs useful statistics about the loaded graph.

        Parameters
        ----------
        graph : nx.DiGraph
            Graph to validate

        Raises
        ------
        DataProcessingError
            If graph is not a valid NetworkX DiGraph

        Notes
        -----
        This method performs the following checks:
        
        - Verifies graph is a NetworkX DiGraph instance
        - Logs node and edge counts
        - Warns if graph is empty (no nodes or edges)
        
        The validation ensures consistent output across all loader implementations.

        Warnings
        --------
        Empty graphs (no nodes or no edges) generate warnings but do not
        raise exceptions. This allows loaders to handle empty data sources
        gracefully.
        """
        # Validate type
        if not isinstance(graph, nx.DiGraph):
            raise DataProcessingError(
                f"build_graph() must return nx.DiGraph, got {type(graph).__name__}"
            )

        # Log statistics
        num_nodes = graph.number_of_nodes()
        num_edges = graph.number_of_edges()

        self.logger.info(
            f"✅ Graph loaded successfully: {num_nodes:,} nodes, {num_edges:,} edges"
        )

        # Log warning for empty graphs
        if num_nodes == 0:
            self.logger.warning("Loaded graph has no nodes")
        elif num_edges == 0:
            self.logger.warning("Loaded graph has no edges")
