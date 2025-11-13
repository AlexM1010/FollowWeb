#!/usr/bin/env python3
"""
Milestone Detection Script for Freesound Pipeline

Detects when the node count crosses 100-node boundaries and determines
if milestone actions should be triggered.

Usage:
    python detect_milestone.py --checkpoint-dir data/freesound_library --output milestone_status.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_checkpoint_metadata(checkpoint_dir: Path) -> Optional[Dict]:
    """
    Load checkpoint metadata from JSON file.
    
    Args:
        checkpoint_dir: Path to checkpoint directory
        
    Returns:
        Dictionary with checkpoint metadata or None if not found
    """
    metadata_path = checkpoint_dir / "checkpoint_metadata.json"
    
    if not metadata_path.exists():
        logger.error(f"Checkpoint metadata not found: {metadata_path}")
        return None
    
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        logger.info(f"Loaded checkpoint metadata: {metadata.get('nodes', 0)} nodes")
        return metadata
    except Exception as e:
        logger.error(f"Failed to load checkpoint metadata: {e}")
        return None


def load_milestone_history(checkpoint_dir: Path) -> list:
    """
    Load milestone history from JSONL file.
    
    Args:
        checkpoint_dir: Path to checkpoint directory
        
    Returns:
        List of milestone records (empty if file doesn't exist)
    """
    history_path = checkpoint_dir.parent / "milestone_history.jsonl"
    
    if not history_path.exists():
        logger.info("No milestone history found (first run)")
        return []
    
    try:
        milestones = []
        with open(history_path, 'r') as f:
            for line in f:
                if line.strip():
                    milestones.append(json.loads(line))
        logger.info(f"Loaded {len(milestones)} milestone records")
        return milestones
    except Exception as e:
        logger.warning(f"Failed to load milestone history: {e}")
        return []


def check_milestone(checkpoint_dir: Path) -> Dict:
    """
    Check if node count crossed 100-node boundary.
    
    Args:
        checkpoint_dir: Path to checkpoint directory
        
    Returns:
        Dictionary with milestone status:
        {
            'is_milestone': bool,
            'current_nodes': int,
            'previous_milestone_nodes': int,
            'milestone_number': int,
            'nodes_since_last_milestone': int
        }
    """
    # Load current checkpoint metadata
    metadata = load_checkpoint_metadata(checkpoint_dir)
    if not metadata:
        logger.error("Cannot determine milestone status without checkpoint metadata")
        return {
            'is_milestone': False,
            'current_nodes': 0,
            'previous_milestone_nodes': 0,
            'milestone_number': 0,
            'nodes_since_last_milestone': 0,
            'error': 'checkpoint_metadata_not_found'
        }
    
    current_nodes = metadata.get('nodes', 0)
    
    # Load milestone history
    milestone_history = load_milestone_history(checkpoint_dir)
    
    # Get last milestone node count
    last_milestone_nodes = 0
    if milestone_history:
        last_milestone_nodes = milestone_history[-1].get('nodes', 0)
    
    # Calculate milestone numbers
    current_milestone = current_nodes // 100
    last_milestone = last_milestone_nodes // 100
    
    # Check if crossed 100-node boundary
    is_milestone = current_milestone > last_milestone and current_nodes >= 100
    
    result = {
        'is_milestone': is_milestone,
        'current_nodes': current_nodes,
        'previous_milestone_nodes': last_milestone_nodes,
        'milestone_number': current_milestone,
        'nodes_since_last_milestone': current_nodes - last_milestone_nodes
    }
    
    if is_milestone:
        logger.info(f"🎉 Milestone {current_milestone} detected! ({current_nodes} nodes)")
    else:
        logger.info(f"No milestone detected ({current_nodes} nodes, {current_nodes % 100} until next)")
    
    return result


def save_milestone_status(output_path: Path, status: Dict) -> bool:
    """
    Save milestone status to JSON file.
    
    Args:
        output_path: Path to output JSON file
        status: Milestone status dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(output_path, 'w') as f:
            json.dump(status, f, indent=2)
        logger.info(f"Milestone status saved to: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save milestone status: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Detect milestone boundaries in Freesound pipeline'
    )
    parser.add_argument(
        '--checkpoint-dir',
        type=str,
        required=True,
        help='Path to checkpoint directory (e.g., data/freesound_library)'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Path to output JSON file (e.g., milestone_status.json)'
    )
    
    args = parser.parse_args()
    
    # Convert to Path objects
    checkpoint_dir = Path(args.checkpoint_dir)
    output_path = Path(args.output)
    
    # Validate checkpoint directory
    if not checkpoint_dir.exists():
        logger.error(f"Checkpoint directory not found: {checkpoint_dir}")
        return 1
    
    # Check milestone status
    logger.info("=" * 60)
    logger.info("Freesound Milestone Detection")
    logger.info("=" * 60)
    
    status = check_milestone(checkpoint_dir)
    
    # Save status to output file
    if not save_milestone_status(output_path, status):
        return 1
    
    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Current nodes: {status['current_nodes']}")
    logger.info(f"Milestone detected: {status['is_milestone']}")
    if status['is_milestone']:
        logger.info(f"Milestone number: {status['milestone_number']}")
        logger.info(f"Nodes since last milestone: {status['nodes_since_last_milestone']}")
    else:
        nodes_until_next = 100 - (status['current_nodes'] % 100)
        logger.info(f"Nodes until next milestone: {nodes_until_next}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
