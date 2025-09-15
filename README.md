# FollowWeb

FollowWeb is a Python script for analyzing and visualizing social network data. It takes a list of users, their followers, and their followees, and generates an interactive HTML graph that reveals the structure of the network, identifies communities, and highlights influential nodes.

## Features

- **Interactive Visualization**: Generates an interactive and explorable network graph in an HTML file using the PyVis library.
- **Network Analysis**: Calculates key network metrics, including:
  - **Community Detection**: Uses the Louvain method to identify communities within the network.
  - **Centrality Measures**: Computes degree, betweenness, and eigenvector centrality to identify influential nodes.
- **Pruning**: Automatically removes less connected nodes to focus on the core network structure.
- **Customizable**: Easily configurable through command-line arguments.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. **Install the required libraries:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script from the command line, providing the path to your input file.

```bash
python FollowWeb_Visualization.py [your_input_file.txt] [options]
```

### Input File Format

The input file should be a text file with a specific triplet format for each user:
1.  Username
2.  A comma-separated list of followers
3.  A comma-separated list of users they follow (followees)

**Example:**
```
user1
followerA,followerB
user2,user3
user2
user1
user3
user3
user1,user2

```

### Command-line Arguments

- `input_file`: (Required) The path to the input text file.
- `--min-connections`: (Optional) The minimum number of connections for a node to be kept during the pruning process. Default is 6.
- `--output-filename`: (Optional) The name of the output HTML file. If not provided, it will be generated automatically based on the input file name.

### Example Command

```bash
python FollowWeb_Visualization.py _followers.txt --min-connections 5
```

This command will:
1.  Read the network data from `followers.txt`.
2.  Prune the graph, keeping only nodes with 5 or more connections.
3.  Analyze the pruned graph.
4.  Generate an interactive HTML file named `FollowWeb_followers_5.html`.

## Understanding the Visualization

- **Nodes**: Represent users in the network.
- **Edges**: Represent the "follows" relationship (an arrow from `userA` to `userB` means `userA` follows `userB`).
- **Node Size**: Proportional to the number of connections (degree). Larger nodes are more connected.
- **Node Color**: Represents the community the node belongs to. Nodes of the same color are part of the same community.
- **Tooltips**: Hover over a node to see its name, number of connections, and community ID.
- **Interactive Controls**: Use the physics controls to adjust the layout of the graph in real-time.
