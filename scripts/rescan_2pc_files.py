#!/usr/bin/env python3
"""Rescan all 2PC files to update hub_diameter and counter_bore_diameter with fixed parser"""

import sqlite3
import sys
import os
from improved_gcode_parser import ImprovedGCodeParser

def rescan_2pc_files():
    """Rescan all 2PC files and update database"""

    db_path = 'gcode_database.db'
    parser = ImprovedGCodeParser()

    # Get all 2PC files
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT program_number, file_path, spacer_type
        FROM programs
        WHERE spacer_type LIKE '%2PC%'
        AND file_path IS NOT NULL
        ORDER BY program_number
    ''')

    files_to_rescan = cursor.fetchall()
    total = len(files_to_rescan)

    print(f"Rescanning {total} 2PC files...")
    print("=" * 70)

    updated = 0
    errors = 0
    skipped = 0

    for i, (prog_num, file_path, spacer_type) in enumerate(files_to_rescan, 1):
        # Progress indicator
        if i % 50 == 0 or i == total:
            print(f"Progress: {i}/{total} ({100*i//total}%)")

        # Check if file exists
        if not os.path.exists(file_path):
            skipped += 1
            continue

        try:
            # Parse file
            result = parser.parse_file(file_path)

            # Update database with new values
            cursor.execute('''
                UPDATE programs
                SET hub_diameter = ?,
                    hub_height = ?,
                    counter_bore_diameter = ?,
                    counter_bore_depth = ?
                WHERE program_number = ?
            ''', (
                result.hub_diameter,
                result.hub_height,
                result.counter_bore_diameter,
                result.counter_bore_depth,
                prog_num
            ))

            updated += 1

        except Exception as e:
            print(f"  ERROR: {prog_num} - {e}")
            errors += 1

    # Commit changes
    conn.commit()
    conn.close()

    print()
    print("=" * 70)
    print(f"Rescan complete!")
    print(f"  Updated: {updated}")
    print(f"  Skipped (file not found): {skipped}")
    print(f"  Errors: {errors}")
    print()

    # Show some examples of updated values
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Sample of updated values:")
    print("-" * 70)
    cursor.execute('''
        SELECT program_number, spacer_type, hub_diameter, hub_height,
               counter_bore_diameter, counter_bore_depth
        FROM programs
        WHERE spacer_type LIKE '%2PC%'
        AND (hub_diameter IS NOT NULL OR counter_bore_diameter IS NOT NULL)
        ORDER BY program_number
        LIMIT 10
    ''')

    print(f"{'Program':<12} {'Type':<12} {'Hub_D':<10} {'Hub_H':<8} {'CB_D':<10} {'CB_Depth':<8}")
    for row in cursor.fetchall():
        hub_d = f"{row[2]:.1f}mm" if row[2] else "-"
        hub_h = f"{row[3]:.2f}\"" if row[3] else "-"
        cb_d = f"{row[4]:.1f}mm" if row[4] else "-"
        cb_depth = f"{row[5]:.2f}\"" if row[5] else "-"
        print(f"{row[0]:<12} {row[1]:<12} {hub_d:<10} {hub_h:<8} {cb_d:<10} {cb_depth:<8}")

    conn.close()

if __name__ == "__main__":
    rescan_2pc_files()
