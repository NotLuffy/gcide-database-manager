import sqlite3
import os
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

# Files that still need fixing
remaining_files = {
    'o13079': 4.00,  # "13.0 221CB 4.00 PRESSPLATE" - 4.00 is the thickness
    'o13124': 0.59,  # "13.0 220CB 15MM SPACER" - 15mm = 0.59 inches
    'o13126': 0.67,  # "13.0 220CB 17MM SPACER" - 17mm = 0.67 inches
    'o13127': 0.87,  # "13.0 220CB 22MM SPACER" - 22mm = 0.87 inches
    'o50459': 1.25,  # "5.75IN DIA 70.3/70.3 1.25IN HC" - 1.25IN is the thickness
    'o50524': None,  # Empty title - need to check file
    'o50529': 0.39,  # "5.75IN DIA 64.1/72.56 10MM -HC" - 10mm = 0.39 inches
    'o58241': 0.75,  # "5.75IN DIA 56.1/56.1 .75--HC" - 0.75 is the thickness
}

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("FIXING REMAINING THICKNESS VALUES")
print("=" * 80)
print()

fixed_count = 0

for prog_num, manual_thickness in remaining_files.items():
    if manual_thickness is None:
        # Check file for o50524
        cursor.execute("""
            SELECT file_path, title
            FROM programs
            WHERE program_number = ?
        """, (prog_num,))
        result = cursor.fetchone()
        if result:
            file_path, title = result
            print(f"{prog_num}: Empty title, file: {file_path}")
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # Try to find thickness from drill depth
                drill_depths = re.findall(r'Z-([0-9.]+)', content)
                if drill_depths:
                    depths = [float(d) for d in drill_depths if 0.1 <= float(d) <= 10]
                    if depths:
                        manual_thickness = max(depths)
                        print(f"  -> Detected from drill depth: {manual_thickness}")
        continue

    # Update thickness
    cursor.execute("""
        UPDATE programs
        SET thickness = ?,
            thickness_display = ?
        WHERE program_number = ?
    """, (manual_thickness, f"{manual_thickness:.2f}\"", prog_num))

    cursor.execute("SELECT title FROM programs WHERE program_number = ?", (prog_num,))
    title = cursor.fetchone()[0]

    print(f"{prog_num}: Set thickness to {manual_thickness}\" - {title}")
    fixed_count += 1

# Handle o50524 separately if we found a value
if remaining_files['o50524'] is not None:
    cursor.execute("""
        UPDATE programs
        SET thickness = ?,
            thickness_display = ?
        WHERE program_number = ?
    """, (remaining_files['o50524'], f"{remaining_files['o50524']:.2f}\"", 'o50524'))
    fixed_count += 1

conn.commit()
conn.close()

print()
print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"Fixed: {fixed_count} files")
