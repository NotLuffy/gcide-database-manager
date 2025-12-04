import sqlite3
import os
import re
from datetime import datetime

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
print(f"SCANNING {len(files)} FILES FOR MISPLACED COMMENTS")
print("=" * 80)
print()

legacy_keywords = ['MOVED FROM', 'UPDATED FROM', 'RANGE CORRECTION', 'INTERNAL O-NUMBER', 'RENAMED FROM']

needs_fix = []

for prog_num, file_path, db_title in files:
    if not os.path.exists(file_path):
        continue

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        if len(lines) < 3:
            continue

        # Find the O-number line and title line
        onumber_line_idx = None
        title_line_idx = None
        legacy_comments_before_title = []

        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            stripped = line.strip()

            # Find O-number line (may have title on same line or not)
            if re.match(r'^[oO]\d+', stripped):
                onumber_line_idx = i
                # Check if title is on same line
                if '(' in stripped and ')' in stripped:
                    # O-number with title on same line
                    title_line_idx = i
                break

        if onumber_line_idx is None:
            continue

        # Check lines BEFORE O-number for legacy comments
        for i in range(onumber_line_idx):
            stripped = lines[i].strip()
            if any(keyword in stripped.upper() for keyword in legacy_keywords):
                legacy_comments_before_title.append((i, lines[i]))

        if legacy_comments_before_title:
            needs_fix.append({
                'prog_num': prog_num,
                'file_path': file_path,
                'onumber_line': onumber_line_idx,
                'legacy_comments': legacy_comments_before_title,
                'all_lines': lines
            })

    except Exception as e:
        print(f"Error reading {prog_num}: {e}")

print(f"Found {len(needs_fix)} files with legacy comments before O-number/title\n")

if not needs_fix:
    print("No files need fixing!")
    conn.close()
    exit()

print("=" * 80)
print(f"PREVIEW - First 10 files that will be fixed")
print("=" * 80)

for item in needs_fix[:10]:
    print(f"\n{item['prog_num']}")
    print(f"  File: {os.path.basename(item['file_path'])}")
    print(f"  O-number on line {item['onumber_line'] + 1}")
    print(f"  Legacy comments to move:")
    for idx, comment in item['legacy_comments']:
        print(f"    Line {idx + 1}: {comment.strip()[:70]}")

print()
print("=" * 80)
print(f"READY TO FIX {len(needs_fix)} FILES")
print("=" * 80)

response = input("\nProceed with fixing? (yes/no): ")

if response.lower() != 'yes':
    print("Cancelled.")
    conn.close()
    exit()

print("\n" + "=" * 80)
print("FIXING FILES...")
print("=" * 80 + "\n")

fixed_count = 0
error_count = 0

for item in needs_fix:
    try:
        prog_num = item['prog_num']
        file_path = item['file_path']
        onumber_line_idx = item['onumber_line']
        legacy_comments = item['legacy_comments']
        all_lines = item['all_lines']

        # Build new file content
        new_lines = []

        # Step 1: Add all lines BEFORE O-number, EXCEPT legacy comments
        legacy_indices = [idx for idx, _ in legacy_comments]
        for i in range(onumber_line_idx):
            if i not in legacy_indices:
                new_lines.append(all_lines[i])

        # Step 2: Add O-number line (with or without title)
        new_lines.append(all_lines[onumber_line_idx])

        # Step 3: Add legacy comments (moved here, after O-number/title)
        for _, comment in legacy_comments:
            new_lines.append(comment)

        # Step 4: Add all remaining lines after O-number
        for i in range(onumber_line_idx + 1, len(all_lines)):
            new_lines.append(all_lines[i])

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        fixed_count += 1
        print(f"[OK] Fixed {prog_num}")

        if fixed_count % 50 == 0:
            print(f"  ... {fixed_count} files fixed so far")

    except Exception as e:
        error_count += 1
        print(f"[ERROR] Error fixing {prog_num}: {e}")

print()
print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"Successfully fixed: {fixed_count} files")
if error_count > 0:
    print(f"Errors: {error_count}")

conn.close()
