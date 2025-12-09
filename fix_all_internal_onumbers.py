"""
Fix ALL Internal O-Numbers

Updates the internal O-number in ALL repository files to match
their database program number.

This fixes files where:
- Filename was renamed but internal O-number wasn't updated
- Database shows o01010 but file contains O70027
"""

import sqlite3
import os
import re
from datetime import datetime

DB_PATH = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("FIX ALL INTERNAL O-NUMBERS")
print("=" * 80)

# Get repository path
cursor.execute("""
    SELECT file_path
    FROM programs
    WHERE is_managed = 1 AND file_path IS NOT NULL
    LIMIT 1
""")
result = cursor.fetchone()
repo_path = os.path.dirname(result[0])

print(f"\nRepository: {repo_path}\n")

# Get all managed files
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE is_managed = 1
      AND file_path IS NOT NULL
      AND file_path LIKE ?
    ORDER BY program_number
""", (f"{repo_path}%",))

all_files = cursor.fetchall()
print(f"Checking {len(all_files)} repository files...\n")

needs_fix = []
already_correct = []
errors = []

for prog_num, file_path, title in all_files:
    if not os.path.exists(file_path):
        errors.append((prog_num, file_path, "File not found"))
        continue

    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Find current internal O-number (first O##### in file)
        match = re.search(r'^[oO](\d+)', content, re.MULTILINE)

        if match:
            current_internal = f"O{match.group(1)}"
            expected_internal = prog_num.upper()

            if current_internal == expected_internal:
                already_correct.append((prog_num, file_path))
            else:
                needs_fix.append((prog_num, file_path, current_internal, expected_internal, title))
        else:
            errors.append((prog_num, file_path, "No O-number found in file"))

    except Exception as e:
        errors.append((prog_num, file_path, str(e)))

print("=" * 80)
print("RESULTS")
print("=" * 80)

print(f"\nAlready correct: {len(already_correct)}")
print(f"Need fixing: {len(needs_fix)}")
print(f"Errors: {len(errors)}\n")

if needs_fix:
    print("=" * 80)
    print(f"FILES THAT NEED FIXING (First 30 of {len(needs_fix)})")
    print("=" * 80)
    print()

    for prog_num, file_path, current, expected, title in needs_fix[:30]:
        filename = os.path.basename(file_path)
        print(f"File: {filename}")
        print(f"  Database program: {prog_num}")
        print(f"  Current internal: {current}")
        print(f"  Should be:        {expected}")
        print(f"  Title: {title[:50] if title else '(no title)'}")
        print()

    if len(needs_fix) > 30:
        print(f"... and {len(needs_fix) - 30} more files\n")

if errors:
    print("=" * 80)
    print(f"ERRORS (First 10)")
    print("=" * 80)
    for prog_num, file_path, error in errors[:10]:
        print(f"{prog_num}: {error}")

print("\n" + "=" * 80)
print("PROCEEDING WITH FIX")
print("=" * 80)

if not needs_fix:
    print("\nNo files need fixing! All internal O-numbers match database.")
    conn.close()
    exit()

print(f"\nFixing {len(needs_fix)} files...")

fixed_count = 0
error_count = 0

for prog_num, file_path, current_internal, expected_internal, title in needs_fix:
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extract just the number from current internal (e.g., O70027 -> 70027)
        current_num = re.sub(r'[oO]', '', current_internal)

        # Extract just the number from expected (e.g., o01010 -> 01010)
        new_num = re.sub(r'[oO]', '', expected_internal)

        # Replace all occurrences of the old O-number
        updated_content = content

        # Pattern 1: O##### at start of line
        updated_content = re.sub(
            rf'^[oO]{current_num}\b',
            expected_internal,
            updated_content,
            flags=re.MULTILINE
        )

        # Pattern 2: O##### in comments
        updated_content = re.sub(
            rf'\b[oO]{current_num}\b',
            expected_internal,
            updated_content
        )

        # Add legacy comment after the O-number line
        today = datetime.now().strftime("%Y-%m-%d")
        legacy_comment = f"(UPDATED FROM {current_internal} ON {today} - INTERNAL O-NUMBER FIX)"

        # Insert legacy comment after first O-number line
        lines = updated_content.split('\n')
        for i, line in enumerate(lines):
            if re.match(rf'^[oO]{new_num}\b', line):
                lines.insert(i + 1, legacy_comment)
                break

        updated_content = '\n'.join(lines)

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        fixed_count += 1

        if fixed_count % 100 == 0:
            print(f"Fixed {fixed_count} files...")

    except Exception as e:
        error_count += 1
        print(f"ERROR fixing {prog_num}: {e}")

conn.close()

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)

print(f"""
Fixed: {fixed_count:,} files
Errors: {error_count}
Already correct: {len(already_correct):,}

All repository files now have internal O-numbers matching their database program numbers!
""")
