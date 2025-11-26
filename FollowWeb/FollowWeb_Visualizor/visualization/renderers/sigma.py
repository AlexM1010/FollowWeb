"""
Sigma.js renderer for high-performance interactive HTML network visualizations.

This module provides the SigmaRenderer class that implements the Renderer interface
for generating interactive HTML visualizations using the Sigma.js library with WebGL support.

The renderer is tuned for large graphs (10,000+ nodes) and includes features like
audio playback for Freesound samples, interactive controls, and customizable styling.

Classes:
    SigmaRenderer: High-performance renderer using Sigma.js and WebGL

Example:
    Basic visualization::

        from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer
        from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader

        # Load data
        loader = FreesoundLoader(config={'api_key': 'xxx'})
        graph = loader.load(query='drum', max_samples=100)

        # Create renderer
        renderer = SigmaRenderer(vis_config={
            'show_labels': True,
            'show_tooltips': True,
            'sigma_interactive': {
                'enable_audio_player': True
            },
            'ui_background_color': '#2d333c',
            'ui_text_color': '#b6e0fe'
        })

        # Generate visualization
        success = renderer.generate_visualization(
            graph,
            'output/freesound_network.html'
        )

    Instagram social network::

        renderer = SigmaRenderer(
            vis_config=config,
            template_name='sigma_instagram.html'
        )

        instagram_graph = instagram_loader.load(filepath='data.json')
        renderer.generate_visualization(
            instagram_graph,
            'output/instagram_network.html'
        )

See Also:
    :class:`~FollowWeb_Visualizor.visualization.renderers.base.Renderer`: Base class
    :class:`~FollowWeb_Visualizor.visualization.renderers.pyvis.PyvisRenderer`: Alternative renderer
    :class:`~FollowWeb_Visualizor.visualization.metrics.MetricsCalculator`: Metrics calculation

Notes:
    Requires Sigma.js and Tone.js libraries, which are loaded from CDN in the
    generated HTML files. No Python dependencies beyond the base requirements.

    The renderer uses Jinja2 templates located in the templates/ subdirectory.
    Custom templates can be created by following the existing template structure.
"""

from pathlib import Path
from typing import Any, Optional

import networkx as nx
import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ...core.types import VisualizationMetrics
from ...output.formatters import EmojiFormatter
from ...utils import ProgressTracker
from ..legends import LegendGenerator
from ..metrics import MetricsCalculator
from .base import Renderer


