"""
Check o81300 record in database to diagnose the file not found issue.
"""

import sqlite3
import os
from pathlib import Path

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
repository_path = r"l:\My Drive\Home\File organizer\repository"

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("DIAGNOSING o81300 FILE NOT FOUND ISSUE")
print("=" * 80)
print()

# Check database record
cursor.execute("""
    SELECT program_number, file_path, is_deleted, deleted_date, last_modified
    FROM programs
    WHERE program_number = 'o81300'
""")

record = cursor.fetchone()

if not record:
    print("[ERROR] o81300 not found in database!")
    print()
    print("The file might be:")
    print("  1. Not yet imported into database")
    print("  2. Using a different program number")
    print()
    print("Searching for files with '81300' in repository...")

    for file in Path(repository_path).glob("*81300*"):
        print(f"  Found: {file.name}")

else:
    prog_num, file_path, is_deleted, deleted_date, last_modified = record

    print(f"Database Record for {prog_num}:")
    print(f"  File Path: {file_path}")
    print(f"  Is Deleted: {is_deleted}")
    print(f"  Deleted Date: {deleted_date}")
    print(f"  Last Modified: {last_modified}")
    print()

    # Check if file exists
    if file_path:
        file_exists = os.path.exists(file_path)
        print(f"File Exists at Path: {'YES' if file_exists else 'NO'}")

        if not file_exists:
            print()
            print("[ISSUE] Database has file path but file doesn't exist!")
            print()
            print("Possible causes:")
            print("  1. File was moved/renamed after database entry")
            print("  2. File path uses wrong drive letter or directory")
            print("  3. File was deleted but record not updated")
            print()

            # Search for the file in repository
            print("Searching repository for o81300 files...")
            matches = list(Path(repository_path).glob("*81300*"))

            if matches:
                print(f"\nFound {len(matches)} matching file(s) in repository:")
                for match in matches:
                    full_path = str(match)
                    print(f"  - {match.name}")
                    print(f"    Full path: {full_path}")

                    # Check if this is a different path than database
                    if full_path != file_path:
                        print(f"    [FIX NEEDED] This is a different path!")
                        print(f"    Database has: {file_path}")
                        print(f"    Actual file:  {full_path}")
                        print()
                        print("SOLUTION: Update database record with correct path")

                        # Offer to fix it
                        response = input("\nUpdate database with correct path? (yes/no): ").strip().lower()
                        if response == 'yes':
                            cursor.execute("""
                                UPDATE programs
                                SET file_path = ?
                                WHERE program_number = ?
                            """, (full_path, prog_num))
                            conn.commit()
                            print(f"[OK] Updated database record for {prog_num}")
                            print(f"     New path: {full_path}")
            else:
                print("\n[ERROR] No matching files found in repository!")
                print("The file may have been deleted or is in a different location.")
        else:
            print()
            print("[OK] File exists at the specified path")
            print("The database record is correct.")
    else:
        print()
        print("[ERROR] Database record has no file_path!")
        print("This record is incomplete.")

conn.close()

print()
print("=" * 80)
