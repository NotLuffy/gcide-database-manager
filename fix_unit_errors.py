"""
Fix programs with CB > 1000mm (unit conversion errors from title typos like "125IN" instead of "125MM")
Re-parse these programs with the fixed parser.
"""

import sqlite3
from improved_gcode_parser import ImprovedGCodeParser
import json

db_path = 'gcode_database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all programs with CB > 1000mm
cursor.execute("""
    SELECT program_number, file_path, center_bore
    FROM programs
    WHERE center_bore > 1000
""")

programs = cursor.fetchall()
print(f"Found {len(programs)} programs with CB > 1000mm (unit errors)")

parser = ImprovedGCodeParser()
fixed_count = 0

for prog_num, file_path, old_cb in programs:
    print(f"\nFixing {prog_num}: old CB={old_cb}mm")

    try:
        # Re-parse with fixed parser
        result = parser.parse_file(file_path)

        print(f"  New CB from title: {result.center_bore}mm")
        print(f"  CB from G-code: {result.cb_from_gcode}mm")

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

        print(f"  Validation status: {validation_status}")

        # Update database
        cursor.execute("""
            UPDATE programs SET
                center_bore = ?,
                cb_from_gcode = ?,
                validation_status = ?,
                validation_issues = ?,
                validation_warnings = ?,
                bore_warnings = ?,
                dimensional_issues = ?
            WHERE program_number = ?
        """, (
            result.center_bore,
            result.cb_from_gcode,
            validation_status,
            '|'.join(result.validation_issues) if result.validation_issues else None,
            '|'.join(result.validation_warnings) if result.validation_warnings else None,
            '|'.join(result.bore_warnings) if result.bore_warnings else None,
            '|'.join(result.dimensional_issues) if result.dimensional_issues else None,
            prog_num
        ))

        fixed_count += 1
        print(f"  [OK] Fixed")

    except Exception as e:
        print(f"  [ERROR] {e}")

conn.commit()
conn.close()

print(f"\n\nFixed {fixed_count}/{len(programs)} programs")
print("Done!")
