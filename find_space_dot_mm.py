import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("FINDING FILES WITH ' .##MM' PATTERN (space before decimal)")
print("=" * 80)
print()

# Find all files
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display
    FROM programs
    WHERE title IS NOT NULL
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Checking {len(results)} files for ' .##MM' pattern...\n")

# Find files with space + decimal + digits + MM pattern
space_dot_mm_files = []

for prog_num, title, thickness, thickness_display in results:
    # Pattern: space followed by .## followed by MM
    # Example: " .75MM", " .5MM", " .25MM"
    pattern_match = re.search(r'\s+\.(\d+)\s*MM', title, re.IGNORECASE)

    if pattern_match:
        decimal_part = pattern_match.group(1)
        expected_thickness = float(f"0.{decimal_part}")

        space_dot_mm_files.append({
            'prog_num': prog_num,
            'title': title,
            'decimal_part': decimal_part,
            'expected': expected_thickness,
            'thickness': thickness,
            'thickness_display': thickness_display
        })

print("=" * 80)
print(f"FILES WITH ' .##MM' PATTERN: {len(space_dot_mm_files)}")
print("=" * 80)
print()

if space_dot_mm_files:
    print(f"{'Prog #':<10} {'Pattern':<12} {'Display':<12} {'Stored':<12} {'Expected':<12} {'Title':<40}")
    print("-" * 110)

    wrong_detections = 0

    for item in space_dot_mm_files:
        title_short = item['title'][:37] + "..." if len(item['title']) > 40 else item['title']
        pattern = f".{item['decimal_part']}MM"
        display = item['thickness_display'] if item['thickness_display'] else "None"
        stored = f"{item['thickness']:.3f}" if item['thickness'] else "None"
        expected = f"{item['expected']:.2f}\""

        # Check if detection is wrong
        is_wrong = False
        if item['thickness']:
            # Check if thickness is way off (more than 0.5 inches difference)
            diff = abs(item['thickness'] - item['expected'])
            if diff > 0.5:
                is_wrong = True
                wrong_detections += 1

        marker = "[ERROR]" if is_wrong else ""
        print(f"{item['prog_num']:<10} {pattern:<12} {display:<12} {stored:<12} {expected:<12} {title_short} {marker}")

    print()
    print(f"Total files with pattern: {len(space_dot_mm_files)}")
    print(f"Files with wrong detection: {wrong_detections}")
else:
    print("No files found with ' .##MM' pattern!")

conn.close()
