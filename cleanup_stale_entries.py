"""
Cleanup Stale Database Entries

Removes database entries for files that don't exist.
"""

import sqlite3
import os

DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("CLEANUP STALE DATABASE ENTRIES")
print("=" * 80)

# Get all managed programs
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    ORDER BY program_number
""")

all_programs = cursor.fetchall()
print(f"\nChecking {len(all_programs)} database entries...\n")

stale_entries = []

for prog_num, file_path, title in all_programs:
    if not os.path.exists(file_path):
        stale_entries.append((prog_num, file_path, title))

print("=" * 80)
print(f"FOUND {len(stale_entries)} STALE ENTRIES")
print("=" * 80)

if not stale_entries:
    print("\nNo stale entries found! Database is clean.")
    conn.close()
    exit()

print(f"\nThese {len(stale_entries)} entries point to files that don't exist.")
print("\nExamples (first 50):")

for prog_num, file_path, title in stale_entries[:50]:
    filename = os.path.basename(file_path)
    print(f"  {prog_num:15} -> {filename:30} ({title[:40] if title else ''})")

if len(stale_entries) > 50:
    print(f"  ... and {len(stale_entries) - 50} more")

print("\n" + "=" * 80)
print("CLEANUP PLAN")
print("=" * 80)
print(f"""
Will remove {len(stale_entries):,} database entries:
  1. Delete from programs table
  2. Mark as AVAILABLE in registry

This will:
  - Clean up database
  - Make program numbers available for reuse
  - Fix the count mismatch
""")

print("\nProceeding with cleanup...")

print("\n" + "=" * 80)
print("REMOVING STALE ENTRIES")
print("=" * 80)

removed_count = 0

for prog_num, file_path, title in stale_entries:
    try:
        # Remove from programs table
        cursor.execute("""
            DELETE FROM programs
            WHERE program_number = ? AND file_path = ?
        """, (prog_num, file_path))

        # Mark as AVAILABLE in registry (if not used by another program)
        cursor.execute("""
            SELECT COUNT(*) FROM programs
            WHERE program_number = ?
        """, (prog_num,))

        if cursor.fetchone()[0] == 0:
            # No other program uses this number, mark as AVAILABLE
            cursor.execute("""
                UPDATE program_number_registry
                SET status = 'AVAILABLE',
                    file_path = NULL
                WHERE program_number = ?
            """, (prog_num,))

        removed_count += 1

        if removed_count % 100 == 0:
            print(f"Removed {removed_count:,} entries...")

    except Exception as e:
        print(f"ERROR removing {prog_num}: {e}")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("CLEANUP COMPLETE")
print("=" * 80)
print(f"""
Removed {removed_count:,} stale database entries
Registry updated - numbers marked as AVAILABLE

BEFORE:
  Database entries: {len(all_programs):,}
  Stale entries: {len(stale_entries):,}

AFTER:
  Database entries: {len(all_programs) - removed_count:,}
  Stale entries: 0

The database should now match the repository file count!
""")