class SigmaRenderer(Renderer):
    """
    Sigma.js-based renderer for high-performance interactive HTML network visualizations.

    This renderer generates standalone HTML files with embedded Sigma.js library
    for interactive graph visualization with WebGL rendering, supporting 10,000+ nodes.
    Includes multi-sample audio playback with beat synchronization using Tone.js for
    Freesound sample networks.

    The renderer uses Jinja2 templates for HTML generation and supports multiple
    template types for different data sources (Freesound audio, Instagram social).

    Features:

    - WebGL rendering for high performance (10,000+ nodes)
    - Canvas fallback for browsers without WebGL
    - Interactive controls (zoom, pan, reset, search)
    - Hover tooltips with node metadata
    - Multi-sample audio playback with beat sync (Tone.js)
    - BPM control and synchronized looping
    - Community detection visualization
    - Centrality metrics display
    - Customizable color schemes and layouts
    - Physics-based spring layout
    - Legend generation

    Attributes
    ----------
    vis_config : dict[str, Any]
        Visualization configuration dictionary
    logger : logging.Logger
        Logger instance for this renderer
    legend_generator : LegendGenerator
        Generator for creating HTML legends
    metrics_calculator : MetricsCalculator, optional
        Calculator for visualization metrics
    template_name : str
        Name of the Jinja2 template to use
    jinja_env : jinja2.Environment
        Jinja2 environment for template rendering

    Notes
    -----
    The renderer supports two template types:

    - 'sigma_samples.html': Default template for Freesound/audio data
        with audio player, sample metadata, and acoustic similarity visualization

    - 'sigma_instagram.html': Template for Instagram social network data
        with follower/following metrics and social relationship visualization

    The renderer automatically detects data type based on node attributes
    and applies appropriate styling and features.

    Examples
    --------
    Basic usage::

        renderer = SigmaRenderer(vis_config={
            'show_labels': True,
            'show_tooltips': True,
            'sigma_interactive': {
                'enable_audio_player': True
            }
        })

        success = renderer.generate_visualization(
            graph,
            'output.html',
            metrics
        )

    With custom template::

        renderer = SigmaRenderer(
            vis_config=config,
            template_name='sigma_instagram.html'
        )
        renderer.generate_visualization(graph, 'instagram.html')

    With metrics calculator::

        calculator = MetricsCalculator(vis_config, performance_config)
        renderer = SigmaRenderer(
            vis_config,
            metrics_calculator=calculator
        )
        renderer.generate_visualization(graph, 'output.html')

    See Also
    --------
    Renderer : Base class interface
    PyvisRenderer : Alternative Pyvis-based renderer
    MetricsCalculator : Visualization metrics calculation
    LegendGenerator : Legend HTML generation
    """

    def __init__(
        self,
        vis_config: dict[str, Any],
        metrics_calculator: Optional[MetricsCalculator] = None,
        template_name: Optional[str] = None,
    ) -> None:
        """
        Initialize the Sigma.js renderer with visualization configuration.

        Parameters
        ----------
        vis_config : dict[str, Any]
            Visualization configuration dictionary containing Sigma settings,
            display options, and styling preferences. Common keys include:

            - show_labels : bool
                Whether to display node labels (default: True)
            - show_tooltips : bool
                Whether to show hover tooltips (default: True)
            - sigma_interactive : dict
                Sigma-specific settings:

                - enable_audio_player : bool
                    Enable audio playback for Freesound samples
                - show_labels : bool
                    Override for label display
                - show_tooltips : bool
                    Override for tooltip display

            - ui_background_color : str
                Background color for UI panels (default: '#2d333c')
            - ui_highlight_color : str
                Highlight color for UI elements (default: '#415a76')
            - ui_text_color : str
                Text color for UI elements (default: '#b6e0fe')
            - template_name : str
                Template to use (if not provided as parameter)

        metrics_calculator : MetricsCalculator, optional
            Optional MetricsCalculator instance for consistent metrics
            calculation across multiple visualizations. If None, a new
            calculator is created when needed.

        template_name : str, optional
            Name of the Jinja2 template to use. If None, reads from
            vis_config['template_name'] or defaults to 'sigma_samples.html'.

            Available templates:

            - 'sigma_samples.html': Default for Freesound/audio data
            - 'sigma_instagram.html': For Instagram social network data

        Raises
        ------
        KeyError
            If required configuration keys are missing from vis_config.

        Notes
        -----
        The constructor initializes:

        - Jinja2 template environment with autoescape
        - Legend generator for creating HTML legends
        - Template caching disabled for development

        The template directory is located at:
        FollowWeb_Visualizor/visualization/renderers/templates/

        Examples
        --------
        Basic initialization::

            renderer = SigmaRenderer(vis_config={
                'show_labels': True,
                'show_tooltips': True
            })

        With audio player::

            renderer = SigmaRenderer(vis_config={
                'sigma_interactive': {
                    'enable_audio_player': True
                }
            })

        With custom template::

            renderer = SigmaRenderer(
                vis_config=config,
                template_name='sigma_instagram.html'
            )

        With shared metrics calculator::

            calculator = MetricsCalculator(vis_config, perf_config)
            renderer = SigmaRenderer(
                vis_config,
                metrics_calculator=calculator
            )
        """
        super().__init__(vis_config)
        self.legend_generator = LegendGenerator(vis_config)
        self.metrics_calculator = metrics_calculator
        # Read template_name from config if not provided
        if template_name is None:
            template_name = vis_config.get("template_name", "sigma_samples.html")
        self.template_name = template_name

        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            auto_reload=True,
            cache_size=0,  # Disable template caching for development
        )

    def generate_visualization(
        self,
        graph: nx.DiGraph,
        output_filename: str,
        metrics: Optional[VisualizationMetrics] = None,
    ) -> bool:
        """
        Generate interactive HTML visualization from graph using Sigma.js.

        Args:
            graph: The analyzed NetworkX directed graph
            output_filename: Path to save the HTML file
            metrics: Optional pre-calculated visualization metrics

        Returns:
            True if successful, False otherwise
        """
        # Validate graph
        if not self._validate_graph_not_empty(graph):
            return False

        # Filter out isolated nodes (nodes with no edges)
        nodes_with_edges = set()
        for u, v in graph.edges():
            nodes_with_edges.add(u)
            nodes_with_edges.add(v)

        if len(nodes_with_edges) < graph.number_of_nodes():
            isolated_count = graph.number_of_nodes() - len(nodes_with_edges)
            self.logger.info(
                f"Filtering out {isolated_count} isolated nodes (nodes with no edges)"
            )
            graph = graph.subgraph(nodes_with_edges).copy()

            if graph.number_of_nodes() == 0:
                self.logger.error("No nodes with edges to visualize")
                return False

        # Calculate metrics if not provided
        metrics = self._ensure_metrics(graph, metrics)

        # Extract metrics from VisualizationMetrics object
        node_metrics = self._extract_node_metrics_dict(metrics)
        edge_metrics = self._extract_edge_metrics_dict(metrics)

        try:
            # Convert graph to Sigma.js format with progress tracking
            with ProgressTracker(
                total=3,
                title="Converting graph to Sigma.js format",
                logger=self.logger,
            ) as tracker:
                graph_data = self._convert_to_sigma_format(
                    graph, node_metrics, edge_metrics, metrics
                )
                tracker.update(1)

                # Generate legend HTML
                legend_html = self.legend_generator.create_html_legend(
                    graph, edge_metrics, metrics
                )
                tracker.update(2)

                # Prepare configuration
                # Read from visualization config (primary) or sigma_interactive (fallback)
                vis_settings = self.vis_config
                sigma_config = self.vis_config.get("sigma_interactive", {})
                config = {
                    "show_labels": vis_settings.get(
                        "show_labels", sigma_config.get("show_labels", True)
                    ),
                    "show_tooltips": vis_settings.get(
                        "show_tooltips", sigma_config.get("show_tooltips", True)
                    ),
                    "enable_audio": sigma_config.get("enable_audio_player", False),
                    "ui_background_color": vis_settings.get(
                        "ui_background_color", "#2d333c"
                    ),
                    "ui_highlight_color": vis_settings.get(
                        "ui_highlight_color", "#415a76"
                    ),
                    "ui_text_color": vis_settings.get("ui_text_color", "#b6e0fe"),
                }
                tracker.update(3)

            # Render HTML using Jinja2 template
            with ProgressTracker(
                total=3,
                title="Generating HTML visualization",
                logger=self.logger,
            ) as tracker:
                template = self.jinja_env.get_template(self.template_name)
                self.logger.info(
                    f"Loading template: {self.template_name} from {Path(__file__).parent / 'templates'}"
                )

                # Ensure output directory exists
                self._ensure_output_directory(output_filename)

                # Write graph data to external JSON file
                output_path = Path(output_filename)
                json_filename = output_path.stem + "_data.json"
                json_filepath = output_path.parent / json_filename

                import json

                with open(json_filepath, "w", encoding="utf-8") as f:
                    json.dump(graph_data, f, separators=(",", ":"))

                self.logger.info(f"Graph data written to: {json_filepath}")
                tracker.update(1)

                # Prepare template context based on template type
                # Use data_file for external loading (more efficient)
                if self.template_name == "sigma_instagram.html":
                    # Instagram-specific template context
                    stats = self._calculate_network_stats(graph)
                    html_content = template.render(
                        title=f"Instagram Network - {graph.number_of_nodes()} users",
                        data_file=json_filename,
                        config=config,
                        node_count=stats["node_count"],
                        edge_count=stats["edge_count"],
                        avg_degree=stats["avg_degree"],
                        density=stats.get("density"),
                        show_centrality=any(
                            "betweenness" in m for m in node_metrics.values() if m
                        ),
                        show_community=any(
                            "community" in m for m in node_metrics.values() if m
                        ),
                        layout_iterations=100,
                        layout_gravity=1,
                        layout_scaling=10,
                        background_color="#0a0e27",
                        graph_background="linear-gradient(135deg, #0a0e27 0%, #1a1e3f 100%)",
                    )
                else:
                    # Default Freesound/audio template context
                    stats = self._calculate_network_stats(graph)
                    html_content = template.render(
                        title=f"Network Visualization - {graph.number_of_nodes()} nodes",
                        data_file=json_filename,
                        config=config,
                        node_count=stats["node_count"],
                        edge_count=stats["edge_count"],
                        avg_degree=stats["avg_degree"],
                        density=stats.get("density"),
                        show_centrality=any(
                            "betweenness" in m for m in node_metrics.values() if m
                        ),
                        show_community=any(
                            "community" in m for m in node_metrics.values() if m
                        ),
                        legend_html=legend_html,
                        legend_html_style="",  # Legend styles are inline in the legend HTML
                        background_color="#0a0e27",
                        graph_background="linear-gradient(135deg, #0a0e27 0%, #1a1e3f 100%)",
                    )
                tracker.update(2)

                # Write HTML file
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)

                # Copy template-specific assets to output directory
                if self.template_name == "sigma_instagram.html":
                    self._copy_forceatlas2_script(output_filename)
                # Audio panel assets are now inlined in the template

                tracker.update(3)

            success_msg = EmojiFormatter.format(
                "success", f"Sigma.js HTML saved: {output_filename}"
            )
            self.logger.info(success_msg)
            return True

        except Exception as e:
            self.logger.error(f"Could not save Sigma.js HTML: {e}", exc_info=True)
            return False

    def _get_tag_color(self, tag: str) -> str:
        """
        Generate a consistent color for a given tag using hash-based color generation.

        Args:
            tag: Tag string to generate color for

        Returns:
            Hex color string (e.g., '#ff6b9d')
        """
        # Use hash to generate consistent color for each tag
        tag_hash = hash(tag)

        # Generate HSL color with good saturation and lightness for visibility
        # Hue: 0-360 degrees
        hue = abs(tag_hash) % 360

        # Saturation: 60-80% for vibrant but not oversaturated colors
        saturation = 60 + (abs(tag_hash >> 8) % 21)

        # Lightness: 50-65% for good contrast on dark background
        lightness = 50 + (abs(tag_hash >> 16) % 16)

        # Convert HSL to RGB
        h = hue / 360.0
        s = saturation / 100.0
        lightness_val = lightness / 100.0

        def hsl_to_rgb(
            h: float, s: float, lightness_val: float
        ) -> tuple[int, int, int]:
            """Convert HSL to RGB."""
            if s == 0:
                r = g = b = lightness_val
            else:

                def hue_to_rgb(p: float, q: float, t: float) -> float:
                    if t < 0:
                        t += 1
                    if t > 1:
                        t -= 1
                    if t < 1 / 6:
                        return p + (q - p) * 6 * t
                    if t < 1 / 2:
                        return q
                    if t < 2 / 3:
                        return p + (q - p) * (2 / 3 - t) * 6
                    return p

                q = (
                    lightness_val * (1 + s)
                    if lightness_val < 0.5
                    else lightness_val + s - lightness_val * s
                )
                p = 2 * lightness_val - q
                r = hue_to_rgb(p, q, h + 1 / 3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1 / 3)

            return (int(r * 255), int(g * 255), int(b * 255))

        r, g, b = hsl_to_rgb(h, s, lightness_val)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _convert_to_sigma_format(
        self,
        graph: nx.DiGraph,
        node_metrics: dict[str, dict[str, Any]],
        edge_metrics: dict[tuple[str, str], dict[str, Any]],
        metrics: VisualizationMetrics,
    ) -> dict[str, Any]:
        """
        Convert NetworkX graph to Sigma.js data format.

        Args:
            graph: NetworkX directed graph
            node_metrics: Pre-calculated node metrics
            edge_metrics: Pre-calculated edge metrics
            metrics: Full visualization metrics including layout

        Returns:
            Dictionary with 'nodes' and 'edges' arrays in Sigma.js format
        """
        nodes = []
        edges = []

        # Get layout positions from metrics, or calculate physics-based layout
        layout = metrics.layout_positions

        # If layout is empty, calculate a physics-based spring layout
        if not layout:
            self.logger.info("Calculating physics-based layout for visualization...")
            # Use spring_layout with more iterations for better physics simulation
            # k controls the optimal distance between nodes (spring length)
            # iterations controls convergence quality
            layout = nx.spring_layout(
                graph,
                k=1 / np.sqrt(graph.number_of_nodes())
                if graph.number_of_nodes() > 0
                else 1,
                iterations=50,
                seed=42,
                scale=100,  # Scale up for better spread
            )
            self.logger.info(f"Layout calculated for {len(layout)} nodes")

        # Convert nodes
        for node_id in graph.nodes():
            node_attrs = graph.nodes[node_id]
            node_metric = node_metrics.get(node_id, {})

            # Get position from layout
            pos = layout.get(node_id, (0, 0))

            # Handle numpy arrays from spring_layout
            if hasattr(pos, "__iter__") and len(pos) >= 2:
                x, y = float(pos[0]), float(pos[1])
            else:
                x, y = 0.0, 0.0

            # Check if this is Instagram data (has followers/following counts)
            is_instagram = (
                "followers_count" in node_attrs or "following_count" in node_attrs
            )

            if is_instagram and self.template_name == "sigma_instagram.html":
                # Instagram-specific node attributes
                degree = graph.degree(node_id)  # type: ignore[operator]
                max_degree = (
                    max(dict(graph.degree()).values())  # type: ignore[operator]
                    if graph.number_of_nodes() > 0
                    else 1
                )
                size = 3 + (degree / max_degree) * 15

                followers = node_attrs.get("followers_count", 0)
                following = node_attrs.get("following_count", 0)

                # Calculate color based on follower/following ratio
                ratio = followers / (following + 1)
                if ratio > 1.5:
                    color = "#ff6b9d"  # Popular
                elif ratio < 0.7:
                    color = "#4ecdc4"  # Active follower
                else:
                    color = "#6c8eff"  # Balanced

                sigma_node = {
                    "key": str(node_id),
                    "attributes": {
                        "label": str(node_id),
                        "x": x,
                        "y": y,
                        "size": float(size),
                        "color": color,
                        "followers": followers,
                        "following": following,
                        "degree": degree,
                    },
                }

                # Add centrality if available
                if node_id in node_metrics and "betweenness" in node_metrics[node_id]:
                    sigma_node["attributes"]["centrality"] = float(
                        node_metrics[node_id]["betweenness"]
                    )

                # Add community if available
                if node_id in node_metrics and "community" in node_metrics[node_id]:
                    sigma_node["attributes"]["community"] = int(
                        node_metrics[node_id]["community"]
                    )
            else:
                # Default Freesound/audio node attributes
                # Determine color based on first tag if available
                node_color = node_metric.get("color_hex", "#999999")
                tags = node_attrs.get("tags", [])

                # Ensure tags is a list
                if isinstance(tags, str):
                    tags = [tags]
                elif not isinstance(tags, list):
                    tags = []

                # Color by first tag if available
                if tags and len(tags) > 0:
                    first_tag = str(tags[0]).lower().strip()
                    node_color = self._get_tag_color(first_tag)

                sigma_node = {
                    "key": str(node_id),
                    "attributes": {
                        "label": str(node_id),
                        "x": x,
                        "y": y,
                        "size": float(node_metric.get("size", 10)),
                        "color": node_color,
                        "community": node_metric.get("community", 0),
                        "degree": node_metric.get("degree", 0),
                        "betweenness": node_metric.get("betweenness", 0.0),
                        "eigenvector": node_metric.get("eigenvector", 0.0),
                    },
                }

                # Add node-specific attributes from graph
                if "name" in node_attrs:
                    sigma_node["attributes"]["name"] = str(node_attrs["name"])

                if tags:
                    sigma_node["attributes"]["tags"] = tags

                if "duration" in node_attrs:
                    sigma_node["attributes"]["duration"] = float(node_attrs["duration"])

                if "user" in node_attrs:
                    sigma_node["attributes"]["user"] = str(node_attrs["user"])

                # Store uploader_id for space-efficient audio URL reconstruction in frontend
                # Frontend reconstructs: https://freesound.org/data/previews/{folder}/{id}_{uploader_id}-{quality}.mp3
                # This saves ~70 bytes per node vs storing full URLs
                if "uploader_id" in node_attrs and node_attrs["uploader_id"] is not None:
                    sigma_node["attributes"]["uploader_id"] = int(node_attrs["uploader_id"])
                else:
                    # Debug: log first few nodes missing uploader_id
                    if len(nodes) < 3:
                        self.logger.warning(f"Node {node_id} missing uploader_id. Available keys: {list(node_attrs.keys())}")

                if "license" in node_attrs:
                    sigma_node["attributes"]["license"] = str(node_attrs["license"])

            nodes.append(sigma_node)

        # Convert edges
        for source, target in graph.edges():
            edge_metric = edge_metrics.get((source, target), {})
            edge_attrs = graph.edges[source, target]

            # Build edge attributes for Sigma.js
            sigma_edge = {
                "source": str(source),
                "target": str(target),
                "attributes": {
                    "size": float(edge_metric.get("width", 1)),
                    "color": edge_metric.get("color", "#cccccc"),
                    "type": "arrow"
                    if not edge_metric.get("is_mutual", False)
                    else "line",
                },
            }

            # Add edge-specific attributes
            if "type" in edge_attrs:
                sigma_edge["attributes"]["edge_type"] = str(edge_attrs["type"])

            if "weight" in edge_attrs:
                sigma_edge["attributes"]["weight"] = float(edge_attrs["weight"])

            edges.append(sigma_edge)

        return {"nodes": nodes, "edges": edges}

    def _copy_forceatlas2_script(self, output_filename: str) -> None:
        """
        Copy the forceatlas2.js script to the same directory as the output HTML file.

        Args:
            output_filename: Path to the output HTML file
        """
        import shutil

        try:
            # Get the template directory where forceatlas2.js is located
            template_dir = Path(__file__).parent / "templates"
            source_script = template_dir / "forceatlas2.js"

            # Get the output directory
            output_dir = Path(output_filename).parent
            dest_script = output_dir / "forceatlas2.js"

            # Copy the script file
            if source_script.exists():
                shutil.copy2(source_script, dest_script)
                self.logger.debug(f"Copied forceatlas2.js to {dest_script}")
            else:
                self.logger.warning(f"forceatlas2.js not found at {source_script}")
        except Exception as e:
            self.logger.warning(f"Could not copy forceatlas2.js: {e}")

    def _calculate_network_stats(self, graph: nx.DiGraph) -> dict[str, Any]:
        """
        Calculate basic network statistics for Instagram template.

        Args:
            graph: NetworkX directed graph

        Returns:
            Dictionary with network statistics
        """
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()

        stats = {
            "node_count": node_count,
            "edge_count": edge_count,
            "avg_degree": f"{(edge_count * 2 / node_count):.2f}"
            if node_count > 0
            else "0.00",
        }

        # Calculate density for smaller graphs
        if node_count > 0 and node_count < 10000:
            try:
                density = nx.density(graph)
                stats["density"] = density
            except Exception:
                pass

        return stats

    def get_file_extension(self) -> str:
        """Return file extension for Sigma.js HTML output."""
        return ".html"

    def supports_large_graphs(self) -> bool:
        """
        Sigma.js with WebGL can efficiently handle 10,000+ nodes.

        Returns:
            True - Sigma.js is tuned for large graphs with WebGL rendering
        """
        return True
