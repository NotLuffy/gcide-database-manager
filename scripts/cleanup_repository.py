"""
One-time Repository Cleanup Script
Consolidates duplicates and archives orphan files
"""

from repository_manager import RepositoryManager
import sys


def main():
    print("=" * 80)
    print("REPOSITORY CLEANUP SCRIPT")
    print("=" * 80)
    print()

    # Initialize manager
    manager = RepositoryManager('gcode_database.db', 'repository')

    # Get initial stats
    print("📊 Initial Repository State:")
    print("-" * 80)

    orphans = manager.detect_orphan_files()
    duplicates = manager.detect_duplicates()
    archive_stats = manager.get_archive_stats()

    print(f"  Orphan files (not in database):     {len(orphans):,}")
    print(f"  Programs with duplicate files:      {len(duplicates):,}")
    print(f"  Files already in archive:           {archive_stats['total_files']:,}")
    print(f"  Archive size:                       {archive_stats['total_size_mb']} MB")
    print()

    if len(orphans) == 0 and len(duplicates) == 0:
        print("✅ Repository is already clean! No action needed.")
        return

    # Ask for confirmation
    print("⚠️  CLEANUP PLAN:")
    print("-" * 80)
    if len(orphans) > 0:
        print(f"  1. Archive {len(orphans):,} orphan files → archive/")
    if len(duplicates) > 0:
        print(f"  2. Consolidate {len(duplicates):,} programs with duplicates")
        print("     (Keep .nc files, archive others)")
    print()

    response = input("Proceed with cleanup? [y/N]: ").strip().lower()

    if response != 'y':
        print("\n❌ Cleanup cancelled by user")
        return

    print()
    print("=" * 80)
    print("STARTING CLEANUP")
    print("=" * 80)
    print()

    # Step 1: Cleanup orphans
    if len(orphans) > 0:
        print("Step 1: Cleaning up orphan files...")
        print("-" * 80)

        result = manager.cleanup_orphans(action='archive', dry_run=False)

        print(f"✅ Archived {result['count']} orphan files")
        if result.get('errors', 0) > 0:
            print(f"⚠️  Errors: {result['errors']}")
        print()

    # Step 2: Consolidate duplicates
    if len(duplicates) > 0:
        print("Step 2: Consolidating duplicate files...")
        print("-" * 80)

        result = manager.consolidate_duplicates(dry_run=False)

        print(f"✅ Consolidated {result['count']} programs")
        if result.get('errors', 0) > 0:
            print(f"⚠️  Errors: {result['errors']}")
        print()

    # Final stats
    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print()

    # Re-check
    orphans_after = manager.detect_orphan_files()
    duplicates_after = manager.detect_duplicates()
    archive_stats_after = manager.get_archive_stats()

    print("📊 Final Repository State:")
    print("-" * 80)
    print(f"  Orphan files:                       {len(orphans_after):,} (was {len(orphans):,})")
    print(f"  Programs with duplicates:           {len(duplicates_after):,} (was {len(duplicates):,})")
    print(f"  Files in archive:                   {archive_stats_after['total_files']:,} (was {archive_stats['total_files']:,})")
    print(f"  Archive size:                       {archive_stats_after['total_size_mb']} MB (was {archive_stats['total_size_mb']} MB)")
    print()

    print("✅ Repository cleanup successful!")
    print()
    print("📁 Archived files are stored in: archive/")
    print("   - Organized by date: archive/2025-12-10/")
    print("   - Can be restored using the Archive Manager GUI")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
