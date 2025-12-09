"""
Rescan all programs with OB/OD match warnings using the fixed parser.
This should fix ~2318 programs that were incorrectly extracting OD as OB.
"""

import sqlite3
from improved_gcode_parser import ImprovedGCodeParser
import os

db_path = 'gcode_database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all programs with OB warnings
cursor.execute("""
    SELECT program_number, file_path
    FROM programs
    WHERE validation_warnings LIKE '%OB extraction uncertain%'
    OR validation_warnings LIKE '%OB%matches OD%'
""")

programs = cursor.fetchall()
print(f"Found {len(programs)} programs with OB/OD match warnings")
print("=" * 80)

parser = ImprovedGCodeParser()
fixed_count = 0
still_warning = 0
errors = 0

for i, (prog_num, file_path) in enumerate(programs):
    if not file_path or not os.path.exists(file_path):
        errors += 1
        continue

    try:
        # Re-parse with fixed OB extraction
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

        # Check if OB warning still present
        has_ob_warning = any('OB' in w and 'matches OD' in w for w in result.validation_warnings)
        if has_ob_warning:
            still_warning += 1
        else:
            fixed_count += 1

        # Update database
        cursor.execute("""
            UPDATE programs SET
                ob_from_gcode = ?,
                validation_status = ?,
                validation_warnings = ?
            WHERE program_number = ?
        """, (
            result.ob_from_gcode,
            validation_status,
            '|'.join(result.validation_warnings) if result.validation_warnings else None,
            prog_num
        ))

        # Show progress every 100 files
        if (i + 1) % 100 == 0:
            print(f"[{i+1}/{len(programs)}] Processed...")

    except Exception as e:
        print(f"[ERROR] {prog_num}: {e}")
        errors += 1

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("RESCAN COMPLETE")
print("=" * 80)
print(f"Total programs: {len(programs)}")
print(f"Fixed (warning removed): {fixed_count}")
print(f"Still has warning: {still_warning}")
print(f"Errors: {errors}")
print("\nRestart the application to see updated OB values!")
