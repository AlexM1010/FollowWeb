#!/usr/bin/env python3
"""
Generate landing page for Freesound Network Explorer.

Wraps the latest visualization with Plausible Analytics tracking.
Can be extended to add metrics, charts, etc.

Usage:
    python generate_landing_page.py \
        --output-dir website \
        --metrics-history data/metrics_history.jsonl \
        --milestone-history data/milestone_history.jsonl \
        --visualizations Output/*.html \
        --plausible-domain your-domain.github.io
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional


def find_latest_visualization(viz_paths: list[Path]) -> Optional[Path]:
    """
    Find the most recent visualization file.

    Args:
        viz_paths: List of visualization file paths

    Returns:
        Path to latest visualization, or None if no files found
    """
    if not viz_paths:
        return None

    # Sort by modification time (most recent first)
    viz_paths_with_time = [(p, p.stat().st_mtime) for p in viz_paths if p.exists()]
    if not viz_paths_with_time:
        return None

    viz_paths_with_time.sort(key=lambda x: x[1], reverse=True)
    return viz_paths_with_time[0][0]


def inject_plausible_analytics(html_content: str, domain: str) -> str:
    """
    Inject Plausible Analytics script into HTML head.

    Args:
        html_content: Original HTML content
        domain: Plausible domain (e.g., 'your-site.github.io')

    Returns:
        HTML with Plausible script injected
    """
    plausible_script = f'''
    <!-- Plausible Analytics -->
    <script defer data-domain="{domain}" src="https://plausible.io/js/script.js"></script>
'''

    # Inject before closing </head> tag
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{plausible_script}\n</head>")
    else:
        # Fallback: inject after opening <head> tag
        html_content = html_content.replace("<head>", f"<head>\n{plausible_script}")

    return html_content


def generate_landing_page(
    output_dir: Path,
    metrics_history: Optional[Path],
    milestone_history: Optional[Path],
    visualizations: list[Path],
    plausible_domain: Optional[str] = None,
) -> bool:
    """
    Generate landing page for GitHub Pages.

    Wraps the latest visualization with Plausible Analytics tracking.
    Future: Can add metrics dashboard, growth charts, etc.

    Args:
        output_dir: Output directory for website
        metrics_history: Path to metrics history JSONL (for future use)
        milestone_history: Path to milestone history JSONL (for future use)
        visualizations: List of visualization HTML files
        plausible_domain: Domain for Plausible Analytics (optional)

    Returns:
        True if successful, False otherwise
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find latest visualization
    latest_viz = find_latest_visualization(visualizations)

    if not latest_viz:
        print("❌ No visualizations found")
        return False

    print(f"📊 Using latest visualization: {latest_viz.name}")

    # Read visualization HTML
    with open(latest_viz, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inject Plausible Analytics if domain provided
    if plausible_domain:
        print(f"📈 Injecting Plausible Analytics for domain: {plausible_domain}")
        html_content = inject_plausible_analytics(html_content, plausible_domain)

    # Update data file reference to use consistent naming
    # Replace timestamped data file reference with 'graph_data.json'
    json_filename = latest_viz.stem + "_data.json"
    if json_filename in html_content:
        html_content = html_content.replace(json_filename, "graph_data.json")
        print(f"✅ Updated data file reference: {json_filename} → graph_data.json")

    # Write to index.html
    index_path = output_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Landing page created: {index_path}")

    # Note: Data file will be copied by deployment workflow with consistent naming
    # This keeps the landing page generator focused on HTML generation

    # Future enhancement: Load metrics and milestone data
    # if metrics_history and metrics_history.exists():
    #     with open(metrics_history) as f:
    #         metrics = [json.loads(line) for line in f if line.strip()]
    #     # Generate metrics dashboard, growth charts, etc.

    # if milestone_history and milestone_history.exists():
    #     with open(milestone_history) as f:
    #         milestones = [json.loads(line) for line in f if line.strip()]
    #     # Display milestone achievements

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate landing page for Freesound Network Explorer"
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="Output directory for website"
    )
    parser.add_argument(
        "--metrics-history", type=Path, help="Path to metrics history JSONL file"
    )
    parser.add_argument(
        "--milestone-history", type=Path, help="Path to milestone history JSONL file"
    )
    parser.add_argument(
        "--visualizations",
        type=str,
        nargs="+",
        required=True,
        help="Paths to visualization HTML files (glob patterns supported)",
    )
    parser.add_argument(
        "--plausible-domain",
        type=str,
        help="Domain for Plausible Analytics (e.g., your-site.github.io)",
    )

    args = parser.parse_args()

    # Expand glob patterns and convert to Path objects
    viz_paths = []
    for pattern in args.visualizations:
        path = Path(pattern)
        if path.exists() and path.is_file():
            viz_paths.append(path)
        else:
            # Try glob pattern
            parent = path.parent if path.parent.exists() else Path(".")
            matches = list(parent.glob(path.name))
            viz_paths.extend(matches)

    print(f"🔍 Found {len(viz_paths)} visualization(s)")

    # Generate landing page
    success = generate_landing_page(
        args.output_dir,
        args.metrics_history,
        args.milestone_history,
        viz_paths,
        args.plausible_domain,
    )

    if success:
        print("\n✅ Landing page generation complete")
        sys.exit(0)
    else:
        print("\n❌ Landing page generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
