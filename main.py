import argparse
import yaml
import os

# Import functions from other modules
from FollowWeb_Scraper import scrape_data
from FollowWeb_Visualization import load_graph_from_json, prune_graph, analyze_network, visualize_network

def main():
    parser = argparse.ArgumentParser(description="FollowWeb: Scrape Instagram data and visualize follower networks.")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config file.')
    
    # Subparsers for different actions
    subparsers = parser.add_subparsers(dest='action', required=True, help='Action to perform (scrape or visualize)')

    # Scrape subparser
    scrape_parser = subparsers.add_parser('scrape', help='Scrape Instagram follower data.')
    scrape_parser.add_argument('--depth', type=int, help='How many levels of followers to scrape. Overrides config.yaml.')

    # Visualize subparser
    visualize_parser = subparsers.add_parser('visualize', help='Visualize the scraped network data.')
    visualize_parser.add_argument('--input', type=str, help='Path to the JSON file containing scraped data. Overrides config.yaml.')
    visualize_parser.add_argument('--min_connections', type=int, help='Minimum number of connections for nodes to be included in visualization. Overrides config.yaml.')

    args = parser.parse_args()

    # Load configuration
    if not os.path.exists(args.config):
        print(f"Error: Config file not found at {args.config}")
        return

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    if args.action == 'scrape':
        print("--- Running Scraper ---")
        # Ensure target_profile is always the username
        config['instagram']['target_profile'] = config['instagram']['username']
        # Override config with CLI args if provided
        if args.depth:
            config['scraper']['depth'] = args.depth

        scrape_data(config)
        print("\n--- Scraping Finished ---")

    elif args.action == 'visualize':
        print("--- Running Visualization ---")
        vis_config = config['visualization']

        # Override config with CLI args if provided
        input_file = args.input if args.input else vis_config['input_file']
        min_connections = args.min_connections if args.min_connections is not None else vis_config['pruning']['min_connections']

        graph = load_graph_from_json(input_file)
        
        if graph.number_of_nodes() > 0:
            pruned_graph = prune_graph(graph, min_connections)
            if pruned_graph.number_of_nodes() > 0:
                analyzed_graph = analyze_network(pruned_graph)
                output_filename = f"FollowWeb_Visualization_{min_connections}.html"
                visualize_network(analyzed_graph, output_filename, config)
        print("\n--- Visualization Finished ---")

if __name__ == "__main__":
    main()
