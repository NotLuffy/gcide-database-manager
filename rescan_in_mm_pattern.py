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
print('RESCANNING FILES WITH IN/MM PATTERN (e.g., 6.25IN/220MM)')
print('=' * 80)
print()

# Find all files with IN/MM pattern in title
cursor.execute('''
    SELECT program_number, file_path, title, center_bore, hub_diameter
    FROM programs
    WHERE title LIKE "%IN/%MM%"
    ORDER BY program_number
''')

results = cursor.fetchall()

print(f'Found {len(results)} files with IN/MM pattern\n')
print(f'Starting rescan...\n')

parser = ImprovedGCodeParser()

rescanned_count = 0
error_count = 0
fixed_count = 0

for i, (prog_num, file_path, title, old_cb, old_ob) in enumerate(results):
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
                SET center_bore = ?,
                    hub_diameter = ?,
                    validation_status = ?,
                    validation_issues = ?,
                    validation_warnings = ?,
                    bore_warnings = ?,
                    dimensional_issues = ?
                WHERE program_number = ?
            ''', (
                parse_result.center_bore,
                parse_result.hub_diameter,
                validation_status,
                json.dumps(parse_result.validation_issues) if parse_result.validation_issues else None,
                json.dumps(parse_result.validation_warnings) if parse_result.validation_warnings else None,
                json.dumps(parse_result.bore_warnings) if parse_result.bore_warnings else None,
                json.dumps(parse_result.dimensional_issues) if parse_result.dimensional_issues else None,
                prog_num
            ))

            rescanned_count += 1

            # Check if values changed
            cb_changed = abs((parse_result.center_bore or 0) - (old_cb or 0)) > 1.0
            ob_changed = abs((parse_result.hub_diameter or 0) - (old_ob or 0)) > 1.0

            if cb_changed or ob_changed:
                fixed_count += 1

                if fixed_count <= 30:
                    print(f'[UPDATED] {prog_num}: {title[:60]}')
                    if cb_changed:
                        print(f'  CB: {old_cb:.1f}mm -> {parse_result.center_bore:.1f}mm')
                    if ob_changed:
                        print(f'  OB: {old_ob:.1f}mm -> {parse_result.hub_diameter:.1f}mm')
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
print(f'  Values changed: {fixed_count}')
print(f'  Errors: {error_count}')
print()
print('Fixes applied:')
print('  - "8.7IN/220MM" now correctly parsed as OB=220.98mm (same value, two units)')
print('  - "6.25IN/220MM" now correctly parsed as CB=158.75mm, OB=220mm (different values)')
print('  - Logic checks if inch value ≈ mm value (±5mm) to determine pattern type')
print()
print('Restart the application to see the updated values in the GUI.')
