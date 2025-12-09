"""
Rescan all programs with CB TOO SMALL errors using the new VALIDATE_WITH_TITLE CB detection strategy.
This should fix ~2426 programs that were broken by the Dec 4th chamfer-depth fix.
"""

import sqlite3
from improved_gcode_parser import ImprovedGCodeParser
import os

db_path = 'gcode_database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all programs with CB TOO SMALL errors
cursor.execute("""
    SELECT program_number, file_path, center_bore, cb_from_gcode, validation_issues
    FROM programs
    WHERE validation_status = 'CRITICAL'
    AND validation_issues LIKE '%CB TOO SMALL%'
    AND file_path IS NOT NULL
""")

programs = cursor.fetchall()
print(f"Found {len(programs)} programs with CB TOO SMALL errors")
print("=" * 80)

parser = ImprovedGCodeParser()
fixed_count = 0
errors = 0
status_changes = {
    'CRITICAL_TO_PASS': 0,
    'CRITICAL_TO_WARNING': 0,
    'CRITICAL_TO_BORE_WARNING': 0,
    'CRITICAL_TO_DIMENSIONAL': 0,
    'STILL_CRITICAL': 0
}

for i, (prog_num, file_path, old_cb, old_cb_gcode, old_issues) in enumerate(programs):
    if not os.path.exists(file_path):
        print(f"[{i+1}/{len(programs)}] {prog_num}: File not found - {file_path}")
        errors += 1
        continue

    try:
        # Re-parse with new CB detection logic
        result = parser.parse_file(file_path)

        # Calculate validation status
        validation_status = "PASS"
        if result.validation_issues:
            validation_status = "CRITICAL"
        elif result.bore_warnings:
            validation_status = "BORE_WARNING"
        elif result.dimensional_issues:
            validation_status = "DIMENSIONAL"
        elif result.validation_warnings:
            validation_status = "WARNING"

        # Track status changes
        if validation_status == "PASS":
            status_changes['CRITICAL_TO_PASS'] += 1
        elif validation_status == "WARNING":
            status_changes['CRITICAL_TO_WARNING'] += 1
        elif validation_status == "BORE_WARNING":
            status_changes['CRITICAL_TO_BORE_WARNING'] += 1
        elif validation_status == "DIMENSIONAL":
            status_changes['CRITICAL_TO_DIMENSIONAL'] += 1
        else:
            status_changes['STILL_CRITICAL'] += 1

        # Update database
        cursor.execute("""
            UPDATE programs SET
                cb_from_gcode = ?,
                validation_status = ?,
                validation_issues = ?,
                validation_warnings = ?,
                bore_warnings = ?,
                dimensional_issues = ?
            WHERE program_number = ?
        """, (
            result.cb_from_gcode,
            validation_status,
            '|'.join(result.validation_issues) if result.validation_issues else None,
            '|'.join(result.validation_warnings) if result.validation_warnings else None,
            '|'.join(result.bore_warnings) if result.bore_warnings else None,
            '|'.join(result.dimensional_issues) if result.dimensional_issues else None,
            prog_num
        ))

        fixed_count += 1

        # Print progress every 100 files
        if (i + 1) % 100 == 0:
            print(f"[{i+1}/{len(programs)}] Processed {fixed_count} files, {errors} errors")

        # Print detailed info for first 10 fixes
        if i < 10 or validation_status != "CRITICAL":
            print(f"\n[{i+1}/{len(programs)}] {prog_num}:")
            print(f"  Old CB: spec={old_cb:.1f}mm, gcode={old_cb_gcode:.1f}mm")
            print(f"  New CB: spec={result.center_bore:.1f}mm, gcode={result.cb_from_gcode:.1f}mm")
            print(f"  Status: CRITICAL -> {validation_status}")

    except Exception as e:
        print(f"[{i+1}/{len(programs)}] {prog_num}: ERROR - {e}")
        errors += 1

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("RESCAN COMPLETE")
print("=" * 80)
print(f"Total programs: {len(programs)}")
print(f"Successfully rescanned: {fixed_count}")
print(f"Errors: {errors}")
print("\nStatus Changes:")
print(f"  CRITICAL -> PASS: {status_changes['CRITICAL_TO_PASS']}")
print(f"  CRITICAL -> WARNING: {status_changes['CRITICAL_TO_WARNING']}")
print(f"  CRITICAL -> BORE_WARNING: {status_changes['CRITICAL_TO_BORE_WARNING']}")
print(f"  CRITICAL -> DIMENSIONAL: {status_changes['CRITICAL_TO_DIMENSIONAL']}")
print(f"  Still CRITICAL: {status_changes['STILL_CRITICAL']}")
print("\nRestart the application to see updated values in the GUI.")
