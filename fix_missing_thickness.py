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

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("FIXING MISSING THICKNESS VALUES")
print("=" * 80)
print()

fixed_count = 0
skip_count = 0

for prog_num in problem_files:
    cursor.execute("""
        SELECT program_number, title, thickness, file_path
        FROM programs
        WHERE program_number = ?
    """, (prog_num,))

    result = cursor.fetchone()
    if not result:
        continue

    prog_num_db, title, thickness, file_path = result

    if thickness is not None:
        skip_count += 1
        continue  # Already has thickness

    if not file_path or not os.path.exists(file_path):
        print(f"{prog_num}: File not found")
        continue

    # Read file
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    detected_thickness = None

    # Strategy 1: Check for "SPACER" pattern with decimal before it
    # Example: "13.0 220CB .5 SPACER" -> thickness is 0.5
    spacer_match = re.search(r'(\d+\.?\d*)\s+(?:SPACER|SPC)', title, re.IGNORECASE)
    if spacer_match:
        # Look for decimal number before SPACER
        parts = title[:title.upper().find('SPACER')].strip().split()
        for part in reversed(parts):
            # Check if it's a decimal number less than 10 (likely thickness, not diameter)
            try:
                val = float(part)
                if 0.1 <= val <= 10:
                    detected_thickness = val
                    print(f"{prog_num}: SPACER thickness from title: {detected_thickness}")
                    break
            except:
                continue

    # Strategy 2: For "2PC LUG" files, calculate from drill depth
    if detected_thickness is None and '2PC' in title.upper():
        # Find the maximum drill depth (should be the face drilling depth)
        drill_depths = re.findall(r'Z-([0-9.]+)', content)
        if drill_depths:
            # Convert to floats and find reasonable thickness candidates
            depths = [float(d) for d in drill_depths if 0.1 <= float(d) <= 10]
            if depths:
                # Use the maximum depth that's reasonable for thickness
                detected_thickness = max(depths)
                print(f"{prog_num}: 2PC LUG thickness from drill depth: {detected_thickness}")

    # Strategy 3: Look for thickness in title more aggressively
    if detected_thickness is None:
        # Pattern: number followed by THK, THICK, or standalone decimal
        thick_patterns = [
            r'(\d+\.?\d*)\s*(?:THK|THICK)',
            r'\s(\d\.\d+)\s+(?:HC|ID|OD)',  # Decimal before HC/ID/OD
        ]
        for pattern in thick_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1))
                    if 0.1 <= val <= 10:
                        detected_thickness = val
                        print(f"{prog_num}: Thickness from title pattern: {detected_thickness}")
                        break
                except:
                    continue

    # Update database if we found a thickness
    if detected_thickness is not None:
        cursor.execute("""
            UPDATE programs
            SET thickness = ?,
                thickness_display = ?
            WHERE program_number = ?
        """, (detected_thickness, f"{detected_thickness:.2f}\"", prog_num))
        fixed_count += 1
    else:
        print(f"{prog_num}: Could not detect thickness - Title: {title}")

conn.commit()
conn.close()

print()
print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"Fixed: {fixed_count}")
print(f"Skipped (already had thickness): {skip_count}")
print(f"Could not fix: {len(problem_files) - fixed_count - skip_count}")
