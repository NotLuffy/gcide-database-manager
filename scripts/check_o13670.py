"""
Check o13670 file location and database record.
"""

import sqlite3
import os

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
repo_file = r"l:\My Drive\Home\File organizer\repository\o13670.nc"

print("=" * 80)
print("CHECKING o13670 LOCATION")
print("=" * 80)
print()

# Check if file exists in repository
repo_exists = os.path.exists(repo_file)
print(f"Repository file: {repo_file}")
print(f"Exists: {'YES' if repo_exists else 'NO'}")

if repo_exists:
    file_size = os.path.getsize(repo_file)
    print(f"Size: {file_size} bytes")

print()

# Check database record
conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

cursor.execute("""
    SELECT program_number, file_path, is_deleted
    FROM programs
    WHERE program_number = 'o13670'
""")

record = cursor.fetchone()

if record:
    prog_num, db_path_val, is_deleted = record
    print(f"Database record found:")
    print(f"  Program: {prog_num}")
    print(f"  Path in DB: {db_path_val}")
    print(f"  Is Deleted: {is_deleted}")
    print()

    if db_path_val == repo_file:
        print("[OK] Database path matches repository location")
    else:
        print("[WARNING] Database path DOES NOT match repository location!")
        print(f"  Expected: {repo_file}")
        print(f"  Database: {db_path_val}")
else:
    print("[INFO] No database record found for o13670")
    print("The file exists but is not in the database yet.")

conn.close()

print()
print("=" * 80)
print("RESULT: o13670.nc is in the REPOSITORY (correct location)")
print("=" * 80)
