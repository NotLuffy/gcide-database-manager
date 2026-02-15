"""
Fix Steel Ring Classification
Reclassify files marked as steel_ring that don't match the allowed round sizes (8", 8.5", 9.5")
"""

import sqlite3
import re

print("=" * 80)
print("FIX STEEL RING CLASSIFICATION")
print("=" * 80)
print()

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"

# Connect to database
conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

# Get all steel ring files
cursor.execute("""
    SELECT program_number, title, round_size, outer_diameter, spacer_type
    FROM programs
    WHERE spacer_type = 'steel_ring'
    AND (is_deleted IS NULL OR is_deleted = 0)
    ORDER BY round_size, program_number
""")

all_steel_rings = cursor.fetchall()
print(f"Found {len(all_steel_rings)} files currently classified as steel_ring")
print()

# Define allowed steel ring round sizes
ALLOWED_STEEL_RING_SIZES = [8.0, 8.5, 9.5]

# Categorize files
valid_steel_rings = []
invalid_steel_rings = []
missing_steel_keyword = []

for prog_num, title, round_size, outer_diam, spacer_type in all_steel_rings:
    # Use round_size if available, otherwise use outer_diameter
    size_to_check = round_size if round_size else outer_diam

    # Check for STEEL keyword variations: STEEL, STL, STL-1, HCS-1, HCS-2, etc.
    title_upper = title.upper() if title else ''
    has_steel_keyword = bool(re.search(r'\bSTEEL\b|\bSTL\b|\bSTL-\d\b|\bHCS-\d\b', title_upper))

    # Valid steel ring must have BOTH correct size AND STEEL keyword
    if size_to_check and size_to_check in ALLOWED_STEEL_RING_SIZES:
        if has_steel_keyword:
            valid_steel_rings.append((prog_num, title, size_to_check))
        else:
            # Correct size but missing STEEL keyword
            missing_steel_keyword.append((prog_num, title, size_to_check, 'No STEEL keyword'))
            invalid_steel_rings.append((prog_num, title, size_to_check, 'No STEEL keyword'))
    else:
        # Wrong size
        invalid_steel_rings.append((prog_num, title, size_to_check, 'Wrong size'))

print("Classification Results:")
print("-" * 80)
print(f"Valid steel rings (8\"/8.5\"/9.5\" + STEEL keyword): {len(valid_steel_rings)}")
print(f"Invalid - wrong size: {len([x for x in invalid_steel_rings if x[3] == 'Wrong size'])}")
print(f"Invalid - missing STEEL keyword: {len(missing_steel_keyword)}")
print(f"Total invalid: {len(invalid_steel_rings)}")
print()

# Show breakdown by round size for INVALID classifications
if invalid_steel_rings:
    from collections import defaultdict
    by_size = defaultdict(int)
    for _, _, size, _ in invalid_steel_rings:
        if size:
            by_size[round(size, 2)] += 1
        else:
            by_size['Unknown'] += 1

    print("Invalid Steel Ring Files by Round Size:")
    print("-" * 80)
    for size in sorted(by_size.keys(), key=lambda x: (isinstance(x, str), x)):
        size_str = f"{size:.2f}\"" if isinstance(size, float) else size
        print(f"  {size_str}: {by_size[size]} files")
    print()

# Show samples
if invalid_steel_rings:
    print("Sample Invalid Steel Ring Files (to be reclassified):")
    print("-" * 80)
    for prog_num, title, size, reason in invalid_steel_rings[:20]:
        size_str = f"{size:.2f}\"" if size else "Unknown"
        print(f"  {prog_num} ({size_str}) [{reason}]: {title[:50]}")
    if len(invalid_steel_rings) > 20:
        print(f"  ... and {len(invalid_steel_rings) - 20} more")
    print()

# Reclassify invalid files
if invalid_steel_rings:
    response = input(f"Reclassify {len(invalid_steel_rings)} files from steel_ring to standard? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        print()
        print("Reclassifying files...")

        for prog_num, _, _, _ in invalid_steel_rings:
            cursor.execute("""
                UPDATE programs
                SET spacer_type = 'standard',
                    detection_confidence = 'HIGH'
                WHERE program_number = ?
            """, (prog_num,))

        conn.commit()

        print(f"SUCCESS: Reclassified {len(invalid_steel_rings)} files to 'standard' type")
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
        print(f"Steel ring files remaining: {final_count}")
        print(f"Standard spacers (reclassified): {len(invalid_steel_rings)}")
        print()

        # Show breakdown of valid steel rings by round size
        cursor.execute("""
            SELECT round_size, COUNT(*) as count
            FROM programs
            WHERE spacer_type = 'steel_ring'
            AND (is_deleted IS NULL OR is_deleted = 0)
            GROUP BY round_size
            ORDER BY round_size
        """)

        print("Valid Steel Ring Files by Round Size:")
        print("-" * 80)
        for row in cursor.fetchall():
            size, count = row
            size_str = f"{size:.2f}\"" if size else "Unknown"
            print(f"  {size_str}: {count} files")
        print()

    else:
        print("Cancelled - no changes made")
        print()
else:
    print("SUCCESS: All steel ring files are correctly classified!")
    print()

    # Show valid steel ring breakdown
    cursor.execute("""
        SELECT round_size, COUNT(*) as count
        FROM programs
        WHERE spacer_type = 'steel_ring'
        AND (is_deleted IS NULL OR is_deleted = 0)
        GROUP BY round_size
        ORDER BY round_size
    """)

    print("Valid Steel Ring Files by Round Size:")
    print("-" * 80)
    for row in cursor.fetchall():
        size, count = row
        size_str = f"{size:.2f}\"" if size else "Unknown"
        print(f"  {size_str}: {count} files")
    print()

conn.close()

print("=" * 80)
print("DONE")
print("=" * 80)
