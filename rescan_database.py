"""
Rescan the database with updated type detection logic.
This will update all records with the new HC priority rules.
"""
import sqlite3
import os
from pathlib import Path
from improved_gcode_parser import ImprovedGCodeParser

# Database path (in same directory as this script)
DB_PATH = "gcode_database.db"
GCODE_DIR = r"I:\My Drive\NC Master\REVISED PROGRAMS\5.75"

def rescan_database():
    """Rescan all files in database with new type detection logic"""

    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all programs in database
    cursor.execute("SELECT program_number, file_path, spacer_type FROM programs ORDER BY program_number")
    programs = cursor.fetchall()

    print(f"Found {len(programs)} programs in database")
    print("Rescanning with updated type detection logic...")
    print("-" * 80)

    parser = ImprovedGCodeParser()
    updated_count = 0
    type_changes = []

    for program_number, file_path, old_type in programs:
        # file_path might be full path or just filename
        if file_path and os.path.exists(file_path):
            filepath = file_path
        else:
            filepath = os.path.join(GCODE_DIR, program_number)

        if not os.path.exists(filepath):
            print(f"WARNING: File not found: {program_number}")
            continue

        # Parse file with new logic
        try:
            result = parser.parse_file(filepath)
            new_type = result.spacer_type

            # Check if type changed
            if old_type != new_type:
                type_changes.append((program_number, old_type, new_type))
                print(f"{program_number}: {old_type} -> {new_type}")

            # Calculate validation status from issues
            if result.validation_issues:
                validation_status = 'CRITICAL'
            elif result.bore_warnings:
                validation_status = 'BORE_WARNING'
            elif result.dimensional_issues:
                validation_status = 'DIMENSIONAL'
            elif result.validation_warnings:
                validation_status = 'WARNING'
            else:
                validation_status = 'PASS'

            # Update database (including all extraction and validation fields)
            cursor.execute("""
                UPDATE programs
                SET spacer_type = ?,
                    detection_confidence = ?,
                    detection_method = ?,
                    lathe = ?,
                    center_bore = ?,
                    hub_diameter = ?,
                    counter_bore_diameter = ?,
                    counter_bore_depth = ?,
                    cb_from_gcode = ?,
                    ob_from_gcode = ?,
                    validation_status = ?,
                    validation_issues = ?,
                    validation_warnings = ?,
                    bore_warnings = ?,
                    dimensional_issues = ?
                WHERE program_number = ?
            """, (
                result.spacer_type,
                result.detection_confidence,
                result.detection_method,
                result.lathe,
                result.center_bore,
                result.hub_diameter,
                result.counter_bore_diameter,
                result.counter_bore_depth,
                result.cb_from_gcode,
                result.ob_from_gcode,
                validation_status,
                str(result.validation_issues) if result.validation_issues else None,
                str(result.validation_warnings) if result.validation_warnings else None,
                str(result.bore_warnings) if result.bore_warnings else None,
                str(result.dimensional_issues) if result.dimensional_issues else None,
                program_number
            ))

            updated_count += 1

        except Exception as e:
            print(f"ERROR parsing {program_number}: {e}")

    # Commit changes
    conn.commit()
    conn.close()

    print("-" * 80)
    print(f"\nRescan complete!")
    print(f"  Total programs: {len(programs)}")
    print(f"  Updated: {updated_count}")
    print(f"  Type changes: {len(type_changes)}")

    if type_changes:
        print("\nType changes detected:")
        for program_number, old_type, new_type in type_changes:
            print(f"  {program_number}: {old_type} -> {new_type}")

if __name__ == "__main__":
    rescan_database()
