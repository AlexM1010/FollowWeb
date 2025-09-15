# FollowWeb_Scrape.py

# Import necessary libraries
import instaloader
import argparse
import yaml
import json
import os
from itertools import chain
import time
import random
import sys

# Added more specific exceptions
from instaloader.exceptions import (
    TooManyRequestsException, 
    ConnectionException, 
    ProfileNotExistsException, 
    PrivateProfileNotFollowedException
)

# The function returns a tuple: (data, status_code)
# This allows the main loop to make smarter decisions based on the outcome.
def get_profile_data(L, username, config):
    """
    Retrieves profile data with a robust retry and error handling mechanism.
    Returns a tuple containing the data and a status code ('SUCCESS', 'SKIP', 'HALT').
    """
    robust_cfg = config['scraper']['robustness']
    max_retries = robust_cfg['max_retries']
    base_wait_time = robust_cfg['base_wait_time_seconds']

    for attempt in range(max_retries):
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            followers = [follower.username for follower in profile.get_followers()]
            followees = [followee.username for followee in profile.get_followees()]
            # On success, return data and SUCCESS status
            return (followers, followees), "SUCCESS"
        
        # Handle non-existent or private profiles gracefully by skipping them.
        except (ProfileNotExistsException, PrivateProfileNotFollowedException) as e:
            print(f"Skipping {username}: {type(e).__name__}.")
            return None, "SKIP"
            
        # Handle rate limiting and connection issues with retries
        except (TooManyRequestsException, ConnectionException) as e:
            if attempt < max_retries - 1:
                wait_time = base_wait_time * (1.5 ** attempt) + random.uniform(0, 15)
                print(f"{type(e).__name__} on {username}. Waiting {wait_time:.2f}s before retry ({attempt + 2}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"Could not get data for {username} after {max_retries} attempts: {e}")
                # If it's a rate limit error after all retries, signal a HALT.
                if isinstance(e, TooManyRequestsException):
                    return None, "HALT"
                # For other connection issues, just signal a SKIP.
                else:
                    return None, "SKIP"
        
        # Handle any other unexpected errors by skipping the user.
        except Exception as e:
            print(f"An unexpected error occurred for {username}: {e}")
            return None, "SKIP"
            
    # Fallback return, should not be reached in normal operation.
    return None, "SKIP"

def scrape_data(config):
    """
    Scrapes Instagram data with state management for resumability.
    """
    username = config['instagram']['username']
    output_file = config['scraper']['output_file']
    depth = config['scraper']['depth']
    robust_cfg = config['scraper']['robustness']
    
    # --- Instaloader setup ---
    L = instaloader.Instaloader()
    try:
        print(f"Attempting to load session for {username}...")
        L.load_session_from_file(username, username)
        print("Session loaded successfully.")
    except FileNotFoundError:
        print("Session file not found. Logging in...")
        try:
            L.interactive_login(username)
            L.save_session_to_file(username)
            print("Logged in and session saved.")
        except Exception as e:
            print(f"Login failed: {e}")
            return

    # --- State Management for Resumability ---
    queue_file = 'queue.json'
    scraped_file = 'scraped_users.json'
    
    # Load state from files if they exist, otherwise start fresh
    if os.path.exists(queue_file) and os.path.exists(scraped_file):
        print("Resuming previous scrape session...")
        with open(queue_file, 'r') as f:
            queue = json.load(f)
        with open(scraped_file, 'r') as f:
            scraped_users = set(json.load(f))
    else:
        print("Starting a new scrape session.")
        queue = [(username, 1)]  # Queue stores tuples of (username, current_depth)
        scraped_users = set()

    # --- Scraping Logic ---
    print(f"\nStarting scrape for '{username}' at depth {depth}...")
    
    # Load existing data if output file already has content
    all_data_list = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                all_data_list = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Output file '{output_file}' is corrupted. Starting with an empty list.")

    users_scraped_this_session = 0
    while queue:
        current_user, current_depth = queue.pop(0)

        if current_user in scraped_users or current_depth > depth:
            continue
        
        print(f"[{len(scraped_users) + 1}] Scraping (Depth {current_depth}/{depth}): {current_user}")
        
        # Get both result and the reason/status code from the function.
        result, reason = get_profile_data(L, current_user, config)

        # --- Handle Scraping Outcome ---
        # Only halt if the reason is specifically a rate-limit failure.
        if reason == "HALT":
            print(f"Persistent rate limit encountered. Halting script to protect session.")
            # Put the user we failed on back in the queue for the next run
            queue.insert(0, (current_user, current_depth))
            print(f"\n--- Saving progress before exit... ---")
            with open(queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f)
            with open(scraped_file, 'w', encoding='utf-8') as f:
                json.dump(list(scraped_users), f)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data_list, f, indent=4)
            sys.exit("Exiting due to rate limit.") # Use sys.exit for a clean stop.

        # If we didn't halt, we mark the user as processed for this session.
        # This prevents retrying a user that was skipped (e.g., private profile).
        scraped_users.add(current_user)
        users_scraped_this_session += 1

        # Only process data if the scrape was successful.
        if reason == "SUCCESS":
            followers, followees = result
            all_data_list.append({
                "user": current_user,
                "followers": followers,
                "following": followees 
            })

            # If we haven't reached max depth, add this user's connections to the queue
            if current_depth < depth:
                connections_to_scrape = set(chain(followers, followees))
                for user_to_add in connections_to_scrape:
                    if user_to_add not in scraped_users and not any(user_to_add in item for item in queue):
                        queue.append((user_to_add, current_depth + 1))
        
        # NOTE: The "SKIP" reason is handled implicitly. The user is added to
        # scraped_users, but the "SUCCESS" block is skipped, and the loop continues.

        # --- Proactive Throttling ---
        delay = random.uniform(robust_cfg['request_min_delay'], robust_cfg['request_max_delay'])
        print(f"Waiting for {delay:.2f} seconds before next request...")
        time.sleep(delay)

        # Add a more substantial, less frequent pause
        if users_scraped_this_session > 0 and users_scraped_this_session % 3 == 0:
            long_break = random.uniform(300, 600)
            print(f"\n--- Taking a long break for {long_break:.2f} seconds to avoid rate limits... ---")
            time.sleep(long_break)
        
        # --- Periodically save progress ---
        if users_scraped_this_session > 0 and users_scraped_this_session % robust_cfg['save_progress_interval'] == 0:
            print(f"\n--- Saving progress... ---")
            with open(queue_file, 'w') as f:
                json.dump(queue, f)
            with open(scraped_file, 'w') as f:
                json.dump(list(scraped_users), f)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data_list, f, indent=4)
            print("--- Progress saved. ---\n")

    # --- Final Save ---
    print(f"\nScraping complete. Saving final data...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data_list, f, indent=4)
    
    # Clean up state files after successful completion
    if os.path.exists(queue_file): os.remove(queue_file)
    if os.path.exists(scraped_file): os.remove(scraped_file)

    print(f"Data for {len(scraped_users)} users saved to {output_file}. State files cleaned up.")

def main():
    parser = argparse.ArgumentParser(description="A robust Instagram follower and followee scraper.")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config file.')
    parser.add_argument('--depth', type=int, help='Scrape depth. Overrides config file.')
    cli_args = parser.parse_args()

    try:
        with open(cli_args.config, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at '{cli_args.config}'.")
        return

    if cli_args.depth is not None:
        config['scraper']['depth'] = cli_args.depth
    
    scrape_data(config)

if __name__ == "__main__":
    main()