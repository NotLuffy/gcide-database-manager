"""
Cleanup Missing Files from Database

This script removes database entries for files that:
1. Have NULL file_path AND don't exist in repository
2. Have file_path set BUT file doesn't exist

This cleans up orphaned entries from duplicate deletion.
"""

import sqlite3
import os
import re

# Database path
DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get repository path
cursor.execute("""
    SELECT file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    LIMIT 1
""")
result = cursor.fetchone()

if not result:
    print("ERROR: No managed files found")
    conn.close()
    exit()

repo_path = os.path.dirname(result[0])
print("=" * 80)
print("CLEANUP MISSING FILES FROM DATABASE")
print("=" * 80)
print(f"Repository: {repo_path}\n")

# Scan repository for all .nc files
nc_files = {}
if os.path.exists(repo_path):
    for filename in os.listdir(repo_path):
        if filename.lower().endswith('.nc'):
            base_name = os.path.splitext(filename)[0]
            nc_files[base_name.lower()] = filename

print(f"Found {len(nc_files)} .nc files in repository\n")

# Get all managed programs
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE is_managed = 1
    ORDER BY program_number
""")

all_programs = cursor.fetchall()
print(f"Found {len(all_programs)} managed programs in database\n")

print("=" * 80)
print("CHECKING FOR MISSING FILES")
print("=" * 80)

to_remove = []

for prog_num, file_path, title in all_programs:
    # Check if file exists
    exists_at_path = file_path and os.path.exists(file_path)

    if exists_at_path:
        continue  # File exists, keep it

    # File doesn't exist at stored path - try to find it
    base_prog = re.sub(r'[\(_]\d+[\)]?$', '', prog_num).lower()

    variations = [
        prog_num.lower(),
        base_prog,
        prog_num.replace('(', '_').replace(')', '').lower(),
    ]

    found = False
    for var in variations:
        if var in nc_files:
            found = True
            break

    if not found:
        # File doesn't exist anywhere
        to_remove.append((prog_num, file_path, title))
        print(f"REMOVE: {prog_num}")
        print(f"  Title: {title}")
        print(f"  DB path: {file_path if file_path else '(NULL)'}")
        print(f"  Reason: File not found in repository\n")

print("=" * 80)
print(f"SUMMARY: Found {len(to_remove)} entries to remove")
print("=" * 80)

if not to_remove:
    print("\nNo missing files found. Database is clean!")
    conn.close()
    exit()

print(f"\nThis will remove {len(to_remove)} database entries for files that don't exist.")
print("\nPrograms to remove:")
for prog_num, _, _ in to_remove[:20]:
    print(f"  - {prog_num}")

if len(to_remove) > 20:
    print(f"  ... and {len(to_remove) - 20} more")

# Auto-proceed with cleanup
print("\nProceeding with cleanup...")

print("\n" + "=" * 80)
print("REMOVING ENTRIES")
print("=" * 80)

removed_count = 0

for prog_num, file_path, title in to_remove:
    try:
        # Remove from programs table
        cursor.execute("""
            DELETE FROM programs
            WHERE program_number = ? AND is_managed = 1
        """, (prog_num,))

        # Mark as AVAILABLE in registry
        cursor.execute("""
            UPDATE program_number_registry
            SET status = 'AVAILABLE',
                file_path = NULL
            WHERE program_number = ?
        """, (prog_num,))

        removed_count += 1
        print(f"Removed: {prog_num}")

    except Exception as e:
        print(f"ERROR removing {prog_num}: {e}")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("CLEANUP COMPLETE")
print("=" * 80)
print(f"Removed {removed_count} database entries")
print(f"Registry updated - {removed_count} numbers marked as AVAILABLE")
print("\nYou can now:")
print("1. Run 'Repair File Paths' to fix remaining path issues")
print("2. Run 'Batch Rename Out-of-Range' to fix programs in wrong ranges")
