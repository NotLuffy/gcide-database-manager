"""
Registry Cleanup Utility
========================

This script cleans up any temporary IN_USE markings that may have been left
in the registry due to previous errors or unexpected window closures.

It resets any registry entries that are marked IN_USE but don't actually
have a corresponding program in the programs table.

Usage:
    python reset_registry_cleanup.py

This is safe to run anytime - it only affects orphaned registry entries.
"""

import sqlite3

def cleanup_registry():
    """Clean up orphaned IN_USE markings in the registry"""

    conn = sqlite3.connect('gcode_database.db')
    cursor = conn.cursor()

    print("="*80)
    print("REGISTRY CLEANUP UTILITY")
    print("="*80)
    print()

    # Get count of IN_USE entries in registry
    cursor.execute("SELECT COUNT(*) FROM program_number_registry WHERE status = 'IN_USE'")
    in_use_count = cursor.fetchone()[0]
    print(f"Registry entries marked IN_USE: {in_use_count}")

    # Get count of actual programs in database
    cursor.execute("SELECT COUNT(*) FROM programs")
    programs_count = cursor.fetchone()[0]
    print(f"Actual programs in database: {programs_count}")
    print()

    # Find orphaned IN_USE entries (marked IN_USE but no corresponding program)
    cursor.execute("""
        SELECT r.program_number
        FROM program_number_registry r
        WHERE r.status = 'IN_USE'
        AND NOT EXISTS (
            SELECT 1 FROM programs p
            WHERE p.program_number = r.program_number
        )
    """)

    orphaned = cursor.fetchall()
    orphan_count = len(orphaned)

    if orphan_count > 0:
        print(f"Found {orphan_count} orphaned IN_USE entries (no corresponding program)")
        print()
        print("These are likely temporary markings left from:")
        print("  - Preview window closed with X button")
        print("  - Error during preview")
        print("  - Application crash")
        print()

        response = input(f"Reset these {orphan_count} entries to AVAILABLE? (yes/no): ")

        if response.lower() == 'yes':
            # Reset orphaned entries to AVAILABLE
            cursor.execute("""
                UPDATE program_number_registry
                SET status = 'AVAILABLE', file_path = NULL
                WHERE status = 'IN_USE'
                AND NOT EXISTS (
                    SELECT 1 FROM programs p
                    WHERE p.program_number = program_number_registry.program_number
                )
            """)

            conn.commit()
            print()
            print(f"✓ Successfully reset {orphan_count} orphaned entries to AVAILABLE")
            print()

            # Show updated counts
            cursor.execute("SELECT COUNT(*) FROM program_number_registry WHERE status = 'AVAILABLE'")
            available = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM program_number_registry WHERE status = 'IN_USE'")
            in_use = cursor.fetchone()[0]

            print("Updated Registry Status:")
            print(f"  AVAILABLE: {available}")
            print(f"  IN_USE:    {in_use}")
            print()
        else:
            print("Cleanup cancelled - no changes made")
            print()
    else:
        print("✓ No orphaned entries found - registry is clean!")
        print()
        print("Registry Status:")

        cursor.execute("SELECT COUNT(*) FROM program_number_registry WHERE status = 'AVAILABLE'")
        available = cursor.fetchone()[0]
        print(f"  AVAILABLE: {available}")
        print(f"  IN_USE:    {in_use_count}")
        print()

    conn.close()

    print("="*80)
    print("CLEANUP COMPLETE")
    print("="*80)

if __name__ == '__main__':
    try:
        cleanup_registry()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
