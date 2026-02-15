"""
Import o81300.nc into the database.
"""

import sys
import os

# Add the current directory to path to import from gcode_database_manager
sys.path.insert(0, r"L:\My Drive\Home\File organizer")

from improved_gcode_parser import ImprovedGCodeParser
import sqlite3
from datetime import datetime
import json

db_path = r"L:\My Drive\Home\File organizer\gcode_database.db"
file_path = r"L:\My Drive\Home\File organizer\repository\o81300.nc"

print("=" * 80)
print("IMPORTING o81300.nc INTO DATABASE")
print("=" * 80)
print()

# Check if file exists
if not os.path.exists(file_path):
    print(f"[ERROR] File not found: {file_path}")
    exit(1)

print(f"File: {file_path}")
print(f"Size: {os.path.getsize(file_path)} bytes")
print()

# Parse the file
print("Parsing file...")
parser = ImprovedGCodeParser()
result = parser.parse_file(file_path)

if not result:
    print("[ERROR] Failed to parse file")
    exit(1)

print(f"[OK] Parsed successfully")
print(f"  Program: {result.program_number}")
print(f"  Title: {result.title}")
print()

# Insert into database
print("Inserting into database...")

try:
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    # Determine validation status
    validation_status = "PASS"
    if result.crash_issues:
        validation_status = "CRASH_RISK"
    elif result.validation_issues:
        validation_status = "CRITICAL"
    elif result.tool_home_status == "CRITICAL":
        validation_status = "TOOL_HOME_CRITICAL"
    elif result.crash_warnings:
        validation_status = "CRASH_WARNING"
    elif result.bore_warnings:
        validation_status = "BORE_WARNING"
    elif result.tool_home_status == "WARNING":
        validation_status = "TOOL_HOME_WARNING"
    elif result.dimensional_issues:
        validation_status = "DIMENSIONAL"
    elif result.validation_warnings:
        validation_status = "WARNING"

    cursor.execute("""
        INSERT INTO programs (
            program_number, title, spacer_type, outer_diameter, thickness, thickness_display,
            center_bore, hub_height, hub_diameter, counter_bore_diameter, counter_bore_depth,
            paired_program, material, notes, date_created, last_modified, file_path,
            detection_confidence, detection_method, validation_status, validation_issues,
            validation_warnings, cb_from_gcode, ob_from_gcode, bore_warnings, dimensional_issues,
            lathe, tool_home_status, tool_home_issues,
            hub_height_display, counter_bore_depth_display,
            feasibility_status, feasibility_issues, feasibility_warnings,
            crash_issues, crash_warnings, date_imported,
            is_deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.program_number,
        result.title,
        result.spacer_type,
        result.outer_diameter,
        result.thickness,
        result.thickness_display,
        result.center_bore,
        result.hub_height,
        result.hub_diameter,
        result.counter_bore_diameter,
        result.counter_bore_depth,
        None,  # paired_program
        result.material,
        None,  # notes
        result.date_created,
        result.last_modified,
        result.file_path,
        result.detection_confidence,
        result.detection_method,
        validation_status,
        json.dumps(result.validation_issues) if result.validation_issues else None,
        json.dumps(result.validation_warnings) if result.validation_warnings else None,
        result.cb_from_gcode,
        result.ob_from_gcode,
        json.dumps(result.bore_warnings) if result.bore_warnings else None,
        json.dumps(result.dimensional_issues) if result.dimensional_issues else None,
        result.lathe,
        result.tool_home_status,
        json.dumps(result.tool_home_issues) if result.tool_home_issues else None,
        None,  # hub_height_display
        None,  # counter_bore_depth_display
        None,  # feasibility_status
        None,  # feasibility_issues
        None,  # feasibility_warnings
        json.dumps(result.crash_issues) if isinstance(result.crash_issues, list) else result.crash_issues,
        json.dumps(result.crash_warnings) if isinstance(result.crash_warnings, list) else result.crash_warnings,
        datetime.now().isoformat(),
        0  # is_deleted
    ))

    conn.commit()
    conn.close()

    print(f"[OK] Successfully imported {result.program_number} into database")
    print()
    print("=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print()
    print("o81300 is now in the database.")
    print("Refresh the database manager to see it.")

except Exception as e:
    print(f"[ERROR] Failed to insert into database: {e}")
    import traceback
    traceback.print_exc()
