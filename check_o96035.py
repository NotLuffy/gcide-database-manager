import sqlite3
import sys
import os

# Add the current directory to path to import the parser
sys.path.insert(0, os.path.dirname(__file__))

from improved_gcode_parser import ImprovedGCodeParser

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

# Check o96035
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, hub_height, file_path
    FROM programs
    WHERE program_number = 'o96035'
""")

result = cursor.fetchone()

if result:
    prog_num, title, old_thickness, old_thickness_display, old_hub_height, file_path = result

    print("=" * 80)
    print("CHECKING o96035")
    print("=" * 80)
    print(f"Title: {title}")
    print(f"OLD: Thickness={old_thickness:.2f}, Hub Height={old_hub_height:.2f}")
    print()

    # Re-parse with updated parser
    if file_path and os.path.exists(file_path):
        parser = ImprovedGCodeParser()
        parse_result = parser.parse_file(file_path)

        if parse_result:
            print(f"NEW: Thickness={parse_result.thickness:.2f}, Hub Height={parse_result.hub_height:.2f}")
            print()

            # Update database
            cursor.execute("""
                UPDATE programs
                SET thickness = ?,
                    thickness_display = ?,
                    hub_height = ?
                WHERE program_number = ?
            """, (parse_result.thickness, parse_result.thickness_display, parse_result.hub_height, prog_num))

            conn.commit()
            print("[OK] Fixed o96035")
        else:
            print("[ERROR] Failed to parse file")
    else:
        print(f"[ERROR] File not found: {file_path}")
else:
    print("o96035 not found in database")

conn.close()
