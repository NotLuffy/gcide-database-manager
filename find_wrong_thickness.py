import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("FINDING FILES WITH INCORRECT THICKNESS DETECTION")
print("=" * 80)
print()

# Find hub_centric files with patterns like "##.## --HC ##.##" or "##.## HC ##.##"
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, hub_height, spacer_type
    FROM programs
    WHERE is_managed = 1
      AND spacer_type = 'hub_centric'
      AND title LIKE '%HC%'
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Checking {len(results)} hub_centric files with HC in title...\n")

wrong_thickness = []

for prog_num, title, thickness, thickness_display, hub_height, spacer_type in results:
    # Pattern: "##.## --HC ##.##" or "##.## HC ##.##" or "##.## -HC ##.##"
    # First number is thickness, second number is hub height
    hc_pattern = re.search(r'(\d+\.?\d*)\s+(?:-{0,2}HC)\s+(\d+\.?\d*)', title, re.IGNORECASE)

    if hc_pattern:
        # Extract values from title
        title_thickness = float(hc_pattern.group(1))
        title_hub_height = float(hc_pattern.group(2))

        # Check if database has it backwards
        if thickness and hub_height:
            # Allow small tolerance for floating point comparison
            thickness_wrong = abs(thickness - title_thickness) > 0.05
            hub_wrong = abs(hub_height - title_hub_height) > 0.05

            # If thickness doesn't match title but is close to title's hub height
            if thickness_wrong and abs(thickness - title_hub_height) < 0.05:
                wrong_thickness.append({
                    'prog_num': prog_num,
                    'title': title,
                    'db_thickness': thickness,
                    'db_hub_height': hub_height,
                    'title_thickness': title_thickness,
                    'title_hub_height': title_hub_height
                })

print("=" * 80)
print(f"FILES WITH SWAPPED THICKNESS/HUB HEIGHT: {len(wrong_thickness)}")
print("=" * 80)
print()

if wrong_thickness:
    print(f"{'Prog #':<10} {'DB Thick':<10} {'Should Be':<10} {'DB Hub':<10} {'Should Be':<10} {'Title':<40}")
    print("-" * 100)

    for item in wrong_thickness[:50]:
        title_short = item['title'][:37] + "..." if len(item['title']) > 40 else item['title']
        print(f"{item['prog_num']:<10} {item['db_thickness']:<10.2f} {item['title_thickness']:<10.2f} "
              f"{item['db_hub_height']:<10.2f} {item['title_hub_height']:<10.2f} {title_short}")

    if len(wrong_thickness) > 50:
        print(f"\n... and {len(wrong_thickness) - 50} more files")
else:
    print("No files found with swapped thickness/hub height!")

conn.close()
