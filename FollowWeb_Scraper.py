# Import necessary libraries
import instaloader
import argparse
import yaml
import json
from itertools import chain

def get_profile_data(L, username):
    """
    Retrieves and returns the followers and followees of a target profile using an authenticated Instaloader instance.

    Args:
        L (instaloader.Instaloader): An authenticated Instaloader instance.
        username (str): The Instagram profile to scrape.

    Returns:
        tuple: A tuple containing two lists: followers and followees.
               Returns (None, None) if an error occurs.
    """
    try:
        # Get the profile of the target user
        profile = instaloader.Profile.from_username(L.context, username)
        # Get the list of followers
        followers = [follower.username for follower in profile.get_followers()]
        # Get the list of followees
        followees = [followee.username for followee in profile.get_followees()]
        return followers, followees
    except Exception as e:
        print(f"Could not get profile data for {username}: {e}")
        return None, None

def scrape_data(config):
    """
    Scrapes Instagram followers and followees based on the provided configuration and command-line arguments.
    """
    username = config['instagram']['username']
    output_file = config['scraper']['output_file']
    # This value can be overridden by the main.py script if a CLI arg is passed
    depth = config['scraper']['depth']

    # --- Instaloader setup and login ---
    L = instaloader.Instaloader()
    try:
        print(f"Attempting to load session for {username}...")
        L.load_session_from_file(username)
        print("Session loaded successfully.")
    except FileNotFoundError:
        print("Session file not found. Logging in...")
        try:
            # Using interactive_login is often better for handling 2FA.
            L.interactive_login(username)
            L.save_session_to_file(username)
            print("Logged in and session saved.")
        except Exception as e:
            print(f"Login failed: {e}")
            return

    # --- Scraping logic with depth control ---
    print(f"\nStarting scrape for '{username}' at depth {depth}...")

    all_data_list = [] # CHANGED: Data is now stored in a list to match the desired output format
    scraped_users = set()
    # Queue stores tuples of (username, current_depth)
    queue = [(username, 1)]

    while queue:
        current_user, current_depth = queue.pop(0)

        if current_user in scraped_users:
            continue
        
        # Also check depth here to avoid scraping beyond the specified limit
        if current_depth > depth:
            continue

        print(f"[{len(scraped_users) + 1}] Scraping (Depth {current_depth}/{depth}): {current_user}")
        followers, followees = get_profile_data(L, current_user)
        scraped_users.add(current_user)

        if followers is not None and followees is not None:
            # CHANGED: Appends a dictionary to the list in the desired format
            all_data_list.append({
                "user": current_user,
                "followers": followers,
                "following": followees # CHANGED: Key name to "following" to match your snippet
            })

            # If we haven't reached max depth, add this user's followers AND followees to the queue
            if current_depth < depth:
                # CHANGED: Combine followers and followees into a single set to handle duplicates efficiently.
                connections_to_scrape = set(chain(followers, followees))
                
                for user_to_add in connections_to_scrape:
                    if user_to_add not in scraped_users:
                        queue.append((user_to_add, current_depth + 1))

    # Save all collected data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # CHANGED: Dump the list of dictionaries into the JSON file
        json.dump(all_data_list, f, indent=4)

    print(f"\nScraping complete. Data for {len(scraped_users)} users saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Scrape Instagram followers and followees.")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config file.')
    parser.add_argument('--depth', type=int, help='How many levels of followers/followees to scrape. Overrides config.')
    cli_args = parser.parse_args()

    with open(cli_args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Override config with CLI argument if provided
    if cli_args.depth is not None:
        config['scraper']['depth'] = cli_args.depth
    
    scrape_data(config)

if __name__ == "__main__":
    main()