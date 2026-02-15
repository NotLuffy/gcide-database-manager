"""
Fix o81300 extension mismatch - rename .txt to .nc and update database.
"""

import sqlite3
import os
import shutil

# Use uppercase L: with forward slashes (standard format in database)
repository_path = "L:/My Drive/Home/File organizer/repository"
db_path = "L:/My Drive/Home/File organizer/gcode_database.db"

txt_file = os.path.join(repository_path, "o81300.txt")
nc_file = os.path.join(repository_path, "o81300.nc")

print("=" * 80)
print("FIXING o81300 FILE EXTENSION")
print("=" * 80)
print()

# Check if .txt file exists
if os.path.exists(txt_file):
    print(f"[FOUND] {txt_file}")
    file_size = os.path.getsize(txt_file)
    print(f"        Size: {file_size} bytes")
    print()

    # Rename to .nc
    try:
        shutil.move(txt_file, nc_file)
        print(f"[OK] Renamed to: {nc_file}")

        # Update database with correct path (using L:/ format)
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()

        # Use forward slashes like other records
        correct_path = "L:/My Drive/Home/File organizer/repository/o81300.nc"

        cursor.execute("""
            UPDATE programs
            SET file_path = ?
            WHERE program_number = 'o81300'
        """, (correct_path,))

        conn.commit()
        conn.close()

        print(f"[OK] Database updated with: {correct_path}")
        print()
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print()
        print("o81300.nc is now properly named and database updated.")
        print("Try opening it from the database manager again.")
        print()

    except Exception as e:
        print(f"[ERROR] Failed to rename file: {e}")

else:
    print(f"[ERROR] File not found: {txt_file}")
    print()
    print("Checking what files actually exist:")
    for file in os.listdir(repository_path):
        if '81300' in file:
            print(f"  Found: {file}")

print("=" * 80)
