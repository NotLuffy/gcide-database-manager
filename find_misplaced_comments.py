import sqlite3
import os
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get ALL repository files
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE is_managed = 1
      AND file_path IS NOT NULL
    ORDER BY program_number
""")

files = cursor.fetchall()

print("=" * 80)
print(f"SCANNING {len(files)} REPOSITORY FILES FOR MISPLACED COMMENTS")
print("=" * 80)
print()

issues_found = []

# Correct structure should be:
# Line 1: O12345
# Line 2: (TITLE TEXT)
# Line 3+: (MOVED FROM... / UPDATED FROM... / other comments)
# Line 4+: G-code

for prog_num, file_path, db_title in files:
    if not os.path.exists(file_path):
        continue

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        if len(lines) < 2:
            continue

        # Check structure
        line1 = lines[0].strip()
        line2 = lines[1].strip() if len(lines) > 1 else ""
        line3 = lines[2].strip() if len(lines) > 2 else ""

        # Expected: Line 1 = O-number, Line 2 = Title (comment), Line 3+ = other comments/gcode
        has_onumber_line1 = re.match(r'^[oO]\d+', line1)

        if not has_onumber_line1:
            # Line 1 should be O-number
            issues_found.append({
                'prog_num': prog_num,
                'file_path': file_path,
                'issue': 'NO_ONUMBER_LINE1',
                'line1': line1,
                'line2': line2,
                'line3': line3
            })
            continue

        # Check if line 2 is a legacy comment instead of title
        legacy_keywords = ['MOVED FROM', 'UPDATED FROM', 'RANGE CORRECTION', 'INTERNAL O-NUMBER']

        if any(keyword in line2.upper() for keyword in legacy_keywords):
            # Line 2 is legacy comment - title should be elsewhere or missing
            issues_found.append({
                'prog_num': prog_num,
                'file_path': file_path,
                'issue': 'LEGACY_COMMENT_LINE2',
                'line1': line1,
                'line2': line2,
                'line3': line3
            })

    except Exception as e:
        print(f"Error reading {prog_num}: {e}")

print(f"Found {len(issues_found)} files with potential issues\n")

if issues_found:
    print("=" * 80)
    print("FILES WITH MISPLACED COMMENTS (First 20)")
    print("=" * 80)

    for item in issues_found[:20]:
        print(f"\n{item['prog_num']} - {item['issue']}")
        print(f"  File: {os.path.basename(item['file_path'])}")
        print(f"  Line 1: {item['line1'][:80]}")
        print(f"  Line 2: {item['line2'][:80]}")
        print(f"  Line 3: {item['line3'][:80]}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

# Count by issue type
no_onumber = sum(1 for x in issues_found if x['issue'] == 'NO_ONUMBER_LINE1')
legacy_line2 = sum(1 for x in issues_found if x['issue'] == 'LEGACY_COMMENT_LINE2')

print(f"Total files with issues: {len(issues_found)}")
print(f"  - No O-number on line 1: {no_onumber}")
print(f"  - Legacy comment on line 2 (title missing/displaced): {legacy_line2}")

conn.close()
