import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("FINDING ALL FILES WITH POTENTIAL --HC THICKNESS ISSUES")
print("=" * 80)
print()

# Find all files with --HC or -HC pattern in title
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, hub_height, spacer_type
    FROM programs
    WHERE is_managed = 1
      AND (title LIKE '%--HC%' OR title LIKE '% -HC %')
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Found {len(results)} files with --HC or -HC in title\n")

potential_issues = []
correctly_parsed = []

for prog_num, title, thickness, thickness_display, hub_height, spacer_type in results:
    # Extract expected values from title using the pattern: "##.## --HC ##.##" or "##.## -HC ##.##"
    hc_pattern = re.search(r'(\d+\.?\d*)\s+--?HC\s+(\d+\.?\d*)', title, re.IGNORECASE)

    if hc_pattern:
        expected_thickness = float(hc_pattern.group(1))
        expected_hub_height = float(hc_pattern.group(2))

        if thickness and hub_height:
            # Check if values match (with small tolerance)
            thickness_matches = abs(thickness - expected_thickness) < 0.05
            hub_matches = abs(hub_height - expected_hub_height) < 0.05

            if thickness_matches and hub_matches:
                correctly_parsed.append((prog_num, title, thickness, hub_height))
            else:
                potential_issues.append({
                    'prog_num': prog_num,
                    'title': title,
                    'db_thickness': thickness,
                    'db_hub_height': hub_height,
                    'expected_thickness': expected_thickness,
                    'expected_hub_height': expected_hub_height
                })

print("=" * 80)
print(f"CORRECTLY PARSED: {len(correctly_parsed)} files")
print("=" * 80)
print("Sample of correctly parsed files:")
for prog_num, title, thickness, hub_height in correctly_parsed[:10]:
    print(f"{prog_num}: Thick={thickness:.2f}, Hub={hub_height:.2f} - {title[:50]}")

print()
print("=" * 80)
print(f"POTENTIAL ISSUES: {len(potential_issues)} files")
print("=" * 80)

if potential_issues:
    print(f"{'Prog #':<10} {'DB Thick':<10} {'Expected':<10} {'DB Hub':<10} {'Expected':<10} {'Title':<40}")
    print("-" * 100)

    for item in potential_issues:
        title_short = item['title'][:37] + "..." if len(item['title']) > 40 else item['title']
        print(f"{item['prog_num']:<10} {item['db_thickness']:<10.2f} {item['expected_thickness']:<10.2f} "
              f"{item['db_hub_height']:<10.2f} {item['expected_hub_height']:<10.2f} {title_short}")
else:
    print("No issues found! All files parsed correctly.")

conn.close()

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total files checked: {len(results)}")
print(f"  [OK] Correctly parsed: {len(correctly_parsed)}")
print(f"  [!] Potential issues: {len(potential_issues)}")
