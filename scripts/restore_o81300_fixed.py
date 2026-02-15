"""
Properly restore o81300 to repository, checking both drive letters.
"""

import sqlite3
import os
import shutil

# Try both drive letters
l_base = r"l:\My Drive\Home\File organizer"
i_base = r"I:\My Drive\Home\File organizer"

# Determine which drive is accessible
if os.path.exists(l_base):
    base_path = l_base
    drive_letter = "l:"
    print(f"[OK] Working with l: drive")
elif os.path.exists(i_base):
    base_path = i_base
    drive_letter = "I:"
    print(f"[OK] Working with I: drive")
else:
    print("[ERROR] Neither l: nor I: drive is accessible!")
    exit(1)

db_path = os.path.join(base_path, "gcode_database.db")
repository_path = os.path.join(base_path, "repository")
archive_path = os.path.join(base_path, "archive", "2026-02-08")

print("=" * 80)
print("RESTORING o81300 TO REPOSITORY")
print("=" * 80)
print(f"Using drive: {drive_letter}")
print()

# Find latest archive version
archive_files = []
for i in range(1, 10):  # Check versions 1-9
    archive_file = os.path.join(archive_path, f"o81300_{i}.nc")
    if os.path.exists(archive_file):
        archive_files.append((i, archive_file))

if not archive_files:
    print("[ERROR] No archive files found!")
    exit(1)

# Use the latest version
latest_version, latest_file = max(archive_files, key=lambda x: x[0])
target_file = os.path.join(repository_path, "o81300.nc")

print(f"Archive versions found: {len(archive_files)}")
print(f"Using latest version: o81300_{latest_version}.nc")
print(f"Source: {latest_file}")
print(f"Target: {target_file}")
print()

# Copy file to repository
try:
    shutil.copy2(latest_file, target_file)
    print(f"[OK] File copied to repository")

    # Verify it exists
    if os.path.exists(target_file):
        file_size = os.path.getsize(target_file)
        print(f"[OK] File verified: {file_size} bytes")

        # Update database with correct drive letter
        from datetime import datetime
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()

        # Build correct path with current drive letter
        correct_path = os.path.join(base_path, "repository", "o81300.nc")

        cursor.execute("""
            UPDATE programs
            SET file_path = ?,
                last_modified = ?
            WHERE program_number = 'o81300'
        """, (correct_path, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        print(f"[OK] Database updated with path: {correct_path}")
        print()
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print()
        print(f"o81300.nc restored to repository on {drive_letter} drive")
        print("You can now open it from the database manager.")
        print()

    else:
        print(f"[ERROR] Copy succeeded but verification failed!")

except Exception as e:
    print(f"[ERROR] Failed to restore file: {e}")
    import traceback
    traceback.print_exc()
