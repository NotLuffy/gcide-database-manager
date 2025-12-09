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
print('RESCANNING 2PC FILES WITH OB DETECTION')
print('=' * 80)
print()

# Find all 2PC files that have hub_diameter in title but no OB detected in G-code
cursor.execute('''
    SELECT program_number, file_path, title, hub_diameter, ob_from_gcode
    FROM programs
    WHERE (title LIKE "%2PC%" OR title LIKE "% RNG%")
      AND hub_diameter IS NOT NULL
      AND hub_diameter > 0
      AND (ob_from_gcode IS NULL OR ob_from_gcode = 0)
    ORDER BY program_number
''')

results = cursor.fetchall()

print(f'Found {len(results)} 2PC/RNG files with title OB but no G-code OB\n')
print(f'Starting rescan...\n')

parser = ImprovedGCodeParser()

rescanned_count = 0
error_count = 0
fixed_count = 0

for i, (prog_num, file_path, title, title_ob, old_ob_gcode) in enumerate(results):
    if not file_path or not os.path.exists(file_path):
        error_count += 1
        continue

    try:
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
                SET ob_from_gcode = ?,
                    validation_status = ?,
                    validation_issues = ?,
                    validation_warnings = ?,
                    bore_warnings = ?,
                    dimensional_issues = ?
                WHERE program_number = ?
            ''', (
                parse_result.ob_from_gcode,
                validation_status,
                json.dumps(parse_result.validation_issues) if parse_result.validation_issues else None,
                json.dumps(parse_result.validation_warnings) if parse_result.validation_warnings else None,
                json.dumps(parse_result.bore_warnings) if parse_result.bore_warnings else None,
                json.dumps(parse_result.dimensional_issues) if parse_result.dimensional_issues else None,
                prog_num
            ))

            rescanned_count += 1

            # Check if OB was detected
            if parse_result.ob_from_gcode and parse_result.ob_from_gcode > 0:
                fixed_count += 1

                if fixed_count <= 30:
                    print(f'[FIXED] {prog_num}: {title[:60]}')
                    print(f'  Title OB: {title_ob:.1f}mm')
                    print(f'  NEW G-code OB: {parse_result.ob_from_gcode:.1f}mm')
                    print(f'  Difference: {abs(parse_result.ob_from_gcode - title_ob):.1f}mm')
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
print(f'  Now have OB detected: {fixed_count}')
print(f'  Errors: {error_count}')
print()
print('Fixes applied:')
print('  - OB detection now works for 2PC files (not just hub-centric)')
print('  - 2PC files with HC interface now detect OB from OP2 progressive facing')
print('  - T121 in OP2 correctly stops OB detection (chamfering, not turning)')
print()
print('Restart the application to see the updated values in the GUI.')
