"""
Check actual format of file paths in database.
"""

import sqlite3

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING FILE PATH FORMATS IN DATABASE")
print("=" * 80)
print()

# Get sample paths
cursor.execute("""
    SELECT program_number, file_path
    FROM programs
    WHERE file_path IS NOT NULL
    ORDER BY program_number
    LIMIT 10
""")

paths = cursor.fetchall()

print("Sample of file paths in database:")
print()

for prog, path in paths:
    print(f"{prog}: {path}")

print()

# Check o81300 specifically
cursor.execute("""
    SELECT program_number, file_path
    FROM programs
    WHERE program_number = 'o81300'
""")

result = cursor.fetchone()

if result:
    prog, path = result
    print(f"o81300 current path: {path}")
    print()

    # Check different drive letter variations
    import os

    print("Checking if file exists at different paths:")
    test_paths = [
        path,
        path.replace('l:', 'L:'),
        path.replace('l:', 'I:'),
        path.replace('L:', 'l:'),
        path.replace('L:', 'I:'),
    ]

    for test_path in set(test_paths):
        exists = os.path.exists(test_path)
        print(f"  {test_path}")
        print(f"    Exists: {'YES' if exists else 'NO'}")

conn.close()

print()
print("=" * 80)
