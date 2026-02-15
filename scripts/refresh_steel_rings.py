"""
Refresh Steel Ring Database
Re-parse all steel ring files to extract counterbore diameters from Side 2
"""

import sqlite3
import os
from improved_gcode_parser import ImprovedGCodeParser

print("=" * 80)
print("REFRESH STEEL RING DATABASE")
print("=" * 80)
print()

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
parser = ImprovedGCodeParser()

# Connect to database
conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

# Get all steel ring files
cursor.execute("""
    SELECT program_number, file_path, title
    FROM programs
    WHERE spacer_type = 'steel_ring'
    AND (is_deleted IS NULL OR is_deleted = 0)
    ORDER BY program_number
""")

steel_rings = cursor.fetchall()
print(f"Found {len(steel_rings)} steel ring files to refresh")
print()

# Track results
updated_count = 0
failed_count = 0
cb_extracted_count = 0
cb_before = 0
cb_after = 0
errors = []

print("Progress:")
print("-" * 80)

for i, (prog_num, file_path, title) in enumerate(steel_rings):
    # Progress indicator
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(steel_rings)} files processed...", end='\r')

    try:
        # Check if file exists
        if not os.path.exists(file_path):
            failed_count += 1
            if len(errors) < 10:
                errors.append(f"{prog_num}: File not found - {file_path}")
            continue

        # Get current counterbore value
        cursor.execute("""
            SELECT counter_bore_diameter
            FROM programs
            WHERE program_number = ?
        """, (prog_num,))
        current_cb = cursor.fetchone()
        if current_cb and current_cb[0]:
            cb_before += 1

        # Re-parse file
        result = parser.parse_file(file_path)

        # Update database with new dimensions
        cursor.execute("""
            UPDATE programs
            SET counter_bore_diameter = ?,
                counter_bore_depth = ?
            WHERE program_number = ?
        """, (
            result.counter_bore_diameter,
            result.counter_bore_depth,
            prog_num
        ))

        updated_count += 1

        # Track if counterbore was extracted
        if result.counter_bore_diameter:
            cb_extracted_count += 1
            cb_after += 1

    except Exception as e:
        failed_count += 1
        if len(errors) < 10:
            errors.append(f"{prog_num}: {type(e).__name__} - {str(e)}")
        continue

# Commit changes
conn.commit()

print()
print()
print("=" * 80)
print("REFRESH COMPLETE")
print("=" * 80)
print()
print(f"Total steel ring files: {len(steel_rings)}")
print(f"Successfully updated: {updated_count}")
print(f"Failed/skipped: {failed_count}")
print()

if errors:
    print("Sample Errors (first 10):")
    print("-" * 80)
    for err in errors:
        print(f"  {err}")
    print()

print("Counterbore Diameter Extraction:")
print(f"  Before refresh: {cb_before} files had counterbore data")
print(f"  After refresh: {cb_after} files have counterbore data")
print(f"  New extractions: {cb_extracted_count - cb_before}")
print()

# Show sample of files with newly extracted counterbore
cursor.execute("""
    SELECT program_number, title, counter_bore_diameter, center_bore
    FROM programs
    WHERE spacer_type = 'steel_ring'
    AND counter_bore_diameter IS NOT NULL
    AND (is_deleted IS NULL OR is_deleted = 0)
    ORDER BY program_number
    LIMIT 15
""")

print("Sample Steel Ring Files with Counterbore Data:")
print("-" * 80)
for row in cursor.fetchall():
    prog_num, title, cb_diam, center_bore = row
    cb_str = f"{cb_diam:.1f}mm" if cb_diam else "N/A"
    center_str = f"{center_bore:.1f}mm" if center_bore else "N/A"
    print(f"  {prog_num}: {title}")
    print(f"    Center Bore: {center_str} | Counterbore: {cb_str}")
    print()

# Statistics by round size
print("=" * 80)
print("COUNTERBORE EXTRACTION BY ROUND SIZE")
print("=" * 80)
print()

cursor.execute("""
    SELECT round_size,
           COUNT(*) as total,
           SUM(CASE WHEN counter_bore_diameter IS NOT NULL THEN 1 ELSE 0 END) as with_cb
    FROM programs
    WHERE spacer_type = 'steel_ring'
    AND (is_deleted IS NULL OR is_deleted = 0)
    GROUP BY round_size
    ORDER BY round_size
""")

print(f"{'Round Size':<15} {'Total':<10} {'With CB':<10} {'%':<10}")
print("-" * 50)
for row in cursor.fetchall():
    round_size, total, with_cb = row
    pct = (with_cb / total * 100) if total > 0 else 0
    size_str = f"{round_size:.2f}\"" if round_size else "Unknown"
    print(f"{size_str:<15} {total:<10} {with_cb:<10} {pct:.1f}%")

conn.close()

print()
print("=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print()

if cb_after < len(steel_rings) * 0.8:
    print("WARNING: Less than 80% of steel ring files have counterbore data extracted")
    print("  - Check if Side 2 operations are missing in some files")
    print("  - Verify FLIP PART comments are present")
    print("  - Review parser logic for Side 2 detection")
else:
    print("SUCCESS: Counterbore data successfully extracted from steel ring files")
    print("  - Database is ready for LPN tracker export")
    print("  - Google Sheets export will include counterbore dimensions")

print()
