"""Execute branch cleanup phase."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.branch_cleanup import BranchCleanupManager


def main():
    """Execute branch cleanup."""
    print("=" * 80)
    print("BRANCH CLEANUP PHASE")
    print("=" * 80)
    
    mgr = BranchCleanupManager()
    
    # List all branches
    print("\n1. Listing all branches...")
    branches = mgr.list_all_branches()
    print(f"   Found {len(branches)} branches")
    
    # Classify branches
    print("\n2. Classifying branches...")
    classified = mgr.classify_branches(branches)
    
    print(f"   - Merged: {len(classified['merged'])}")
    print(f"   - Stale: {len(classified['stale'])}")
    print(f"   - Active: {len(classified['active'])}")
    print(f"   - Protected: {len(classified['protected'])}")
    
    # Show details
    if classified['merged']:
        print("\n   Merged branches:")
        for b in classified['merged']:
            print(f"     - {b.name} (last commit: {b.last_commit_date.strftime('%Y-%m-%d')})")
    
    if classified['stale']:
        print("\n   Stale branches (no commits in 30+ days):")
        for b in classified['stale']:
            days = (b.last_commit_date.now(b.last_commit_date.tzinfo) - b.last_commit_date).days
            print(f"     - {b.name} ({days} days old)")
    
    if classified['active']:
        print("\n   Active branches:")
        for b in classified['active']:
            pr_info = f" (PR #{b.pr_number})" if b.has_open_pr else ""
            print(f"     - {b.name}{pr_info}")
    
    # Delete merged branches automatically
    print("\n3. Deleting merged branches...")
    if classified['merged']:
        deleted = mgr.delete_merged_branches(classified['merged'], dry_run=False)
        print(f"   Deleted {len(deleted)} branches")
    else:
        deleted = []
        print("   No merged branches to delete")
    
    # Generate report
    print("\n5. Generating cleanup report...")
    report_path = Path("analysis_reports") / f"branch_cleanup_{Path(__file__).stem}.json"
    report = mgr.generate_cleanup_report(classified, deleted, report_path)
    print(f"   Report saved to: {report_path}")
    
    print("\n" + "=" * 80)
    print("BRANCH CLEANUP COMPLETE")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Total branches: {report['summary']['total_branches']}")
    print(f"  - Deleted: {report['summary']['deleted']}")
    print(f"  - Stale (review needed): {report['summary']['stale']}")
    print(f"  - Active: {report['summary']['active']}")
    print(f"  - Protected: {report['summary']['protected']}")


if __name__ == "__main__":
    main()
