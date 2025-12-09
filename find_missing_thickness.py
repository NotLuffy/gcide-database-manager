import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("FINDING FILES WITH NO THICKNESS DETECTED")
print("=" * 80)
print()

# Find all files with NULL thickness
cursor.execute("""
    SELECT program_number, title, file_path, spacer_type
    FROM programs
    WHERE thickness IS NULL
      AND title IS NOT NULL
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Found {len(results)} files with no thickness detected\n")

# Analyze the titles to find patterns
thickness_patterns_in_title = []
no_obvious_pattern = []

for prog_num, title, file_path, spacer_type in results[:100]:  # Check first 100
    # Common thickness patterns
    patterns = [
        (r'(\d+\.?\d*)\s*(?:IN|")\s+(?:THK|THICK)', 'Inches with THK'),
        (r'(\d*\.?\d+)\s+THK', 'Decimal with THK'),
        (r'(\d*\.?\d+)\s+HC', 'Decimal before HC'),
        (r'(\d*\.?\d+)\s*-*HC', 'Decimal before -HC'),
        (r'/(\d*\.?\d+)\s+', 'After slash'),
        (r'(\d+\.?\d*)\s*MM\s+', 'MM value'),
        (r'\s+(\d*\.?\d+)\s*$', 'End of line'),
    ]

    found_pattern = False
    for pattern, description in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            value = match.group(1)
            thickness_patterns_in_title.append({
                'prog_num': prog_num,
                'title': title,
                'pattern': description,
                'value': value,
                'spacer_type': spacer_type
            })
            found_pattern = True
            break

    if not found_pattern:
        no_obvious_pattern.append((prog_num, title, spacer_type))

print("=" * 80)
print(f"FILES WITH THICKNESS PATTERN IN TITLE: {len(thickness_patterns_in_title)}")
print("=" * 80)
print("These files have clear thickness values in title but aren't being detected:")
print()
print(f"{'Prog #':<10} {'Pattern':<25} {'Value':<10} {'Type':<15} {'Title':<50}")
print("-" * 120)

for item in thickness_patterns_in_title[:30]:
    title_short = item['title'][:47] + "..." if len(item['title']) > 50 else item['title']
    print(f"{item['prog_num']:<10} {item['pattern']:<25} {item['value']:<10} {item['spacer_type']:<15} {title_short}")

if len(thickness_patterns_in_title) > 30:
    print(f"\n... and {len(thickness_patterns_in_title) - 30} more files with patterns")

print()
print("=" * 80)
print(f"FILES WITH NO OBVIOUS PATTERN: {len(no_obvious_pattern)}")
print("=" * 80)
print("These files might need special handling or title correction:")
print()

for prog_num, title, spacer_type in no_obvious_pattern[:20]:
    print(f"{prog_num}: {title[:80]}")

print()
print("=" * 80)
print("PATTERN BREAKDOWN")
print("=" * 80)

# Count by pattern type
pattern_counts = {}
for item in thickness_patterns_in_title:
    pattern = item['pattern']
    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
    print(f"  {pattern:<30} {count:>6} files")

print()
print("=" * 80)
print("SPECIFIC FILE CHECK: o50494")
print("=" * 80)

cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, file_path
    FROM programs
    WHERE program_number = 'o50494'
""")

result = cursor.fetchone()
if result:
    prog_num, title, thickness, thickness_display, file_path = result
    print(f"Program: {prog_num}")
    print(f"Title: {title}")
    print(f"Thickness: {thickness}")
    print(f"Display: {thickness_display}")
    print()

    # Check what pattern should match
    if '1.75' in title and 'HC' in title.upper():
        print("ISSUE: Title contains '1.75' and 'HC' but thickness not detected!")
        print("Pattern that should match: '1.75 HC' or '1.75 --HC'")
else:
    print("o50494 not found in database")

conn.close()
