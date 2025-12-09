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
print('RESCANNING FILES WITH OB DETECTION ERRORS')
print('=' * 80)
print()

# Find all files with OB TOO SMALL or OB TOO LARGE errors
cursor.execute('''
    SELECT program_number, file_path, title
    FROM programs
    WHERE validation_issues LIKE "%OB TOO SMALL%"
       OR validation_issues LIKE "%OB TOO LARGE%"
    ORDER BY program_number
''')

results = cursor.fetchall()

print(f'Found {len(results)} files with OB size errors\n')
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
            SELECT ob_from_gcode, validation_status
            FROM programs
            WHERE program_number = ?
        ''', (prog_num,))
        old_result = cursor.fetchone()
        old_ob, old_status = old_result if old_result else (None, None)

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

            # Check if validation status improved
            if old_status == 'CRITICAL' and validation_status != 'CRITICAL':
                fixed_count += 1

                if fixed_count <= 30:
                    print(f'[FIXED] {prog_num}: {title[:60]}')
                    if old_ob and parse_result.ob_from_gcode:
                        print(f'  OLD: OB={old_ob:.1f}mm, Status={old_status}')
                        print(f'  NEW: OB={parse_result.ob_from_gcode:.1f}mm, Status={validation_status}')
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
print('  - Extended OB detection range from 2.2-4.0" to 2.2-10.5"')
print('  - Now detects large OB values in 13" rounds (e.g., X8.661 = 220mm)')
print()
print('Restart the application to see the updated values in the GUI.')
