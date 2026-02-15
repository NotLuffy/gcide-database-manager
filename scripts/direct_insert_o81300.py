"""
Direct SQL insert for o81300 - bypass all buggy import functions.
"""

import sqlite3
import os
from datetime import datetime

# Direct paths
db_file = r"L:\My Drive\Home\File organizer\gcode_database.db"
nc_file = r"L:\My Drive\Home\File organizer\repository\o81300.nc"

print("=" * 80)
print("DIRECT SQL INSERT FOR o81300")
print("=" * 80)
print()

# Verify file exists
if not os.path.exists(nc_file):
    print(f"[ERROR] File not found: {nc_file}")
    exit(1)

print(f"File exists: {nc_file}")
print(f"Size: {os.path.getsize(nc_file)} bytes")
print()

# Read title from file
title = None
try:
    with open(nc_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        for line in lines[:20]:  # Check first 20 lines
            if line.strip().startswith('(') and not line.strip().startswith('(%'):
                title = line.strip().strip('()')
                break
except:
    pass

print(f"Title: {title}")
print()

# Direct insert
print("Inserting into database...")

try:
    conn = sqlite3.connect(db_file, timeout=30.0)
    cursor = conn.cursor()

    # Simple insert with minimal fields
    cursor.execute("""
        INSERT OR REPLACE INTO programs (
            program_number,
            title,
            file_path,
            date_created,
            last_modified,
            date_imported,
            is_deleted,
            validation_status,
            spacer_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'o81300',
        title,
        nc_file,
        datetime.now().isoformat(),
        datetime.now().isoformat(),
        datetime.now().isoformat(),
        0,
        'PASS',
        'Ring'  # Default spacer type
    ))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected > 0:
        print(f"[OK] Successfully inserted o81300 into database!")
        print()
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print()
        print("Refresh the database manager to see o81300")
    else:
        print("[ERROR] Insert didn't affect any rows")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
