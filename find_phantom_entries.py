"""
Find Phantom Database Entries

Database entries that point to files that don't exist.
"""

import sqlite3
import os

DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("FINDING PHANTOM DATABASE ENTRIES")
print("=" * 80)

# Get all managed programs with file_path
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    ORDER BY program_number
""")

all_programs = cursor.fetchall()
print(f"\nChecking {len(all_programs)} database entries...\n")

phantom_entries = []
existing_entries = []

for prog_num, file_path, title in all_programs:
    if os.path.exists(file_path):
        existing_entries.append((prog_num, file_path, title))
    else:
        phantom_entries.append((prog_num, file_path, title))

print("=" * 80)
print("RESULTS")
print("=" * 80)

print(f"\nEntries with existing files: {len(existing_entries)}")
print(f"Phantom entries (file missing): {len(phantom_entries)}\n")

if phantom_entries:
    print("=" * 80)
    print("PHANTOM ENTRIES (First 50)")
    print("=" * 80)
    print()

    for prog_num, file_path, title in phantom_entries[:50]:
        print(f"Program: {prog_num}")
        print(f"  DB path: {file_path}")
        print(f"  Title: {title[:60] if title else '(no title)'}")
        print(f"  Status: FILE DOES NOT EXIST")
        print()

    if len(phantom_entries) > 50:
        print(f"... and {len(phantom_entries) - 50} more phantom entries\n")

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"""
Total database entries:  {len(all_programs):6,}
Files exist:             {len(existing_entries):6,}
Files missing:           {len(phantom_entries):6,}

These phantom entries should be removed from the database.
They are taking up space and causing the count mismatch.
""")

    # Ask if user wants to clean them up
    print("=" * 80)
    print("CLEANUP OPTIONS")
    print("=" * 80)
    print("""
Option 1: Remove phantom entries from database
  - Deletes database records for files that don't exist
  - Marks program numbers as AVAILABLE in registry
  - Recommended if files were deleted intentionally

Option 2: Keep entries but mark as not managed
  - Sets is_managed = 0 for these entries
  - Keeps records for historical purposes
  - Numbers stay marked as IN_USE

Run this script with cleanup option to proceed.
""")

else:
    print("\nNo phantom entries found! All database entries have existing files.")

conn.close()
