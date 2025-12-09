import sqlite3
import os
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

# Files with MM thickness that should be displayed as MM, not converted to inches
mm_thickness_files = {
    'o13124': 15,   # "13.0 220CB 15MM SPACER"
    'o13126': 17,   # "13.0 220CB 17MM SPACER"
    'o13127': 22,   # "13.0 220CB 22MM SPACER"
    'o50529': 10,   # "5.75IN DIA 64.1/72.56 10MM -HC"
}

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("FIXING MM THICKNESS DISPLAY")
print("=" * 80)
print()

fixed_count = 0

for prog_num, mm_value in mm_thickness_files.items():
    # Set thickness_display to show MM format
    # Keep thickness in inches for calculations (mm / 25.4)
    thickness_inches = mm_value / 25.4
    thickness_display = f"{mm_value}MM"

    cursor.execute("""
        UPDATE programs
        SET thickness = ?,
            thickness_display = ?
        WHERE program_number = ?
    """, (thickness_inches, thickness_display, prog_num))

    cursor.execute("SELECT title FROM programs WHERE program_number = ?", (prog_num,))
    result = cursor.fetchone()
    title = result[0] if result else "Unknown"

    print(f"{prog_num}: Set to {thickness_display} ({thickness_inches:.3f}\" internally) - {title}")
    fixed_count += 1

conn.commit()
conn.close()

print()
print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"Fixed: {fixed_count} files")
print()
print("These files will now display as MM in the table (e.g., '15MM')")
print("but are stored as inches internally for calculations.")
