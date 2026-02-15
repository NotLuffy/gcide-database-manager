"""
Check for drive letter mismatch in o81300 database record.
"""

import sqlite3
import os

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING DRIVE LETTER MISMATCH FOR o81300")
print("=" * 80)
print()

# Get database record
cursor.execute("""
    SELECT program_number, file_path
    FROM programs
    WHERE program_number = 'o81300'
""")

record = cursor.fetchone()

if record:
    prog_num, db_path_val = record
    print(f"Database record for {prog_num}:")
    print(f"  Path in database: {db_path_val}")
    print()

    # Check what drive letters exist
    print("Checking actual file locations:")

    # Check l: drive
    l_path = r"l:\My Drive\Home\File organizer\repository\o81300.nc"
    l_exists = os.path.exists(l_path)
    print(f"  l: drive: {l_path}")
    print(f"    Exists: {'YES' if l_exists else 'NO'}")

    # Check I: drive (from error message)
    i_path = r"I:\My Drive\Home\File organizer\repository\o81300.nc"
    i_exists = os.path.exists(i_path)
    print(f"  I: drive: {i_path}")
    print(f"    Exists: {'YES' if i_exists else 'NO'}")

    print()

    # Determine the fix
    if db_path_val and db_path_val.startswith('I:') and l_exists and not i_exists:
        print("[ISSUE] Database has I: drive but file is on l: drive")
        print()
        print("FIX: Update database to use l: drive")
        print()

        response = input("Update database path to l: drive? (yes/no): ").strip().lower()
        if response == 'yes':
            new_path = db_path_val.replace('I:', 'l:')
            cursor.execute("""
                UPDATE programs
                SET file_path = ?
                WHERE program_number = ?
            """, (new_path, prog_num))
            conn.commit()
            print(f"[OK] Updated database path to: {new_path}")

    elif db_path_val and db_path_val.startswith('l:') and i_exists and not l_exists:
        print("[ISSUE] Database has l: drive but file is on I: drive")
        print()
        print("FIX: Update database to use I: drive")
        print()

        response = input("Update database path to I: drive? (yes/no): ").strip().lower()
        if response == 'yes':
            new_path = db_path_val.replace('l:', 'I:')
            cursor.execute("""
                UPDATE programs
                SET file_path = ?
                WHERE program_number = ?
            """, (new_path, prog_num))
            conn.commit()
            print(f"[OK] Updated database path to: {new_path}")

    elif l_exists and i_exists:
        print("[INFO] File exists on BOTH drives (I: and l:)")
        print("These are likely the same Google Drive mapped to different letters.")

    else:
        print("[ERROR] File not found on either drive!")

else:
    print("[ERROR] No database record found for o81300")

conn.close()

print()
print("=" * 80)
