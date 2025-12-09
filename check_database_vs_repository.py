"""
Check Database vs Repository Counts

Shows why database has more entries than physical files.
"""

import sqlite3
import os

DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("DATABASE vs REPOSITORY ANALYSIS")
print("=" * 80)

# Get repository path
cursor.execute("""
    SELECT file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    LIMIT 1
""")
result = cursor.fetchone()
repo_path = os.path.dirname(result[0])

# Count physical files
nc_files = set()
if os.path.exists(repo_path):
    for filename in os.listdir(repo_path):
        if filename.lower().endswith('.nc'):
            nc_files.add(filename.lower())

print(f"\nPhysical files in repository: {len(nc_files)}")

# Count database entries
cursor.execute("SELECT COUNT(*) FROM programs WHERE is_managed = 1")
total_managed = cursor.fetchone()[0]
print(f"Database entries (is_managed=1): {total_managed}")
print(f"Difference: {total_managed - len(nc_files)} extra database entries\n")

print("=" * 80)
print("BREAKDOWN OF DATABASE ENTRIES")
print("=" * 80)

# Count entries with NULL file_path
cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE is_managed = 1 AND file_path IS NULL
""")
null_paths = cursor.fetchone()[0]
print(f"\n1. NULL file_path: {null_paths}")
print(f"   (These should be cleaned up or repaired)")

# Count entries where file_path is set
cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
""")
has_paths = cursor.fetchone()[0]
print(f"\n2. Has file_path: {has_paths}")

# Count unique file paths (how many actual files are referenced)
cursor.execute("""
    SELECT COUNT(DISTINCT file_path)
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
""")
unique_paths = cursor.fetchone()[0]
print(f"   Unique file paths: {unique_paths}")
print(f"   Multiple entries for same file: {has_paths - unique_paths}")

# Check for duplicate file_path entries
cursor.execute("""
    SELECT file_path, COUNT(*) as count
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    GROUP BY file_path
    HAVING count > 1
    ORDER BY count DESC
    LIMIT 20
""")

duplicate_paths = cursor.fetchall()
print(f"\n   Files with multiple database entries (showing first 20):")

if duplicate_paths:
    for file_path, count in duplicate_paths:
        filename = os.path.basename(file_path)
        print(f"     {filename}: {count} entries")

        # Show which programs point to this file
        cursor.execute("""
            SELECT program_number, title
            FROM programs
            WHERE file_path = ?
            ORDER BY program_number
        """, (file_path,))

        programs = cursor.fetchall()
        for prog_num, title in programs[:5]:
            print(f"       - {prog_num}: {title[:50] if title else '(no title)'}")

        if len(programs) > 5:
            print(f"       ... and {len(programs) - 5} more")
        print()

    if len(duplicate_paths) > 20:
        print(f"   ... and {len(duplicate_paths) - 20} more files with duplicates")
else:
    print("     None found")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"""
Physical repository files:     {len(nc_files):6,}
Unique file_path in database:  {unique_paths:6,}
Total database entries:        {total_managed:6,}

Extra database entries:        {total_managed - unique_paths:6,}
  - NULL file_path:            {null_paths:6,}
  - Duplicate references:      {has_paths - unique_paths:6,}

EXPLANATION:
- Physical files ({len(nc_files):,}) are the actual .nc files in repository folder
- Database has {total_managed:,} entries because multiple program numbers
  can reference the same physical file
- This is normal when you have duplicates that share the same file
- After full cleanup, you can remove duplicate database entries
""")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("""
The extra database entries are likely from:
1. Type 1 duplicates (same program number, different files) - NOT YET RESOLVED
2. Programs that were marked as duplicates but entries not deleted
3. Old entries that should be cleaned up

To clean up:
1. Complete the duplicate resolution workflow (Manage Duplicates - All 3 passes)
2. The system SHOULD delete these duplicate entries automatically
3. If not, we may need to create a cleanup script to remove entries
   that point to the same file
""")

conn.close()
