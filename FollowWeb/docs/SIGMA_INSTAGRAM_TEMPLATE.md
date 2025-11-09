# Sigma.js Instagram Template

The unified `SigmaRenderer` now supports multiple templates, including a specialized template for Instagram follower/following network visualizations.

## Features

The Instagram template (`sigma_instagram.html`) provides:

- **Color-coded nodes** based on follower/following ratio:
  - 🌸 **Pink (#ff6b9d)**: Popular users (more followers than following)
  - 🌊 **Teal (#4ecdc4)**: Active followers (following more than followers)
  - 💙 **Blue (#6c8eff)**: Balanced users

- **Node sizes** scaled by degree centrality (total connections)
- **Interactive search** to find and highlight specific users
- **Click nodes** to see detailed statistics
- **Hover tooltips** with user information
- **Dynamic layout** with ForceAtlas2 algorithm
- **Network statistics** panel
- **Modern dark theme** with smooth animations

## Usage

### Basic Example

```python
from FollowWeb_Visualizor.visualization.renderers import SigmaRenderer
import networkx as nx

# Create graph with Instagram data
graph = nx.DiGraph()

# Add nodes with follower/following counts
graph.add_node("user1", followers_count=100, following_count=50)
graph.add_node("user2", followers_count=200, following_count=150)

# Add edges (following relationships)
graph.add_edge("user1", "user2")

# Configure visualization
vis_config = {
    "sigma_interactive": {
        "show_labels": True,
        "show_tooltips": True,
    }
}

# Create renderer with Instagram template
renderer = SigmaRenderer(
    vis_config=vis_config,
    template_name="sigma_instagram.html"  # Use Instagram template
)

# Generate visualization
renderer.generate_visualization(
    graph=graph,
    output_filename="instagram_network.html"
)
```

### Loading from JSON

```python
import json
import networkx as nx
from FollowWeb_Visualizor.visualization.renderers import SigmaRenderer

# Load Instagram data
with open("followers_following.json", 'r') as f:
    data = json.load(f)

# Create graph
graph = nx.DiGraph()

for user_data in data:
    user = user_data['user']
    followers_count = len(user_data.get('followers', []))
    following_count = len(user_data.get('following', []))
    
    graph.add_node(
        user,
        followers_count=followers_count,
        following_count=following_count
    )
    
    for followed_user in user_data.get('following', []):
        if graph.has_node(followed_user):
            graph.add_edge(user, followed_user)

# Generate visualization
renderer = SigmaRenderer(
    vis_config={},
    template_name="sigma_instagram.html"
)

renderer.generate_visualization(graph, "output.html")
```

## Template Selection

The `SigmaRenderer` supports multiple templates:

- **`sigma_visualization.html`** (default): Freesound audio network template with Howler.js integration
- **`sigma_instagram.html`**: Instagram social network template with follower/following visualization

Select the template by passing the `template_name` parameter:

```python
# Instagram template
renderer = SigmaRenderer(vis_config, template_name="sigma_instagram.html")

# Freesound template (default)
renderer = SigmaRenderer(vis_config, template_name="sigma_visualization.html")
# or simply
renderer = SigmaRenderer(vis_config)
```

## Node Attributes

The Instagram template expects nodes to have these attributes:

- **`followers_count`** (int): Number of followers
- **`following_count`** (int): Number of users being followed

Optional attributes:
- **`centrality`** (float): Betweenness centrality (if calculated)
- **`community`** (int): Community assignment (if calculated)

## Interactive Features

### Search
- Type a username in the search box
- Press Enter or click "Highlight User"
- The camera will center on the user and highlight them in yellow

### Node Information
- Click any node to see detailed statistics:
  - Followers count
  - Following count
  - Total connections (degree)
  - Centrality (if available)
  - Community (if available)

### Layout
- Click "Apply Layout" to run the ForceAtlas2 physics simulation
- This reorganizes nodes based on their connections
- Takes ~100 iterations to complete

### Reset View
- Click "Reset View" to:
  - Clear all highlights
  - Reset camera position
  - Restore original node colors and sizes

## Configuration Options

Template-specific configuration in `vis_config`:

```python
vis_config = {
    "sigma_interactive": {
        "show_labels": True,        # Show node labels
        "show_tooltips": True,      # Enable hover tooltips
    }
}
```

Template rendering options (passed to Jinja2):

```python
# These are set automatically but can be customized
template_vars = {
    "layout_iterations": 100,       # ForceAtlas2 iterations
    "layout_gravity": 1,            # Gravity strength
    "layout_scaling": 10,           # Scaling ratio
    "background_color": "#0a0e27",  # Page background
    "graph_background": "linear-gradient(...)",  # Canvas background
}
```

## Example Script

A complete example script is available at:
```
FollowWeb/examples/generate_instagram_sigma.py
```

Run it with:
```bash
python FollowWeb/examples/generate_instagram_sigma.py
```

This will generate an interactive HTML visualization from the example Instagram data.

## Performance

The Sigma.js renderer with WebGL can efficiently handle:
- ✓ 10,000+ nodes
- ✓ 100,000+ edges
- ✓ Real-time interactions
- ✓ Smooth animations

For very large networks (>50,000 nodes), consider:
- Disabling labels (`show_labels: False`)
- Using k-core filtering to reduce graph size
- Applying community detection to focus on subgraphs

## Browser Compatibility

The Instagram template requires:
- Modern browser with WebGL support
- JavaScript enabled
- Recommended: Chrome, Firefox, Edge, Safari (latest versions)

## Customization

To customize the template:

1. Copy `sigma_instagram.html` to a new file
2. Modify colors, styles, or functionality
3. Use your custom template:

```python
renderer = SigmaRenderer(
    vis_config,
    template_name="my_custom_template.html"
)
```

## Troubleshooting

**Nodes are all the same color:**
- Ensure nodes have `followers_count` and `following_count` attributes
- Check that the Instagram template is selected

**Layout doesn't work:**
- Ensure graphology-layout-forceatlas2 CDN is accessible
- Check browser console for JavaScript errors

**Search doesn't find users:**
- Search is case-insensitive and uses partial matching
- Ensure the username exists in the graph

**Visualization is slow:**
- Reduce graph size with filtering
- Disable labels for large graphs
- Use a more powerful device with better GPU
