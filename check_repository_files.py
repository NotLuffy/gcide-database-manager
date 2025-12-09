"""
Check Repository Files - Diagnostic Script

This script scans your repository folder and shows:
1. All .nc files found
2. Database entries with missing file_path
3. Database entries where file doesn't exist

Run this to diagnose file path issues.
"""

import sqlite3
import os

# Database path
DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

# Get repository path from database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get repository path (use the one from the first managed file)
cursor.execute("""
    SELECT file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    LIMIT 1
""")
result = cursor.fetchone()

if not result:
    print("ERROR: No managed files found in database")
    conn.close()
    exit()

# Extract repository path from first file
repo_path = os.path.dirname(result[0])
print("=" * 80)
print("REPOSITORY PATH")
print("=" * 80)
print(f"{repo_path}\n")

# Scan repository for all .nc files
print("=" * 80)
print("SCANNING REPOSITORY FOR .NC FILES")
print("=" * 80)

nc_files = {}
if os.path.exists(repo_path):
    for filename in os.listdir(repo_path):
        if filename.lower().endswith('.nc'):
            full_path = os.path.join(repo_path, filename)
            base_name = os.path.splitext(filename)[0]
            nc_files[base_name.lower()] = (filename, full_path)

    print(f"Found {len(nc_files)} .nc files in repository\n")

    # Show first 20 files
    print("First 20 files:")
    for i, (base_name, (filename, full_path)) in enumerate(sorted(nc_files.items())[:20]):
        print(f"  {base_name:20} -> {filename}")

    if len(nc_files) > 20:
        print(f"  ... and {len(nc_files) - 20} more files")
else:
    print(f"ERROR: Repository path does not exist: {repo_path}")

print("\n" + "=" * 80)
print("PROGRAMS WITH SUFFIX IN DATABASE")
print("=" * 80)

# Get programs with suffixes
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE is_managed = 1
      AND (program_number LIKE '%(%' OR program_number LIKE '%_%')
    ORDER BY program_number
""")

suffix_programs = cursor.fetchall()
print(f"Found {len(suffix_programs)} programs with suffixes\n")

for prog_num, file_path, title in suffix_programs[:30]:
    print(f"Program: {prog_num}")
    print(f"  DB path: {file_path if file_path else '(NULL)'}")

    if file_path and os.path.exists(file_path):
        print(f"  Status: OK File exists")
    elif file_path:
        print(f"  Status: X File NOT found at DB path")

        # Try to find it
        import re
        base_prog = re.sub(r'[\(_]\d+[\)]?$', '', prog_num).lower()

        # Try variations
        variations = [
            prog_num.lower(),
            base_prog,
            prog_num.replace('(', '_').replace(')', '').lower(),
        ]

        found = False
        for var in variations:
            if var in nc_files:
                actual_filename, actual_path = nc_files[var]
                print(f"  Found as: {actual_filename}")
                found = True
                break

        if not found:
            print(f"  Result: XX NOT FOUND in repository")
    else:
        print(f"  Status: WARNING NULL file_path in database")

        # Try to find it
        import re
        base_prog = re.sub(r'[\(_]\d+[\)]?$', '', prog_num).lower()

        variations = [
            prog_num.lower(),
            base_prog,
            prog_num.replace('(', '_').replace(')', '').lower(),
        ]

        found = False
        for var in variations:
            if var in nc_files:
                actual_filename, actual_path = nc_files[var]
                print(f"  Found as: {actual_filename}")
                found = True
                break

        if not found:
            print(f"  Result: XX NOT FOUND in repository")

    print()

if len(suffix_programs) > 30:
    print(f"... and {len(suffix_programs) - 30} more programs with suffixes")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Count issues
cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE is_managed = 1 AND file_path IS NULL
""")
null_paths = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
""")
has_paths = cursor.fetchone()[0]

print(f"Programs with NULL file_path: {null_paths}")
print(f"Programs with file_path set: {has_paths}")
print(f"Files in repository folder: {len(nc_files)}")
print(f"Programs with suffixes: {len(suffix_programs)}")

conn.close()

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("1. Run 'Repair File Paths' button to fix database paths")
print("2. Then run 'Fix Program Number Format' to add leading zeros")
print("3. Then run 'Batch Rename Out-of-Range' to fix suffixes")
print("4. Finally run 'Sync Filenames' to ensure everything matches")
