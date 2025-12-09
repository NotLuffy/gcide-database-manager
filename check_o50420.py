import sqlite3
import os
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING o50420 DRILL DEPTH DETECTION")
print("=" * 80)
print()

# Get o50420 details
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, file_path, spacer_type
    FROM programs
    WHERE program_number = 'o50420'
""")

result = cursor.fetchone()

if result:
    prog_num, title, thickness, thickness_display, file_path, spacer_type = result

    print(f"Program Number: {prog_num}")
    print(f"Title: {title}")
    print(f"Spacer Type: {spacer_type}")
    print(f"Thickness (stored): {thickness}")
    print(f"Thickness Display: {thickness_display}")
    print()

    if file_path and os.path.exists(file_path):
        print("=" * 80)
        print("G-CODE ANALYSIS")
        print("=" * 80)
        print()

        # Read file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Find all Z-depth patterns
        print("Z-depth patterns found in file:")
        print("-" * 80)

        z_depths = []
        for i, line in enumerate(lines[:100], 1):  # Check first 100 lines
            # Find all Z- patterns
            z_matches = re.findall(r'Z-([0-9.]+)', line, re.IGNORECASE)
            if z_matches:
                for z_val in z_matches:
                    z_depths.append(float(z_val))
                    print(f"Line {i:3d}: {line.strip()[:80]}")

        if z_depths:
            print()
            print("=" * 80)
            print("DEPTH ANALYSIS")
            print("=" * 80)
            print(f"All Z-depths found: {sorted(set(z_depths))}")
            print(f"Maximum Z-depth: {max(z_depths):.3f}")
            print(f"Minimum Z-depth: {min(z_depths):.3f}")
            print()
            print("Expected thickness from title:")
            print(f"  Title says: {title}")
            print()
            print("Current database:")
            print(f"  Thickness: {thickness:.3f}\" ({thickness_display})")
            print()
            print("ISSUE:")
            if max(z_depths) != thickness:
                print(f"  Database shows {thickness:.3f}\" but file has Z-{max(z_depths):.3f}")
                print(f"  Parser may have extracted wrong Z-depth value")
    else:
        print(f"File not found: {file_path}")
else:
    print("o50420 not found in database")

conn.close()

print()
print("=" * 80)
print("PATTERN PARSING ISSUE")
print("=" * 80)
print()
print("The pattern 'Z-2.4Q1.1' contains two numbers:")
print("  Z-2.4   = Drill depth (what we want)")
print("  Q1.1    = Peck depth (should be ignored)")
print()
print("The regex 'Z-([0-9.]+)' may be too greedy and matching")
print("'Z-2.4Q1.1' as a single value instead of just 'Z-2.4'")
