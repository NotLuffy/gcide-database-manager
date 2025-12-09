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
print('RESCANNING FILES WITH CB/OB DETECTION ERRORS')
print('=' * 80)
print()

# Find all files with CB TOO LARGE or CB TOO SMALL errors
cursor.execute('''
    SELECT program_number, file_path, title
    FROM programs
    WHERE validation_issues LIKE "%CB TOO LARGE%"
       OR validation_issues LIKE "%CB TOO SMALL%"
    ORDER BY program_number
''')

results = cursor.fetchall()

print(f'Found {len(results)} files with CB size errors\n')
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
            SELECT cb_from_gcode, ob_from_gcode, validation_status
            FROM programs
            WHERE program_number = ?
        ''', (prog_num,))
        old_result = cursor.fetchone()
        old_cb, old_ob, old_status = old_result if old_result else (None, None, None)

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
                SET cb_from_gcode = ?,
                    ob_from_gcode = ?,
                    validation_status = ?,
                    validation_issues = ?,
                    validation_warnings = ?,
                    bore_warnings = ?,
                    dimensional_issues = ?
                WHERE program_number = ?
            ''', (
                parse_result.cb_from_gcode,
                parse_result.ob_from_gcode,
                validation_status,
                json.dumps(parse_result.validation_issues) if parse_result.validation_issues else None,
                json.dumps(parse_result.validation_warnings) if parse_result.validation_warnings else None,
                json.dumps(parse_result.bore_warnings) if parse_result.bore_warnings else None,
                json.dumps(parse_result.dimensional_issues) if parse_result.dimensional_issues else None,
                prog_num
            ))

            rescanned_count += 1

            # Check if validation status improved
            if old_status == 'CRITICAL' and validation_status != 'CRITICAL':
                fixed_count += 1

                if fixed_count <= 20:
                    print(f'[FIXED] {prog_num}: {title[:60]}')
                    print(f'  OLD: CB={old_cb:.1f}mm, Status={old_status}')
                    print(f'  NEW: CB={parse_result.cb_from_gcode:.1f}mm, Status={validation_status}')
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
print(f'  Fixed (CRITICAL -> non-CRITICAL): {fixed_count}')
print(f'  Errors: {error_count}')
print()
print('Fixes applied:')
print('  - Ignored misleading "(X IS CB)" comments at chamfer depth')
print('  - Ignored shallow chamfers (< 0.3" depth) as CB candidates')
print('  - CB now uses smallest X value that reaches full drill depth')
print('  - OB detection from OP2 unchanged (was already correct)')
print()
print('Restart the application to see the updated values in the GUI.')
