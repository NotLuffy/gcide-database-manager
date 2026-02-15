"""
Restore o81300 from archive to repository (final fix).
"""

import sqlite3
import os
import shutil
from datetime import datetime

base_path = r"L:\My Drive\Home\File organizer"
archive_path = os.path.join(base_path, "archive", "2026-02-08")
repository_path = os.path.join(base_path, "repository")
db_path = os.path.join(base_path, "gcode_database.db")

print("=" * 80)
print("RESTORING o81300 FROM ARCHIVE (FINAL FIX)")
print("=" * 80)
print()

# Find latest archive version
versions = []
for i in range(1, 10):
    archive_file = os.path.join(archive_path, f"o81300_{i}.nc")
    if os.path.exists(archive_file):
        versions.append((i, archive_file))

if not versions:
    print("[ERROR] No archive versions found!")
    exit(1)

# Use latest version
latest_num, latest_file = max(versions, key=lambda x: x[0])
target_file = os.path.join(repository_path, "o81300.nc")

print(f"Found {len(versions)} archive versions")
print(f"Using latest: o81300_{latest_num}.nc")
print()
print(f"Source: {latest_file}")
print(f"Target: {target_file}")
print()

# Copy file to repository
try:
    shutil.copy2(latest_file, target_file)

    # Verify it exists
    if os.path.exists(target_file):
        size = os.path.getsize(target_file)
        print(f"[OK] File restored to repository")
        print(f"     Size: {size} bytes")
        print()

        # Update database - use the path format that matches other files
        # Most files use L:/ with forward slashes
        correct_path = "L:/My Drive/Home/File organizer/repository/o81300.nc"

        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE programs
            SET file_path = ?,
                last_modified = ?
            WHERE program_number = 'o81300'
        """, (correct_path, datetime.now().isoformat()))

        updated = cursor.rowcount
        conn.commit()
        conn.close()

        if updated > 0:
            print(f"[OK] Database updated")
            print(f"     Path: {correct_path}")
        else:
            print(f"[WARNING] Database record not found for o81300")

        print()
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print()
        print("o81300.nc has been restored to the repository.")
        print()
        print("NEXT STEP: Restart the database manager to see the changes.")
        print()

    else:
        print("[ERROR] File copy succeeded but verification failed")

except sqlite3.OperationalError as e:
    if "locked" in str(e).lower():
        print("[ERROR] Database is locked!")
        print()
        print("The file has been restored to the repository,")
        print("but I couldn't update the database.")
        print()
        print("SOLUTION:")
        print("  1. Close the database manager")
        print("  2. Run this script again")
        print("  3. Reopen the database manager")
    else:
        print(f"[ERROR] {e}")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
