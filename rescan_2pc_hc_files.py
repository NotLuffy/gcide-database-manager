import sqlite3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))
from improved_gcode_parser import ImprovedGCodeParser

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print('=' * 80)
print('RESCANNING 2PC AND 13.0 ROUND FILES WITH HC DIMENSIONS')
print('=' * 80)
print()

# Find all files that need rescanning:
# 1. 2PC files with HC in title
# 2. 13.0 round files with HC
cursor.execute('''
    SELECT program_number, file_path, title
    FROM programs
    WHERE (spacer_type LIKE "2PC%" AND title LIKE "% HC %")
       OR (title LIKE "13.0%" AND title LIKE "%IN/%")
    ORDER BY program_number
''')

results = cursor.fetchall()

print(f'Found {len(results)} files to rescan\n')
print(f'Starting rescan...\n')

parser = ImprovedGCodeParser()

rescanned_count = 0
error_count = 0
fixed_count = 0

for i, (prog_num, file_path, title) in enumerate(results):
    if not file_path or not os.path.exists(file_path):
        error_count += 1
        continue

    try:
        # Get old values
        cursor.execute('''
            SELECT thickness, hub_height, hub_diameter
            FROM programs
            WHERE program_number = ?
        ''', (prog_num,))
        old_result = cursor.fetchone()
        old_thick, old_hub_h, old_hub_d = old_result if old_result else (None, None, None)

        # Re-parse file
        parse_result = parser.parse_file(file_path)

        if parse_result:
            # Determine validation status
            validation_status = "PASS"
            if parse_result.validation_issues:
                validation_status = "CRITICAL"
            elif parse_result.bore_warnings:
                validation_status = "BORE_WARNING"
            elif parse_result.dimensional_issues:
                validation_status = "DIMENSIONAL"
            elif parse_result.validation_warnings:
                validation_status = "WARNING"

            # Update database
            cursor.execute('''
                UPDATE programs
                SET thickness = ?,
                    thickness_display = ?,
                    hub_height = ?,
                    hub_diameter = ?,
                    center_bore = ?,
                    validation_status = ?,
                    validation_issues = ?,
                    validation_warnings = ?,
                    bore_warnings = ?,
                    dimensional_issues = ?
                WHERE program_number = ?
            ''', (
                parse_result.thickness,
                parse_result.thickness_display,
                parse_result.hub_height,
                parse_result.hub_diameter,
                parse_result.center_bore,
                validation_status,
                json.dumps(parse_result.validation_issues) if parse_result.validation_issues else None,
                json.dumps(parse_result.validation_warnings) if parse_result.validation_warnings else None,
                json.dumps(parse_result.bore_warnings) if parse_result.bore_warnings else None,
                json.dumps(parse_result.dimensional_issues) if parse_result.dimensional_issues else None,
                prog_num
            ))

            rescanned_count += 1

            # Check if values changed
            changed = False
            if old_thick != parse_result.thickness or old_hub_h != parse_result.hub_height or old_hub_d != parse_result.hub_diameter:
                changed = True
                fixed_count += 1

                if fixed_count <= 20:
                    print(f'[FIXED] {prog_num}: {title[:60]}')
                    print(f'  OLD: thick={old_thick}, hub_h={old_hub_h}, hub_d={old_hub_d}')
                    print(f'  NEW: thick={parse_result.thickness}, hub_h={parse_result.hub_height}, hub_d={parse_result.hub_diameter}')
                    print()

        if (i + 1) % 50 == 0:
            print(f'  ... processed {i + 1}/{len(results)} files')
            conn.commit()

    except Exception as e:
        error_count += 1
        if error_count <= 5:
            print(f'[ERROR] {prog_num}: {e}')

conn.commit()
conn.close()

print()
print('=' * 80)
print('RESCAN COMPLETE')
print('=' * 80)
print(f'Files processed: {len(results)}')
print(f'  Successfully rescanned: {rescanned_count}')
print(f'  Values changed (fixed): {fixed_count}')
print(f'  Errors: {error_count}')
print()
print('Fixes applied:')
print('  - 2PC files with HC now parse thickness/hub correctly')
print('  - Decimal HC patterns (.75 HC, 1. HC) now work')
print('  - 13.0 round files now extract hub diameter from "8.7IN/220MM" pattern')
print()
print('Restart the application to see the updated values in the GUI.')
