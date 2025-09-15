# FollowWeb

FollowWeb is a Python tool designed to scrape, analyze, and visualize social network data from Instagram. It consists of two main components: a scraper to gather follower/following data and a visualizer to generate an interactive HTML graph. This graph reveals the underlying structure of the network, identifies communities, and highlights the most influential users.



## Features

-   **Instagram Data Scraping**: Logs into Instagram to collect follower and following lists for a target user and, optionally, their connections up to a specified depth.
-   **Interactive Visualization**: Generates a dynamic and explorable network graph in a single HTML file using the PyVis library.
-   **Comprehensive Network Analysis**: Calculates key network metrics to provide deep insights:
    -   **Community Detection**: Employs the Louvain method to find and color-code distinct communities or cliques.
    -   **Centrality Measures**: Computes **Degree**, **Betweenness**, and **Eigenvector** centrality to identify the most important and influential nodes in the network.
-   **Intelligent Pruning**: Includes an option to iteratively remove less-connected nodes, helping to declutter the graph and focus on the core network structure.
-   **Configurable & Modular**: All settings are managed through a clean `config.yaml` file, and the scraper and visualizer are separated into distinct, manageable modules.

---

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

---

## Configuration

Before running the tool, you must configure your settings in the `config.yaml` file.

1.  **Open `config.yaml` in a text editor.**
2.  **Add your Instagram credentials**:
    ```yaml
    instagram:
      username: "YOUR_INSTAGRAM_USERNAME"
    ```
3.  **Review other settings**: Adjust the default scraper `depth`, `output_file`, and `visualization` parameters as needed.

config.yaml parameter guide:
## `instagram`

This section contains the credentials required to log into Instagram for scraping.

* **`username`**: Your Instagram account's username. The script will use this account to perform the scraping.
* **`password`**: The password for your Instagram account. It's stored in plain text, so ensure the file is kept secure.

---

## `scraper`

This section controls the behavior of the data collection script (`FollowWeb_Scraper.py`).

* **`output_file`**: The name of the file where the scraped network data will be saved. It's set to `"followers.json"` by default.
* **`depth`**: An integer that determines how deep the scraper will go into the network.
    * **`depth: 1`**: Scrapes only the followers and following of the initial target user (your `username`).
    * **`depth: 2`**: Scrapes the initial target user **and** all of their followers' and followees' connections. This can result in a very large amount of data and take a long time.

---

## `visualization`

This section configures the network analysis and the final interactive HTML output.

* **`input_file`**: The JSON data file that the visualization script will read from. This should typically match the `output_file` from the `scraper` section.

### `pruning`

This subsection controls the filtering process to focus on the core of the network.

* **`min_connections`**: The minimum number of connections (followers + following) a user must have to be included in the final graph. Nodes with fewer connections than this value are removed, which helps to reduce clutter.

### `visualization_settings`

These parameters directly affect the appearance and properties of the generated HTML graph.

* **`width`**: The width of the visualization canvas. `"100%"` makes it responsive to the browser window's width.
* **`height`**: The height of the visualization canvas. `"90vh"` means it will take up 90% of the browser's viewport height.
* **`notebook`**: A boolean (`True` or `False`) that, if set to `True`, configures the output to be displayed inline within a Jupyter Notebook. For generating a standalone HTML file, this should be `False`.
* **`base_node_size`**: The minimum size for a node in the graph, representing a user with very few connections.
* **`node_size_multiplier`**: A factor that scales the size of a node based on its number of connections. A higher value will create a greater size difference between poorly-connected and well-connected nodes.
* **`scaling_algorithm`**: Determines how node size increases with the number of connections.
    * **`"logarithmic"`** (default): Node sizes increase more slowly as connections get very high. This is useful for preventing super-popular accounts from becoming excessively large and obscuring the graph.
    * **`"linear"`**: Node size is directly proportional to the number of connections.

---

## Usage

The tool is operated from `main.py` and has two primary actions: `scrape` and `visualize`.

### Step 1: Scrape the Data

Run the `scrape` command to log into Instagram and gather the network data. The data will be saved to the JSON file specified in your `config.yaml` (`followers.json` by default).

```bash
# Scrape data using the depth set in config.yaml
python main.py scrape

# Override the depth from the command line (e.g., scrape 2 levels deep)
python main.py scrape --depth 2
```

The scraper will create a session file the first time you log in, so you won't need to enter your password or 2FA code on subsequent runs.

### Step 2: Visualize the Network

Once you have a JSON data file, run the `visualize` command to analyze it and generate the interactive HTML graph.

```bash
# Visualize the data using the settings from config.yaml
python main.py visualize

# Override the minimum connections for pruning
python main.py visualize --min-connections 10

# Specify a different input file
python main.py visualize --input my_other_data.json --min-connections 5
```

This command will:
1.  Read the network data from the specified JSON file.
2.  Prune the graph, keeping only nodes with the specified minimum number of connections.
3.  Analyze the pruned graph for communities and centrality.
4.  Generate an interactive HTML file named `FollowWeb_Visualization_[min_connections].html`.

---

## Understanding the Visualization

-   **Nodes**: Represent individual Instagram users.
-   **Edges**: Represent the "follows" relationship. An arrow from `UserA` to `UserB` means `UserA` follows `UserB`.
-   **Node Size**: Proportional to the node's **degree** (total number of connections). Larger nodes are more connected.
-   **Node Color**: Represents the **community** the node belongs to. Nodes of the same color are part of a more tightly-knit group.
-   **Tooltips**: Hover over any node to see its username, total connection count, and community ID.
-   **Interactive Controls**: The generated HTML file includes a control panel to adjust the physics and layout of the graph in real-time in your browser.