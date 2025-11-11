"""
Abstract base class for data loaders in FollowWeb.

This module defines the DataLoader interface that all data source implementations
must follow. It provides a template method pattern for loading data and building
graphs, with built-in validation and caching support.
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

    Attributes:
        config: Configuration dictionary for the loader
        logger: Logger instance for this loader
        cache_manager: Centralized cache manager for expensive operations

    Example:
        class MyLoader(DataLoader):
            def fetch_data(self, **params):
                # Fetch data from source
                return {'nodes': [...], 'edges': [...]}

            def build_graph(self, data):
                # Convert data to NetworkX graph
                graph = nx.DiGraph()
                # ... add nodes and edges
                return graph

        loader = MyLoader(config={'api_key': 'xxx'})
        graph = loader.load(query='example')
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the data loader.

        Args:
            config: Optional configuration dictionary for the loader.
                   Subclasses can define their own configuration schema.
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

        Args:
            **params: Source-specific parameters for data fetching.
                     Examples: filepath, query, filters, max_items, etc.

        Returns:
            Dictionary containing raw data in a source-specific format.
            The structure is defined by the subclass implementation.

        Raises:
            DataProcessingError: If data fetching fails due to network errors,
                               authentication issues, invalid parameters, etc.

        Example:
            def fetch_data(self, filepath: str) -> Dict[str, Any]:
                with open(filepath) as f:
                    return json.load(f)
        """
        pass

    @abstractmethod
    def build_graph(self, data: dict[str, Any]) -> nx.DiGraph:
        """
        Convert raw data to a NetworkX directed graph.

        This method must be implemented by subclasses to handle source-specific
        graph construction logic. The method should create nodes with appropriate
        attributes and edges representing relationships.

        Args:
            data: Raw data dictionary returned by fetch_data().
                 The structure depends on the subclass implementation.

        Returns:
            NetworkX DiGraph with nodes and edges representing the network.
            Nodes and edges should have meaningful attributes for analysis.

        Raises:
            DataProcessingError: If graph construction fails due to invalid data,
                               missing required fields, or other processing errors.

        Example:
            def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
                graph = nx.DiGraph()
                for node in data['nodes']:
                    graph.add_node(node['id'], **node['attributes'])
                for edge in data['edges']:
                    graph.add_edge(edge['source'], edge['target'])
                return graph
        """
        pass

    def load(self, **params) -> nx.DiGraph:
        """
        Complete loading workflow: fetch data, build graph, and validate.

        This is the main entry point for pipeline integration. It orchestrates
        the complete data loading process using the template method pattern:
        1. Fetch raw data from source
        2. Build NetworkX graph from data
        3. Validate graph structure
        4. Log statistics

        Subclasses should not override this method unless they need to customize
        the workflow. Instead, implement fetch_data() and build_graph().

        Args:
            **params: Parameters passed to fetch_data().

        Returns:
            Validated NetworkX DiGraph ready for analysis.

        Raises:
            DataProcessingError: If any step in the workflow fails.

        Example:
            loader = InstagramLoader()
            graph = loader.load(filepath='data.json')
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

        Args:
            graph: Graph to validate

        Raises:
            DataProcessingError: If graph is not a valid NetworkX DiGraph
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
