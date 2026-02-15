"""
Update all database paths from I: drive to l: drive (or vice versa).
"""

import sqlite3
import os

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("FIXING DRIVE LETTER MISMATCHES IN DATABASE")
print("=" * 80)
print()

# Check what drive letters are in the database
cursor.execute("""
    SELECT file_path
    FROM programs
    WHERE file_path IS NOT NULL
    LIMIT 100
""")

sample_paths = cursor.fetchall()

i_drive_count = sum(1 for (path,) in sample_paths if path and path.startswith('I:'))
l_drive_count = sum(1 for (path,) in sample_paths if path and path.startswith('l:'))

print(f"Sample of 100 file paths:")
print(f"  I: drive paths: {i_drive_count}")
print(f"  l: drive paths: {l_drive_count}")
print()

if i_drive_count > 0:
    print(f"[ISSUE] Database has {i_drive_count} paths using I: drive")
    print("        But I: drive is not accessible from current session")
    print()
    print("FIX: Convert all I: paths to l: paths")
    print()

    # Show some examples
    print("Example paths that will be updated:")
    for (path,) in sample_paths[:5]:
        if path and path.startswith('I:'):
            new_path = path.replace('I:', 'l:', 1)
            print(f"  {path}")
            print(f"    -> {new_path}")

    print()
    response = input("Update all I: drive paths to l: drive? (yes/no): ").strip().lower()

    if response == 'yes':
        # Update all paths
        cursor.execute("""
            UPDATE programs
            SET file_path = REPLACE(file_path, 'I:', 'l:')
            WHERE file_path LIKE 'I:%'
        """)

        updated_count = cursor.rowcount
        conn.commit()

        print(f"[OK] Updated {updated_count} file paths from I: to l: drive")
        print()
        print("The database manager should now find files correctly.")

elif l_drive_count > 0:
    print("[OK] Database already uses l: drive paths")
    print("     This is correct for the current session.")

else:
    print("[INFO] No I: or l: drive paths found in sample")

conn.close()

print()
print("=" * 80)
