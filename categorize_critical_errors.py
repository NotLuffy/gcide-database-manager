import sqlite3
import json

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("CRITICAL ERROR CATEGORIZATION")
print("=" * 80)
print()

cursor.execute("""
    SELECT program_number, validation_issues
    FROM programs
    WHERE validation_status = 'CRITICAL'
      AND validation_issues IS NOT NULL
""")

results = cursor.fetchall()

error_categories = {
    'FILENAME MISMATCH': [],
    'THICKNESS ERROR': [],
    'CB TOO SMALL': [],
    'CB TOO LARGE': [],
    'OB TOO SMALL': [],
    'OB TOO LARGE': [],
    'OTHER': []
}

for prog_num, issues_str in results:
    # Try parsing as JSON first
    try:
        issues_list = json.loads(issues_str)
        issues_text = ' | '.join(issues_list)
    except:
        # Plain string
        issues_text = issues_str if issues_str else ''

    # Categorize by keyword
    categorized = False
    for category in error_categories.keys():
        if category in issues_text:
            error_categories[category].append(prog_num)
            categorized = True
            break

    if not categorized and issues_text:
        error_categories['OTHER'].append(prog_num)

print(f"{'Error Category':<30} {'Count':>8}")
print("-" * 40)

total = 0
for category, prog_nums in sorted(error_categories.items(), key=lambda x: -len(x[1])):
    count = len(prog_nums)
    if count > 0:
        total += count
        print(f"{category:<30} {count:>8}")

print("-" * 40)
print(f"{'TOTAL CRITICAL ERRORS':<30} {total:>8}")

# Sample errors from each category
print()
print("=" * 80)
print("SAMPLE ERRORS BY CATEGORY")
print("=" * 80)

for category, prog_nums in error_categories.items():
    if len(prog_nums) > 0:
        print()
        print(f"{category} ({len(prog_nums)} files):")
        print("-" * 80)

        # Get sample details
        sample_size = min(3, len(prog_nums))
        cursor.execute(f"""
            SELECT program_number, title, validation_issues
            FROM programs
            WHERE program_number IN ({','.join('?' * sample_size)})
        """, prog_nums[:sample_size])

        samples = cursor.fetchall()
        for prog_num, title, issues in samples:
            # Parse issues
            try:
                issues_list = json.loads(issues)
                issue_text = issues_list[0] if issues_list else issues
            except:
                issue_text = issues

            print(f"  {prog_num}: {issue_text[:90]}")

        if len(prog_nums) > 3:
            print(f"  ... and {len(prog_nums) - 3} more files")

conn.close()

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total CRITICAL errors: {total}")
print()
print("After today's fixes:")
print("  - 622 FILENAME MISMATCH false positives cleared")
print("  - Validation messages improved for clarity")
print("  - 324 files now have thickness (may reduce errors)")
