"""
Check File Locations

Where are the database files actually located?
"""

import sqlite3
import os

DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING FILE LOCATIONS")
print("=" * 80)

# Get repository path from first managed file
cursor.execute("""
    SELECT file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    LIMIT 1
""")
result = cursor.fetchone()
repo_path = os.path.dirname(result[0])

print(f"\nRepository folder: {repo_path}\n")

# Get all managed programs
cursor.execute("""
    SELECT program_number, file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    ORDER BY program_number
""")

all_programs = cursor.fetchall()

# Count by location
in_repository = 0
outside_repository = 0
locations = {}

for prog_num, file_path in all_programs:
    if not file_path:
        continue

    file_dir = os.path.dirname(file_path)

    if file_dir.lower() == repo_path.lower():
        in_repository += 1
    else:
        outside_repository += 1
        if file_dir not in locations:
            locations[file_dir] = 0
        locations[file_dir] += 1

print("=" * 80)
print("RESULTS")
print("=" * 80)

print(f"\nTotal database entries: {len(all_programs):,}")
print(f"Files in repository folder: {in_repository:,}")
print(f"Files OUTSIDE repository: {outside_repository:,}\n")

if outside_repository > 0:
    print("=" * 80)
    print("FILES OUTSIDE REPOSITORY")
    print("=" * 80)
    print()

    for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"{count:5,} files in: {location}")

    print()

# Show some examples
if outside_repository > 0:
    print("=" * 80)
    print("EXAMPLES (First 20)")
    print("=" * 80)
    print()

    cursor.execute("""
        SELECT program_number, file_path
        FROM programs
        WHERE is_managed = 1
          AND file_path IS NOT NULL
        ORDER BY program_number
        LIMIT 8210
    """)

    shown = 0
    for prog_num, file_path in cursor.fetchall():
        file_dir = os.path.dirname(file_path)
        if file_dir.lower() != repo_path.lower():
            print(f"{prog_num}: {file_path}")
            shown += 1
            if shown >= 20:
                break

print("\n" + "=" * 80)
print("EXPLANATION")
print("=" * 80)
print(f"""
The database has {len(all_programs):,} entries marked as is_managed=1
These files are located:
  - In repository: {in_repository:,}
  - Outside repository: {outside_repository:,}

If you have {outside_repository:,} files outside the repository, these are likely:
1. Files scanned but not yet copied to repository
2. Files from the source folder (I:/My Drive/NC Master/REVISED PROGRAMS/5.75/)
3. Files that should be moved to repository

RECOMMENDATION:
- Files marked as is_managed=1 should be IN the repository folder
- Run "Add to Repository" to copy these files to the repository
- Or set is_managed=0 for files you don't want to manage
""")

conn.close()
