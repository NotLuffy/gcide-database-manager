import sqlite3
import sys
import os

# Add the current directory to path to import the parser
sys.path.insert(0, os.path.dirname(__file__))

from improved_gcode_parser import ImprovedGCodeParser

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

# Files with .##MM pattern that are incorrectly detected
problem_files = [
    'o50274', 'o50286', 'o50305', 'o50328', 'o50408', 'o50480',
    'o58239', 'o58253', 'o58278', 'o58305', 'o58405', 'o58420', 'o59001'
]

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("FIXING .##MM THICKNESS DETECTION")
print("=" * 80)
print()

# Initialize parser
parser = ImprovedGCodeParser()

fixed_count = 0
error_count = 0

for prog_num in problem_files:
    # Get current values
    cursor.execute("""
        SELECT title, thickness, thickness_display, file_path
        FROM programs
        WHERE program_number = ?
    """, (prog_num,))

    result = cursor.fetchone()
    if not result:
        print(f"{prog_num}: NOT FOUND in database")
        error_count += 1
        continue

    title, old_thickness, old_thickness_display, file_path = result

    print(f"{prog_num}: {title}")
    print(f"  OLD: {old_thickness_display} ({old_thickness:.3f}\")")

    # Re-parse the file with updated parser
    if file_path and os.path.exists(file_path):
        parse_result = parser.parse_file(file_path)
        if parse_result:
            new_thickness = parse_result.thickness
            new_thickness_display = parse_result.thickness_display

            print(f"  NEW: {new_thickness_display} ({new_thickness:.3f}\")")

            # Update database
            cursor.execute("""
                UPDATE programs
                SET thickness = ?,
                    thickness_display = ?
                WHERE program_number = ?
            """, (new_thickness, new_thickness_display, prog_num))

            fixed_count += 1
            print(f"  [OK] Fixed!")
        else:
            print(f"  [ERROR] Failed to parse file")
            error_count += 1
    else:
        print(f"  [ERROR] File not found: {file_path}")
        error_count += 1

    print()

conn.commit()
conn.close()

print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"Successfully fixed: {fixed_count} files")
print(f"Errors: {error_count} files")
print()
print("Files with '.##MM' pattern now correctly detect as decimal inches")
print("instead of whole millimeters.")
