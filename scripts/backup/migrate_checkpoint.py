#!/usr/bin/env python3
"""
Temporary migration script for Freesound checkpoint architecture.

This script migrates legacy checkpoint format to the new split architecture:
- Legacy: Single .pkl file with graph + metadata
- New: Separate files for graph topology, metadata cache, and checkpoint info

Run this once to migrate, then delete this script.
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_split_checkpoint_exists(checkpoint_dir: Path) -> bool:
    """Check if split checkpoint files exist."""
    required_files = [
        checkpoint_dir / "graph_topology.gpickle",
        checkpoint_dir / "metadata_cache.db",
        checkpoint_dir / "checkpoint_metadata.json",
    ]
    return all(f.exists() for f in required_files)


def check_legacy_checkpoint_exists(checkpoint_dir: Path) -> bool:
    """Check if legacy checkpoint file exists."""
    return (checkpoint_dir / "freesound_library.pkl").exists()


def migrate_checkpoint(checkpoint_dir: Path) -> bool:
    """
    Migrate legacy checkpoint to split architecture.

    Returns:
        True if migration successful, False otherwise
    """
    from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint
    from FollowWeb_Visualizor.data.storage import MetadataCache

    legacy_path = checkpoint_dir / "freesound_library.pkl"

    logger.info(f"Loading legacy checkpoint from: {legacy_path}")
    checkpoint = GraphCheckpoint(str(legacy_path))
    checkpoint_data = checkpoint.load()

    if not checkpoint_data:
        logger.error("Failed to load legacy checkpoint")
        return False

    graph = checkpoint_data["graph"]
    processed_ids = checkpoint_data["processed_ids"]
    sound_cache = checkpoint_data.get("sound_cache", {})
    metadata = checkpoint_data.get("metadata", {})

    logger.info(f"Loaded legacy checkpoint:")
    logger.info(f"  - Nodes: {graph.number_of_nodes()}")
    logger.info(f"  - Edges: {graph.number_of_edges()}")
    logger.info(f"  - Processed IDs: {len(processed_ids)}")
    logger.info(f"  - Sound cache entries: {len(sound_cache)}")

    # Create split checkpoint directory
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save graph topology (edges only, no attributes)
    import networkx as nx
    import pickle

    topology_path = checkpoint_dir / "graph_topology.gpickle"
    logger.info(f"Saving graph topology to: {topology_path}")
    with open(topology_path, "wb") as f:
        pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

    # 2. Create metadata cache and store node attributes
    metadata_db_path = checkpoint_dir / "metadata_cache.db"
    logger.info(f"Creating metadata cache: {metadata_db_path}")
    metadata_cache = MetadataCache(str(metadata_db_path), logger)

    # Extract metadata from graph nodes
    metadata_dict = {}
    for node_id in graph.nodes():
        node_data = dict(graph.nodes[node_id])
        metadata_dict[int(node_id)] = node_data

    # Bulk insert metadata
    if metadata_dict:
        metadata_cache.bulk_insert(metadata_dict)
        logger.info(f"Migrated {len(metadata_dict)} node metadata entries to SQLite")

    # 3. Save checkpoint metadata
    import json
    from datetime import datetime

    checkpoint_metadata = {
        "timestamp": datetime.now().isoformat(),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "processed_ids_count": len(processed_ids),
        "migration": "completed",
        "migrated_from": "legacy_checkpoint",
        "original_metadata": metadata,
    }

    metadata_path = checkpoint_dir / "checkpoint_metadata.json"
    logger.info(f"Saving checkpoint metadata to: {metadata_path}")
    with open(metadata_path, "w") as f:
        json.dump(checkpoint_metadata, f, indent=2)

    # 4. Save processed IDs (for incremental loading)
    processed_ids_path = checkpoint_dir / "processed_ids.json"
    logger.info(f"Saving processed IDs to: {processed_ids_path}")
    with open(processed_ids_path, "w") as f:
        json.dump(list(processed_ids), f)

    logger.info("✅ Migration completed successfully!")
    return True


def main():
    """Main migration workflow."""
    checkpoint_dir = Path("data/freesound_library")

    logger.info("=" * 60)
    logger.info("Freesound Checkpoint Migration Script")
    logger.info("=" * 60)

    # Check if checkpoint directory exists
    if not checkpoint_dir.exists():
        logger.info("✅ No checkpoint directory found - nothing to migrate")
        return 0

    # Check if split checkpoint already exists
    if check_split_checkpoint_exists(checkpoint_dir):
        logger.info("✅ Split checkpoint already exists")

        # Check if legacy checkpoint still exists
        if check_legacy_checkpoint_exists(checkpoint_dir):
            legacy_path = checkpoint_dir / "freesound_library.pkl"
            logger.info(f"⚠️  Legacy checkpoint still exists: {legacy_path}")
            logger.info(
                "   You can safely delete it after verifying the split checkpoint works"
            )
            logger.info(f"   Command: rm {legacy_path}")
        else:
            logger.info("✅ Legacy checkpoint already removed")

        return 0

    # Check if legacy checkpoint exists
    if not check_legacy_checkpoint_exists(checkpoint_dir):
        logger.info("✅ No legacy checkpoint found - nothing to migrate")
        return 0

    # Perform migration
    logger.info("🔄 Starting migration from legacy to split checkpoint...")
    try:
        success = migrate_checkpoint(checkpoint_dir)

        if success:
            logger.info("")
            logger.info("=" * 60)
            logger.info("Migration Complete!")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Verify the split checkpoint works:")
            logger.info(
                "   python generate_freesound_visualization.py --max-samples 10"
            )
            logger.info("")
            logger.info("2. If successful, delete the legacy checkpoint:")
            logger.info(f"   rm {checkpoint_dir / 'freesound_library.pkl'}")
            logger.info("")
            logger.info("3. Delete this migration script:")
            logger.info("   rm migrate_checkpoint.py")
            return 0
        else:
            logger.error("❌ Migration failed")
            return 1

    except Exception as e:
        logger.error(f"❌ Migration failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
