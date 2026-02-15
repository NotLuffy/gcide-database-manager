"""
Complete diagnostic for o81300 file location issue.
"""

import sqlite3
import os
from pathlib import Path

print("=" * 80)
print("COMPLETE o81300 DIAGNOSTIC")
print("=" * 80)
print()

# Test all possible drive/path combinations
base_paths = [
    r"L:\My Drive\Home\File organizer",
    r"l:\My Drive\Home\File organizer",
    r"I:\My Drive\Home\File organizer",
    "L:/My Drive/Home/File organizer",
    "l:/My Drive/Home/File organizer",
    "I:/My Drive/Home/File organizer",
]

print("STEP 1: Check which base paths are accessible")
print("-" * 80)

accessible_paths = []
for base_path in base_paths:
    exists = os.path.exists(base_path)
    print(f"{base_path}: {'ACCESSIBLE' if exists else 'Not accessible'}")
    if exists:
        accessible_paths.append(base_path)

print()

if not accessible_paths:
    print("[ERROR] No accessible paths found!")
    exit(1)

# Use the first accessible path
working_base = accessible_paths[0]
print(f"Using: {working_base}")
print()

# Check repository folder
repo_path = os.path.join(working_base, "repository")
print("STEP 2: Check repository folder")
print("-" * 80)
print(f"Repository path: {repo_path}")
print(f"Exists: {os.path.exists(repo_path)}")
print()

# Find all o81300 files in repository
print("STEP 3: Search for o81300 files in repository")
print("-" * 80)

o81300_files = []
if os.path.exists(repo_path):
    for file in os.listdir(repo_path):
        if '81300' in file.lower():
            full_path = os.path.join(repo_path, file)
            size = os.path.getsize(full_path)
            o81300_files.append((file, full_path, size))
            print(f"  Found: {file}")
            print(f"    Full path: {full_path}")
            print(f"    Size: {size} bytes")

if not o81300_files:
    print("  [ERROR] No o81300 files found in repository!")
    print()
    print("  Checking archive folder...")
    archive_path = os.path.join(working_base, "archive", "2026-02-08")
    if os.path.exists(archive_path):
        for file in os.listdir(archive_path):
            if '81300' in file.lower():
                print(f"    Found in archive: {file}")
else:
    print()

# Check database
print("STEP 4: Check database record")
print("-" * 80)

db_path = os.path.join(working_base, "gcode_database.db")
print(f"Database path: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")
print()

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT program_number, file_path, is_deleted
            FROM programs
            WHERE program_number = 'o81300'
        """)

        record = cursor.fetchone()

        if record:
            prog_num, db_file_path, is_deleted = record
            print(f"Database record found:")
            print(f"  Program: {prog_num}")
            print(f"  Path in DB: {db_file_path}")
            print(f"  Is Deleted: {is_deleted}")
            print()

            # Check if database path exists
            if db_file_path:
                db_path_exists = os.path.exists(db_file_path)
                print(f"  File exists at DB path: {'YES' if db_path_exists else 'NO'}")
                print()

                if not db_path_exists and o81300_files:
                    # Database has wrong path, but we found the file
                    actual_file, actual_path, actual_size = o81300_files[0]
                    print(f"  [FIX NEEDED] Database path doesn't match actual file location")
                    print(f"    Database says: {db_file_path}")
                    print(f"    Actual file:   {actual_path}")
                    print()

                    # Update database with correct path
                    print("  Updating database with correct path...")
                    cursor.execute("""
                        UPDATE programs
                        SET file_path = ?
                        WHERE program_number = 'o81300'
                    """, (actual_path,))

                    conn.commit()
                    print(f"  [OK] Database updated!")
                    print(f"       New path: {actual_path}")

        else:
            print("[ERROR] No database record found for o81300")

        conn.close()

    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            print("[ERROR] Database is locked!")
            print("        Close the database manager and run this again.")
        else:
            print(f"[ERROR] {e}")

print()
print("=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

if o81300_files:
    file, path, size = o81300_files[0]
    print(f"[OK] o81300 file found: {file}")
    print(f"     Location: {path}")
    print(f"     Size: {size} bytes")
    print()
    print("If database was updated, restart the database manager.")
else:
    print("[ERROR] o81300 file not found in repository")
    print("        File may need to be restored from archive.")
