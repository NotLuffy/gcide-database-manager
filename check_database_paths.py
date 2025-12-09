"""
Check exact database file paths
"""

import sqlite3
import os

DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check specific programs
test_programs = ['o10202', 'o10203', 'o08501_1', 'o00802']

print("Checking database paths:\n")

for prog in test_programs:
    cursor.execute("""
        SELECT program_number, file_path
        FROM programs
        WHERE program_number = ? AND is_managed = 1
    """, (prog,))

    result = cursor.fetchone()
    if result:
        prog_num, file_path = result
        exists = "EXISTS" if os.path.exists(file_path) else "MISSING"
        print(f"{prog_num}:")
        print(f"  Path: {file_path}")
        print(f"  File: {exists}")
        print()

# Check file extensions
print("\n" + "=" * 80)
print("File Extensions in Database")
print("=" * 80)

cursor.execute("""
    SELECT file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
""")

extensions = {}
for (path,) in cursor.fetchall():
    ext = os.path.splitext(path)[1].lower()
    if ext not in extensions:
        extensions[ext] = 0
    extensions[ext] += 1

for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
    print(f"{ext if ext else '(no extension)':15} : {count:5,} files")

conn.close()
