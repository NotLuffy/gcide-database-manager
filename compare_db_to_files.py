"""
Compare Database File Paths to Actual Repository Files

Shows the discrepancy between database entries and actual files.
"""

import sqlite3
import os

DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("DATABASE vs ACTUAL FILES COMPARISON")
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

print(f"\nRepository: {repo_path}\n")

# Get actual files in repository
actual_files = set()
if os.path.exists(repo_path):
    for filename in os.listdir(repo_path):
        if filename.lower().endswith('.nc'):
            full_path = os.path.join(repo_path, filename)
            actual_files.add(full_path.lower())

print(f"Actual .nc files in repository: {len(actual_files)}\n")

# Get database file paths
cursor.execute("""
    SELECT DISTINCT file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    ORDER BY file_path
""")

db_paths = set()
for (path,) in cursor.fetchall():
    db_paths.add(path.lower())

print(f"Unique file paths in database: {len(db_paths)}\n")

# Find differences
print("=" * 80)
print("ANALYSIS")
print("=" * 80)

# Files in DB but not in repository
in_db_not_repo = db_paths - actual_files
print(f"\nIn database but NOT in repository: {len(in_db_not_repo)}")

if in_db_not_repo:
    print("\nExamples (first 30):")
    for i, path in enumerate(sorted(in_db_not_repo)[:30]):
        filename = os.path.basename(path)
        print(f"  {filename}")

    if len(in_db_not_repo) > 30:
        print(f"  ... and {len(in_db_not_repo) - 30} more")

# Files in repository but not in DB
in_repo_not_db = actual_files - db_paths
print(f"\nIn repository but NOT in database: {len(in_repo_not_db)}")

if in_repo_not_db:
    print("\nExamples (first 30):")
    for i, path in enumerate(sorted(in_repo_not_db)[:30]):
        filename = os.path.basename(path)
        print(f"  {filename}")

    if len(in_repo_not_db) > 30:
        print(f"  ... and {len(in_repo_not_db) - 30} more")

# Files in both
in_both = db_paths & actual_files
print(f"\nIn BOTH database and repository: {len(in_both)}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"""
Actual repository files:       {len(actual_files):6,}
Database file_path entries:    {len(db_paths):6,}
Files in both:                 {len(in_both):6,}

DB entries for missing files:  {len(in_db_not_repo):6,} <-- PROBLEM
Files not in database:         {len(in_repo_not_db):6,}

EXPLANATION:
The database has {len(in_db_not_repo):,} entries pointing to files that don't exist.
These are "stale" database entries that should be cleaned up.

This happens when:
1. Files were deleted but database entries weren't removed
2. Duplicate resolution deleted files but kept database entries
3. Files were moved/renamed but database wasn't updated

RECOMMENDATION:
Create a cleanup script to:
1. Find all database entries where file doesn't exist
2. Remove these entries from programs table
3. Mark program numbers as AVAILABLE in registry
""")

conn.close()
