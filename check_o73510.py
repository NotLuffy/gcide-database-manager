import sqlite3
import os
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING o73510 FILENAME MISMATCH WARNING")
print("=" * 80)
print()

# Get o73510 details
cursor.execute("""
    SELECT program_number, title, file_path, validation_status, validation_issues
    FROM programs
    WHERE program_number = 'o73510'
""")

result = cursor.fetchone()

if result:
    prog_num, title, file_path, validation_status, validation_issues = result

    print(f"Program Number (DB): {prog_num}")
    print(f"Title: {title}")
    print(f"File Path: {file_path}")
    print(f"Validation Status: {validation_status}")
    print(f"Validation Issues: {validation_issues}")
    print()

    if file_path and os.path.exists(file_path):
        # Extract filename
        filename = os.path.basename(file_path)
        print(f"Filename: {filename}")

        # Extract O-number from filename
        filename_match = re.search(r'[oO](\d+)', filename)
        if filename_match:
            filename_onumber = 'o' + filename_match.group(1)
            print(f"O-number from filename: {filename_onumber}")

        # Read internal O-number from file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        internal_onumber = None
        for i, line in enumerate(lines[:10]):
            stripped = line.strip()
            # Match O##### at start of line
            internal_match = re.match(r'^[oO](\d+)', stripped)
            if internal_match:
                internal_onumber = 'o' + internal_match.group(1)
                print(f"Internal O-number (line {i+1}): {internal_onumber}")
                print(f"  Full line: {stripped[:80]}")
                break

        print()
        print("ANALYSIS:")
        print("-" * 80)

        if filename_onumber and internal_onumber:
            if filename_onumber == internal_onumber:
                print(f"[OK] MATCH: Filename {filename_onumber} == Internal {internal_onumber}")
                print(f"  FALSE POSITIVE WARNING - Should NOT show as critical!")
            else:
                print(f"[ERROR] MISMATCH: Filename {filename_onumber} != Internal {internal_onumber}")
                print(f"  WARNING IS CORRECT")

        print()
        print("Database says:")
        print(f"  Validation Status: {validation_status}")
        if validation_issues:
            import json
            try:
                issues = json.loads(validation_issues)
                for issue in issues:
                    print(f"  - {issue}")
            except:
                print(f"  - {validation_issues}")
    else:
        print(f"File not found: {file_path}")
else:
    print("o73510 not found in database")

conn.close()
