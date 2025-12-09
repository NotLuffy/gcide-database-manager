import sqlite3
import os
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

# Files reported as having thickness detection issues
problem_files = [
    'o10024', 'o10025', 'o10026', 'o10502', 'o10506', 'o10512', 'o10540', 'o10593', 'o10631',
    'o13004', 'o13006', 'o13018', 'o13024', 'o13026', 'o13038', 'o13039', 'o13077', 'o13079',
    'o13082', 'o13090', 'o13091', 'o13092', 'o13121', 'o13122', 'o13124', 'o13125', 'o13126',
    'o13127', 'o13300', 'o13301', 'o13302', 'o13794', 'o13820', 'o13961', 'o50432', 'o50434',
    'o50459', 'o50484', 'o50494', 'o50495', 'o50524', 'o50529', 'o58241'
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("ANALYZING THICKNESS DETECTION ISSUES")
print("=" * 80)
print()

for prog_num in problem_files[:10]:  # Check first 10
    cursor.execute("""
        SELECT program_number, title, thickness, file_path, validation_issues
        FROM programs
        WHERE program_number = ?
    """, (prog_num,))

    result = cursor.fetchone()
    if not result:
        print(f"{prog_num}: NOT FOUND in database")
        continue

    prog_num, title, thickness, file_path, issues = result

    print(f"\n{prog_num}")
    print(f"  Title: {title}")
    print(f"  DB Thickness: {thickness}")
    print(f"  Issues: {issues}")

    if file_path and os.path.exists(file_path):
        # Read file to check for P-codes and drill depths
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Look for P-codes (P9, P10, P11, P12, etc.)
        p_codes = re.findall(r'P(\d+)=([0-9.]+)', content, re.IGNORECASE)
        if p_codes:
            print(f"  P-codes found: {p_codes[:5]}")  # Show first 5

        # Look for drill depth (Z-....)
        drill_depths = re.findall(r'Z-([0-9.]+)', content)
        if drill_depths:
            unique_depths = list(set(drill_depths))[:3]
            print(f"  Drill depths (Z-): {unique_depths}")

        # Look for title line
        title_match = re.search(r'\([^)]*\b([\d.]+)\s*(?:THK|THICK|IN)\b[^)]*\)', content, re.IGNORECASE)
        if title_match:
            print(f"  Title thickness hint: {title_match.group(1)}")
    else:
        print(f"  File not found: {file_path}")

print()
print("=" * 80)
print("PATTERN ANALYSIS")
print("=" * 80)

# Check what all problem files have in common
cursor.execute(f"""
    SELECT program_number, title, thickness, thickness_display, outer_diameter
    FROM programs
    WHERE program_number IN ({','.join('?' * len(problem_files))})
""", problem_files)

results = cursor.fetchall()

no_thickness = []
has_thickness = []

for prog_num, title, thickness, thickness_display, od in results:
    if thickness is None:
        no_thickness.append((prog_num, title, od))
    else:
        has_thickness.append((prog_num, title, thickness, od))

print(f"\nFiles WITHOUT thickness: {len(no_thickness)}")
for prog_num, title, od in no_thickness[:5]:
    print(f"  {prog_num}: {title[:60]} (OD: {od})")

print(f"\nFiles WITH thickness: {len(has_thickness)}")
for prog_num, title, thickness, od in has_thickness[:5]:
    print(f"  {prog_num}: {title[:60]} (Thick: {thickness}, OD: {od})")

conn.close()
