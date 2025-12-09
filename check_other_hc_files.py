import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING OTHER --HC FILES (Not matching standard pattern)")
print("=" * 80)
print()

# Find all files with --HC or -HC pattern in title
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, hub_height
    FROM programs
    WHERE is_managed = 1
      AND (title LIKE '%--HC%' OR title LIKE '% -HC %')
    ORDER BY program_number
""")

results = cursor.fetchall()

# Filter for files that DON'T match the pattern "##.## --HC ##.##"
other_formats = []

for prog_num, title, thickness, thickness_display, hub_height in results:
    # Check if it matches the standard pattern
    hc_pattern = re.search(r'(\d+\.?\d*)\s+--?HC\s+(\d+\.?\d*)', title, re.IGNORECASE)

    if not hc_pattern:
        other_formats.append((prog_num, title, thickness, hub_height))

print(f"Found {len(other_formats)} files with non-standard --HC format\n")

print("Sample of different formats:")
print("-" * 100)

for prog_num, title, thickness, hub_height in other_formats[:30]:
    thick_str = f"{thickness:.2f}" if thickness else "None"
    hub_str = f"{hub_height:.2f}" if hub_height else "None"
    print(f"{prog_num}: T={thick_str}, H={hub_str} - {title[:65]}")

if len(other_formats) > 30:
    print(f"... and {len(other_formats) - 30} more")

conn.close()
