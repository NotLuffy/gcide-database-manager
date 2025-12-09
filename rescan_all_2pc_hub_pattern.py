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
print('RESCANNING ALL 2PC FILES FOR UNSTATED HUB PATTERN (0.15-0.35")')
print('=' * 80)
print()

# Find all 2PC files (LUG, STUD, UNSURE)
cursor.execute('''
    SELECT program_number, file_path, title, thickness, hub_height, spacer_type,
           validation_status, validation_issues
    FROM programs
    WHERE spacer_type LIKE "%2PC%"
    ORDER BY spacer_type, program_number
''')

results = cursor.fetchall()

print(f'Found {len(results)} 2PC files (LUG, STUD, UNSURE)\n')
print(f'Starting rescan...\n')

parser = ImprovedGCodeParser()

rescanned_count = 0
error_count = 0
status_improved_count = 0
hub_populated_count = 0

for i, (prog_num, file_path, title, old_thickness, old_hub, spacer_type, old_status, old_issues) in enumerate(results):
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
                SET hub_height = ?,
                    validation_status = ?,
                    validation_issues = ?,
                    validation_warnings = ?,
                    bore_warnings = ?,
                    dimensional_issues = ?
                WHERE program_number = ?
            ''', (
                parse_result.hub_height,
                validation_status,
                json.dumps(parse_result.validation_issues) if parse_result.validation_issues else None,
                json.dumps(parse_result.validation_warnings) if parse_result.validation_warnings else None,
                json.dumps(parse_result.bore_warnings) if parse_result.bore_warnings else None,
                json.dumps(parse_result.dimensional_issues) if parse_result.dimensional_issues else None,
                prog_num
            ))

            rescanned_count += 1

            # Check if status improved
            status_improved = old_status == "CRITICAL" and validation_status != "CRITICAL"

            # Check if hub was populated
            hub_was_populated = old_hub is None and parse_result.hub_height is not None

            if status_improved:
                status_improved_count += 1

            if hub_was_populated:
                hub_populated_count += 1

            if (status_improved or hub_was_populated) and (status_improved_count + hub_populated_count) <= 30:
                print(f'[{"FIXED" if status_improved else "UPDATED"}] {prog_num} ({spacer_type}): {title[:50]}')
                if hub_was_populated:
                    print(f'  Hub: None -> {parse_result.hub_height:.3f}"')
                if status_improved:
                    print(f'  Status: {old_status} -> {validation_status}')
                print()

        if (i + 1) % 100 == 0:
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
print(f'  Status improved (CRITICAL -> other): {status_improved_count}')
print(f'  Hub height populated: {hub_populated_count}')
print(f'  Errors: {error_count}')
print()
print('Fixes applied:')
print('  - Accept ANY 2PC (LUG, STUD, UNSURE) with hub in range 0.15-0.35"')
print('  - No longer require specific spacer type or "HC" keyword')
print('  - Automatically populate hub_height for all valid patterns')
print('  - Clear thickness errors for 2PC with unstated hub')
print()
print('Restart the application to see the updated values in the GUI.')
