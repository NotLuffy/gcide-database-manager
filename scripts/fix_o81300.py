"""
Fix o81300 by restoring it from archive to repository.
"""

import sqlite3
import os
import shutil

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
repository_path = r"l:\My Drive\Home\File organizer\repository"
archive_file = r"l:\My Drive\Home\File organizer\archive\2026-02-08\o81300_1.nc"
target_file = os.path.join(repository_path, "o81300.nc")

print("=" * 80)
print("RESTORING o81300 FROM ARCHIVE")
print("=" * 80)
print()

# Check if archive file exists
if not os.path.exists(archive_file):
    print(f"[ERROR] Archive file not found: {archive_file}")
    exit(1)

print(f"Source (archive): {archive_file}")
print(f"Target (repository): {target_file}")
print()

# Copy file from archive to repository
try:
    shutil.copy2(archive_file, target_file)
    print(f"[OK] File restored to repository")

    # Verify it exists
    if os.path.exists(target_file):
        file_size = os.path.getsize(target_file)
        print(f"[OK] File verified: {file_size} bytes")

        # Update database last_modified timestamp
        from datetime import datetime
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE programs
            SET last_modified = ?
            WHERE program_number = 'o81300'
        """, (datetime.now().isoformat(),))

        conn.commit()
        conn.close()

        print(f"[OK] Database record updated")
        print()
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print()
        print("o81300.nc has been restored to the repository.")
        print("You can now open it from the database manager.")
        print()
    else:
        print(f"[ERROR] Copy succeeded but file verification failed")

except Exception as e:
    print(f"[ERROR] Failed to restore file: {e}")
    import traceback
    traceback.print_exc()
