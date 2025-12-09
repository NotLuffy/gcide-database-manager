import sqlite3
import os
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get repository files
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE is_managed = 1
      AND file_path IS NOT NULL
    ORDER BY program_number
    LIMIT 100
""")

files = cursor.fetchall()

print("=" * 80)
print("CHECKING FILE STRUCTURE - First 5 lines of each file")
print("=" * 80)
print()

issues_found = []

for prog_num, file_path, title in files[:20]:
    if not os.path.exists(file_path):
        continue

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        if len(lines) < 3:
            continue

        # Check first 5 lines
        first_5 = ''.join(lines[:5])

        # Look for comment before O-number or title
        has_issue = False

        # Check if first line is a comment (starts with parenthesis)
        if lines[0].strip().startswith('('):
            # Check if it's a legacy comment (MOVED FROM, UPDATED FROM, etc.)
            if any(keyword in lines[0].upper() for keyword in ['MOVED FROM', 'UPDATED FROM', 'RANGE CORRECTION', 'INTERNAL O-NUMBER']):
                has_issue = True
                issues_found.append((prog_num, file_path, lines[0].strip()))

        # Check if second line is a comment and first line is O-number
        if len(lines) > 1:
            if re.match(r'^[oO]\d+', lines[0].strip()) and lines[1].strip().startswith('('):
                if any(keyword in lines[1].upper() for keyword in ['MOVED FROM', 'UPDATED FROM', 'RANGE CORRECTION', 'INTERNAL O-NUMBER']):
                    # This is OK only if line 2 is the legacy comment and line 3+ is the title
                    if len(lines) > 2 and lines[2].strip().startswith('(') and not any(keyword in lines[2].upper() for keyword in ['MOVED FROM', 'UPDATED FROM', 'RANGE CORRECTION', 'INTERNAL O-NUMBER']):
                        # Title is on line 3, legacy comment is on line 2 - this is WRONG
                        has_issue = True
                        issues_found.append((prog_num, file_path, f"Line 1: {lines[0].strip()}, Line 2: {lines[1].strip()}, Line 3: {lines[2].strip()}"))

        if has_issue:
            print(f"\n{prog_num} - ISSUE FOUND")
            print(f"File: {file_path}")
            print("First 5 lines:")
            for i, line in enumerate(lines[:5], 1):
                print(f"  {i}: {line.rstrip()}")

    except Exception as e:
        print(f"Error reading {prog_num}: {e}")

print()
print("=" * 80)
print(f"SUMMARY: Found {len(issues_found)} files with comments before title")
print("=" * 80)

conn.close()
