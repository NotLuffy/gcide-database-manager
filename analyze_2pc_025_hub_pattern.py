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
print('ANALYZING 2PC FILES WITH 0.25" HUB PATTERN')
print('=' * 80)
print()

# Find 2PC files with thickness errors close to 0.25" difference
cursor.execute('''
    SELECT program_number, file_path, title, thickness, hub_height, spacer_type,
           validation_issues
    FROM programs
    WHERE (spacer_type LIKE "%2PC%")
      AND validation_issues LIKE "%THICKNESS ERROR%"
      AND validation_issues LIKE "%+0.25%"
    ORDER BY spacer_type, program_number
    LIMIT 50
''')

results = cursor.fetchall()

print(f'Found {len(results)} 2PC files with ~0.25" thickness difference\n')

parser = ImprovedGCodeParser()

by_type = {'2PC LUG': [], '2PC STUD': [], '2PC UNSURE': []}

for prog_num, file_path, title, thickness, hub_height, spacer_type, issues_json in results:
    # Parse the G-code to get drill depth
    drill_depth = None
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Look for drill depth
            for line in lines[:100]:
                if 'G81' in line.upper() or 'G83' in line.upper():
                    import re
                    z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
                    if z_match:
                        drill_depth = float(z_match.group(1))
                        break
        except:
            pass

    if drill_depth and thickness:
        implied_hub = drill_depth - thickness - 0.15

        # Check if exactly 0.25" hub (within 0.02" tolerance)
        if abs(implied_hub - 0.25) < 0.02:
            entry = {
                'prog': prog_num,
                'title': title[:65],
                'type': spacer_type,
                'thickness': thickness,
                'drill': drill_depth,
                'hub': hub_height,
                'implied_hub': implied_hub
            }

            if spacer_type in by_type:
                by_type[spacer_type].append(entry)

print('=' * 80)
print('2PC FILES WITH EXACTLY 0.25" IMPLIED HUB')
print('=' * 80)
print()

for spacer_type in ['2PC LUG', '2PC STUD', '2PC UNSURE']:
    files = by_type[spacer_type]
    if files:
        print(f'{spacer_type}: {len(files)} files')
        print('-' * 80)
        for entry in files[:10]:
            print(f'{entry["prog"]}: {entry["title"]}')
            print(f'  Thickness: {entry["thickness"]}", Drill: {entry["drill"]}", Implied hub: {entry["implied_hub"]:.3f}"')
            print(f'  Hub in DB: {entry["hub"]}" ({"NOT SET" if entry["hub"] is None else "SET"})')
            print()
        if len(files) > 10:
            print(f'  ... and {len(files) - 10} more files')
        print()

total = sum(len(files) for files in by_type.values())

print('=' * 80)
print('PATTERN SUMMARY')
print('=' * 80)
print()
print(f'Total 2PC files with 0.25" implied hub: {total}')
print()
print('These files show the pattern:')
print('  - Title: "X.XX" thick (body thickness)')
print('  - Drill: title_thickness + 0.25" + 0.15" breach')
print('  - Hub: 0.25" (NOT stated in title)')
print()
print('This pattern appears in:')
print(f'  - 2PC LUG: {len(by_type["2PC LUG"])} files')
print(f'  - 2PC STUD: {len(by_type["2PC STUD"])} files')
print(f'  - 2PC UNSURE: {len(by_type["2PC UNSURE"])} files')
print()
print('Solution:')
print('  - For ANY 2PC file (LUG, STUD, UNSURE):')
print('  - If implied_hub = drill - thickness - 0.15 is close to 0.25" (±0.02")')
print('  - Accept as valid 2PC with unstated 0.25" hub')
print('  - Populate hub_height = 0.25"')
print('  - No thickness error')

conn.close()
