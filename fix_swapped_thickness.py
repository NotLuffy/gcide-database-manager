import sqlite3
import sys
import os

# Add the current directory to path to import the parser
sys.path.insert(0, os.path.dirname(__file__))

from improved_gcode_parser import ImprovedGCodeParser

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

# Files with swapped thickness/hub height
problem_files = [
    ('o50240', 1.0, 0.50),  # Should be: thickness=1.0, hub_height=0.50
    ('o80056', 1.0, 0.50),  # Should be: thickness=1.0, hub_height=0.50
    ('o95500', 6.0, 1.0),   # Should be: thickness=6.0, hub_height=1.0
]

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("FIXING SWAPPED THICKNESS/HUB HEIGHT")
print("=" * 80)
print()

# Initialize parser
parser = ImprovedGCodeParser()

fixed_count = 0

for prog_num, expected_thickness, expected_hub_height in problem_files:
    # Get current values
    cursor.execute("""
        SELECT title, thickness, thickness_display, hub_height, file_path
        FROM programs
        WHERE program_number = ?
    """, (prog_num,))

    result = cursor.fetchone()
    if not result:
        print(f"{prog_num}: NOT FOUND in database")
        continue

    title, old_thickness, old_thickness_display, old_hub_height, file_path = result

    print(f"{prog_num}: {title}")
    print(f"  OLD: Thickness={old_thickness:.2f}, Hub Height={old_hub_height:.2f}")

    # Re-parse the file with updated parser
    if file_path and os.path.exists(file_path):
        parse_result = parser.parse_file(file_path)
        if parse_result:
            new_thickness = parse_result.thickness
            new_hub_height = parse_result.hub_height

            print(f"  NEW: Thickness={new_thickness:.2f}, Hub Height={new_hub_height:.2f}")

            # Update database
            cursor.execute("""
                UPDATE programs
                SET thickness = ?,
                    thickness_display = ?,
                    hub_height = ?
                WHERE program_number = ?
            """, (new_thickness, parse_result.thickness_display, new_hub_height, prog_num))

            fixed_count += 1
            print(f"  [OK] Fixed!")
        else:
            print(f"  [ERROR] Failed to parse file")
    else:
        print(f"  [ERROR] File not found: {file_path}")

    print()

conn.commit()
conn.close()

print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"Fixed: {fixed_count} files")
