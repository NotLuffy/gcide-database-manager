import sqlite3
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from improved_gcode_parser import ImprovedGCodeParser

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('=' * 80)
print('ANALYZING 2PC STUD FILES WITH THICKNESS ERRORS')
print('=' * 80)
print()

# Find 2PC STUD files with thickness errors
cursor.execute('''
    SELECT program_number, file_path, title, thickness, hub_height,
           validation_issues, validation_status
    FROM programs
    WHERE spacer_type LIKE "%STUD%"
      AND (validation_issues LIKE "%THICKNESS%"
           OR validation_status = "CRITICAL")
    ORDER BY program_number
    LIMIT 30
''')

results = cursor.fetchall()

print(f'Found {len(results)} 2PC STUD files with thickness-related errors\n')

parser = ImprovedGCodeParser()

for i, (prog_num, file_path, title, thickness, hub_height, issues_json, status) in enumerate(results[:15]):
    if i >= 15:
        break

    print(f'{prog_num}: {title[:70]}')
    print(f'  Spacer Type: 2PC STUD')
    print(f'  Title Thickness: {thickness}" (spec)')
    print(f'  Title Hub Height: {hub_height}" ({"not specified" if hub_height is None else "specified"})')

    # Parse the actual G-code to see drill depth
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Look for drill depth
            drill_depth = None
            for line in lines[:100]:  # Check first 100 lines
                if 'G81' in line.upper() or 'G83' in line.upper():
                    import re
                    z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
                    if z_match:
                        drill_depth = float(z_match.group(1))
                        break

            if drill_depth:
                calculated_hub = drill_depth - 0.15 - (thickness if thickness else 0)
                print(f'  Drill Depth: {drill_depth}" (from G-code)')
                print(f'  Calculated Hub: {calculated_hub:.3f}" (drill - 0.15 breach - thickness)')
                print(f'  Expected pattern: 0.75" thick + 0.25" hub = 1.00" drill')

                if abs(calculated_hub - 0.25) < 0.1:
                    print(f'  -> MATCHES STUD PATTERN! (hub ~0.25")')
                else:
                    print(f'  -> Hub height unusual for STUD (expected ~0.25")')
        except Exception as e:
            print(f'  Error reading G-code: {e}')

    if issues_json:
        try:
            issues = json.loads(issues_json)
            if issues:
                print(f'  Validation Issue: {issues[0]}')
        except:
            print(f'  Validation Issue: (parsing error)')

    print()

print('=' * 80)
print('PATTERN ANALYSIS')
print('=' * 80)
print()
print('2PC STUD Pattern:')
print('  - Title shows actual spacer thickness (e.g., 0.75")')
print('  - Drill depth = thickness + hub_height + 0.15" breach')
print('  - Hub height typically ~0.25" (often NOT stated in title)')
print('  - Example: "0.75" thick -> drilled 1.00" -> hub = 1.00 - 0.15 - 0.75 = 0.10"')
print()
print('Current Issue:')
print('  - Parser sees drill depth 1.00" and calculates thickness = 0.85"')
print('  - Compares to title spec 0.75" -> ERROR: +0.100" difference')
print('  - Should instead recognize STUD pattern and extract hub height')
print()
print('Solution Needed:')
print('  - Detect 2PC STUD spacer type')
print('  - Calculate hub_height from: drill - 0.15 - thickness')
print('  - Accept drill depth if calculated hub ~0.15-0.35" (typical STUD range)')
print('  - Populate hub_height field instead of throwing thickness error')

conn.close()
