import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("FINDING FILES WITH MM THICKNESS IN TITLE")
print("=" * 80)
print()

# Find all files with MM in the title that might indicate MM thickness
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display
    FROM programs
    WHERE is_managed = 1
      AND title LIKE '%MM%'
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Found {len(results)} files with 'MM' in title\n")

# Categorize by whether thickness_display already shows MM
already_mm = []
needs_fix = []
no_thickness = []

for prog_num, title, thickness, thickness_display in results:
    if thickness_display and 'MM' in thickness_display:
        already_mm.append((prog_num, title, thickness_display))
    elif thickness is not None:
        # Has thickness but display doesn't show MM
        # Check if title indicates MM thickness
        mm_patterns = [
            r'(\d+)\s*MM\s+(?:SPACER|SPC|THK|HC)',
            r'(\d+\.?\d*)\s*MM\s*$',
            r'ID\s+(\d+)\s*MM',
        ]

        found_mm = False
        for pattern in mm_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                mm_value = match.group(1)
                needs_fix.append((prog_num, title, thickness, thickness_display, mm_value))
                found_mm = True
                break

        if not found_mm:
            # MM in title but not for thickness (e.g., "70MM/60MM B/C")
            pass
    else:
        no_thickness.append((prog_num, title))

print("=" * 80)
print(f"FILES ALREADY SHOWING MM IN THICKNESS_DISPLAY: {len(already_mm)}")
print("=" * 80)
for prog_num, title, thickness_display in already_mm[:20]:
    print(f"{prog_num}: {thickness_display:8s} - {title[:60]}")
if len(already_mm) > 20:
    print(f"... and {len(already_mm) - 20} more")

print()
print("=" * 80)
print(f"FILES THAT NEED MM DISPLAY FIX: {len(needs_fix)}")
print("=" * 80)
for prog_num, title, thickness, thickness_display, mm_value in needs_fix[:20]:
    current_display = thickness_display if thickness_display else f"{thickness:.3f}"
    print(f"{prog_num}: Currently '{current_display}', should be '{mm_value}MM' - {title[:50]}")
if len(needs_fix) > 20:
    print(f"... and {len(needs_fix) - 20} more")

print()
print("=" * 80)
print(f"FILES WITH MM IN TITLE BUT NO THICKNESS: {len(no_thickness)}")
print("=" * 80)
for prog_num, title in no_thickness[:20]:
    print(f"{prog_num}: {title[:70]}")
if len(no_thickness) > 20:
    print(f"... and {len(no_thickness) - 20} more")

conn.close()
