#!/usr/bin/env python3
"""
Generate metrics dashboard from pipeline execution history.

This script reads the metrics history file and generates a 4-panel visualization
showing pipeline health and trends over time:
- Graph growth (nodes and edges)
- API requests used per run
- Cache hit ratio
- Execution duration

The dashboard is saved as a PNG file for easy monitoring.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def load_metrics_history(metrics_file: Path) -> pd.DataFrame:
    """
    Load metrics history from JSONL file.
    
    Args:
        metrics_file: Path to metrics_history.jsonl file
    
    Returns:
        DataFrame with metrics data
    
    Raises:
        FileNotFoundError: If metrics file doesn't exist
        ValueError: If file is empty or invalid
    """
    if not metrics_file.exists():
        raise FileNotFoundError(f"Metrics file not found: {metrics_file}")
    
    # Read JSONL file (one JSON object per line)
    records: List[Dict[str, Any]] = []
    
    with open(metrics_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                logging.warning(f"Skipping invalid JSON on line {line_num}: {e}")
    
    if not records:
        raise ValueError(f"No valid records found in {metrics_file}")
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Parse timestamp column
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    
    return df


def generate_dashboard(df: pd.DataFrame, output_path: Path, logger: logging.Logger) -> None:
    """
    Generate 4-panel metrics dashboard.
    
    Args:
        df: DataFrame with metrics data
        output_path: Path to save dashboard PNG
        logger: Logger instance
    """
    # Create figure with 2x2 subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Freesound Pipeline Metrics Dashboard', fontsize=16, fontweight='bold')
    
    # Panel 1: Graph Growth (top-left)
    ax1 = axes[0, 0]
    if 'nodes_added' in df.columns and 'edges_added' in df.columns:
        # Calculate cumulative totals
        df['total_nodes'] = df.get('total_nodes', df['nodes_added'].cumsum())
        df['total_edges'] = df.get('total_edges', df['edges_added'].cumsum())
        
        ax1.plot(df['timestamp'], df['total_nodes'], marker='o', label='Total Nodes', linewidth=2)
        ax1.plot(df['timestamp'], df['total_edges'], marker='s', label='Total Edges', linewidth=2)
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Count', fontsize=12)
        ax1.set_title('Graph Growth Over Time', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
    else:
        ax1.text(0.5, 0.5, 'No graph growth data available', 
                ha='center', va='center', fontsize=12)
        ax1.set_title('Graph Growth Over Time', fontsize=14, fontweight='bold')
    
    # Panel 2: API Requests (top-right)
    ax2 = axes[0, 1]
    if 'api_requests' in df.columns:
        ax2.bar(df['timestamp'], df['api_requests'], alpha=0.7, label='Requests Used')
        
        # Add limit line
        max_requests = df.get('max_requests', pd.Series([1950] * len(df))).iloc[0]
        ax2.axhline(y=max_requests, color='r', linestyle='--', linewidth=2, label=f'Limit ({max_requests})')
        
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('API Requests', fontsize=12)
        ax2.set_title('API Requests Used Per Run', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.tick_params(axis='x', rotation=45)
    else:
        ax2.text(0.5, 0.5, 'No API request data available', 
                ha='center', va='center', fontsize=12)
        ax2.set_title('API Requests Used Per Run', fontsize=14, fontweight='bold')
    
    # Panel 3: Cache Hit Ratio (bottom-left)
    ax3 = axes[1, 0]
    if 'cache_hit_ratio' in df.columns:
        ax3.plot(df['timestamp'], df['cache_hit_ratio'] * 100, 
                marker='o', color='green', linewidth=2)
        ax3.set_xlabel('Date', fontsize=12)
        ax3.set_ylabel('Cache Hit Ratio (%)', fontsize=12)
        ax3.set_title('Cache Hit Ratio Over Time', fontsize=14, fontweight='bold')
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3)
        ax3.tick_params(axis='x', rotation=45)
    else:
        ax3.text(0.5, 0.5, 'No cache hit ratio data available', 
                ha='center', va='center', fontsize=12)
        ax3.set_title('Cache Hit Ratio Over Time', fontsize=14, fontweight='bold')
    
    # Panel 4: Execution Duration (bottom-right)
    ax4 = axes[1, 1]
    if 'duration_seconds' in df.columns:
        # Convert to minutes
        df['duration_minutes'] = df['duration_seconds'] / 60
        
        ax4.plot(df['timestamp'], df['duration_minutes'], 
                marker='o', color='purple', linewidth=2)
        ax4.set_xlabel('Date', fontsize=12)
        ax4.set_ylabel('Duration (minutes)', fontsize=12)
        ax4.set_title('Execution Duration Over Time', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='x', rotation=45)
    else:
        ax4.text(0.5, 0.5, 'No duration data available', 
                ha='center', va='center', fontsize=12)
        ax4.set_title('Execution Duration Over Time', fontsize=14, fontweight='bold')
    
    # Adjust layout to prevent overlap
    plt.tight_layout()
    
    # Save dashboard
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"✅ Dashboard saved to: {output_path}")
    
    # Close figure to free memory
    plt.close(fig)


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code (0 = success, non-zero = failure)
    """
    parser = argparse.ArgumentParser(
        description='Generate metrics dashboard from pipeline execution history'
    )
    parser.add_argument(
        '--metrics-file',
        type=Path,
        default=Path('data/metrics_history.jsonl'),
        help='Path to metrics history file (default: data/metrics_history.jsonl)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('Output/metrics_dashboard.png'),
        help='Path to save dashboard PNG (default: Output/metrics_dashboard.png)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    logger = setup_logging(args.log_level)
    
    try:
        logger.info("📊 Generating metrics dashboard...")
        logger.info(f"Reading metrics from: {args.metrics_file}")
        
        # Load metrics data
        df = load_metrics_history(args.metrics_file)
        logger.info(f"Loaded {len(df)} metric records")
        
        # Generate dashboard
        generate_dashboard(df, args.output, logger)
        
        logger.info("✅ Dashboard generation complete")
        return 0
    
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return 1
    
    except ValueError as e:
        logger.error(f"❌ Invalid data: {e}")
        return 1
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())
