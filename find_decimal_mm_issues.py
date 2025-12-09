import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = cursor = conn.cursor()

print("=" * 80)
print("FINDING FILES WITH .##MM PATTERN (decimal without leading zero)")
print("=" * 80)
print()

# Find files with pattern like ".75MM", ".5MM", ".25MM" etc in title
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display
    FROM programs
    WHERE is_managed = 1
      AND title LIKE '%.%MM%'
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Checking {len(results)} files with decimals and MM in title...\n")

# Filter for files with .##MM pattern (decimal without leading zero)
decimal_mm_issues = []

for prog_num, title, thickness, thickness_display in results:
    # Pattern: .## MM (decimal without leading zero followed by MM)
    # Should match: ".75MM", ".5MM", ".25 MM", etc.
    # Should NOT match: "0.75MM", "70.5MM", etc.
    decimal_mm_pattern = re.search(r'\s+\.(\d+)\s*MM\s+', title, re.IGNORECASE)

    if decimal_mm_pattern:
        decimal_part = decimal_mm_pattern.group(1)
        expected_thickness = float(f"0.{decimal_part}")

        # Check if thickness_display shows wrong value
        if thickness_display and 'MM' in thickness_display:
            # Extract MM value from display
            mm_value_str = thickness_display.replace('MM', '').replace('mm', '').strip()
            try:
                detected_mm = float(mm_value_str)

                # Check if it's treating ".75MM" as "75MM"
                if detected_mm == float(decimal_part):  # e.g., detected 75 instead of 0.75
                    decimal_mm_issues.append({
                        'prog_num': prog_num,
                        'title': title,
                        'pattern': f'.{decimal_part}MM',
                        'detected': thickness_display,
                        'expected_inches': expected_thickness,
                        'detected_inches': thickness
                    })
            except:
                pass

print("=" * 80)
print(f"FILES WITH .##MM PATTERN ISSUES: {len(decimal_mm_issues)}")
print("=" * 80)
print()

if decimal_mm_issues:
    print(f"{'Prog #':<10} {'Pattern':<12} {'Detected':<12} {'Should Be':<12} {'Title':<45}")
    print("-" * 100)

    for item in decimal_mm_issues:
        title_short = item['title'][:42] + "..." if len(item['title']) > 45 else item['title']
        print(f"{item['prog_num']:<10} {item['pattern']:<12} {item['detected']:<12} "
              f"{item['expected_inches']:<12.2f} {title_short}")

    print()
    print(f"Total files affected: {len(decimal_mm_issues)}")
    print()
    print("These files have '.##MM' patterns (e.g., '.75MM')")
    print("Parser is ignoring the decimal point and treating '.75MM' as '75MM'")
else:
    print("No files found with .##MM pattern issues!")

conn.close()
