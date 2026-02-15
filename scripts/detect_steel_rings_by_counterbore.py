"""
Detect Steel Rings by Counterbore Evidence
Find standard spacers that might be steel rings based on:
- 8"/8.5"/9.5" round size
- Counterbore diameter matching common steel ring CB values
- Even without STEEL keyword in title
"""

import sqlite3
from improved_gcode_parser import ImprovedGCodeParser

print("=" * 80)
print("STEEL RING DETECTION BY COUNTERBORE EVIDENCE")
print("=" * 80)
print()

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
parser = ImprovedGCodeParser()

# Connect to database
conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

# Get all standard spacers in 8"/8.5"/9.5" sizes
cursor.execute("""
    SELECT program_number, file_path, title, round_size, outer_diameter
    FROM programs
    WHERE spacer_type = 'standard'
    AND (round_size IN (8.0, 8.5, 9.5) OR
         (outer_diameter >= 7.75 AND outer_diameter <= 9.75))
    AND (is_deleted IS NULL OR is_deleted = 0)
    ORDER BY round_size, program_number
""")

candidates = cursor.fetchall()
print(f"Found {len(candidates)} standard spacers in 8\"/8.5\"/9.5\" sizes")
print("Re-parsing to check for counterbore evidence...")
print()

# Track results
reclassified = []
no_counterbore = 0
wrong_cb_value = 0

print("Progress:")
print("-" * 80)

for i, (prog_num, file_path, title, round_size, outer_diam) in enumerate(candidates):
    # Progress indicator
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(candidates)} files processed...", end='\r')

    try:
        # Re-parse file
        result = parser.parse_file(file_path)

        # Check if reclassified as steel_ring
        if result and result.spacer_type == 'steel_ring':
            reclassified.append({
                'program_number': prog_num,
                'title': title,
                'round_size': round_size or outer_diam,
                'cb_diameter': result.counter_bore_diameter,
                'detection_notes': result.detection_notes
            })
        elif result and result.counter_bore_diameter:
            wrong_cb_value += 1
        else:
            no_counterbore += 1

    except Exception as e:
        continue

print()
print()
print("=" * 80)
print("DETECTION COMPLETE")
print("=" * 80)
print()

print(f"Total candidates scanned: {len(candidates)}")
print(f"Reclassified as steel_ring: {len(reclassified)}")
print(f"Has CB but doesn't match steel ring values: {wrong_cb_value}")
print(f"No counterbore detected: {no_counterbore}")
print()

if reclassified:
    print("Files Detected as Steel Rings (by counterbore evidence):")
    print("=" * 80)
    for item in reclassified:
        print(f"\n{item['program_number']} ({item['round_size']:.2f}\")")
        print(f"  Title: {item['title']}")
        print(f"  CB Diameter: {item['cb_diameter']:.1f}mm")
        if item['detection_notes']:
            print(f"  Detection: {item['detection_notes'][-1]}")

    print()
    print("=" * 80)
    print(f"RECOMMENDATION: Update database for {len(reclassified)} files")
    print("=" * 80)
    print()

    response = input(f"Update database to reclassify {len(reclassified)} files as steel_ring? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        print()
        print("Updating database...")

        for item in reclassified:
            cursor.execute("""
                UPDATE programs
                SET spacer_type = 'steel_ring',
                    detection_confidence = 'MEDIUM'
                WHERE program_number = ?
            """, (item['program_number'],))

        conn.commit()

        print(f"SUCCESS: Reclassified {len(reclassified)} files to 'steel_ring' type")
        print()

        # Show final counts
        cursor.execute("""
            SELECT COUNT(*) FROM programs
            WHERE spacer_type = 'steel_ring'
            AND (is_deleted IS NULL OR is_deleted = 0)
        """)
        final_count = cursor.fetchone()[0]

        print("Final Statistics:")
        print("-" * 80)
        print(f"Total steel ring files: {final_count}")
        print(f"  - With STEEL keyword: {final_count - len(reclassified)}")
        print(f"  - Detected by CB evidence: {len(reclassified)}")
        print()

    else:
        print("Cancelled - no changes made")
        print()
else:
    print("No additional steel rings detected by counterbore evidence")
    print("All 8\"/8.5\"/9.5\" files without STEEL keyword are correctly classified as standard")
    print()

conn.close()

print("=" * 80)
print("DONE")
print("=" * 80)
