#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Program Number Registry - Phase 2
This will generate all 97,001 program numbers and mark existing ones as IN_USE
"""

import sqlite3
import os
import sys
import time
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Path to database
db_path = os.path.join(os.path.dirname(__file__), 'gcode_database.db')

print("=" * 80)
print("POPULATE PROGRAM NUMBER REGISTRY - PHASE 2")
print("=" * 80)
print()

# Check if database exists
if not os.path.exists(db_path):
    print(f"ERROR: Database not found at: {db_path}")
    sys.exit(1)

print(f"Database: {db_path}")
print()

# Import functions from main module
sys.path.insert(0, os.path.dirname(__file__))

try:
    # We'll implement the logic directly here for standalone operation
    def get_round_size_ranges():
        return {
            10.25: (10000, 12999, "10.25 & 10.50"),
            10.50: (10000, 12999, "10.25 & 10.50"),
            13.0:  (13000, 13999, "13.0"),
            5.75:  (50000, 59999, "5.75"),
            6.0:   (60000, 62499, "6.0"),
            6.25:  (62500, 64999, "6.25"),
            6.5:   (65000, 69999, "6.5"),
            7.0:   (70000, 74999, "7.0"),
            7.5:   (75000, 79000, "7.5"),
            8.0:   (80000, 84999, "8.0"),
            8.5:   (85000, 89999, "8.5"),
            9.5:   (90000, 99999, "9.5"),
            0.0:   (1000, 9999, "Free Range 1"),
            -1.0:  (14000, 49999, "Free Range 2")
        }

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all round size ranges
    ranges = get_round_size_ranges()

    print("Step 1: Clearing existing registry...")
    cursor.execute("DELETE FROM program_number_registry")
    print("  Registry cleared")
    print()

    print("Step 2: Loading existing programs from database...")
    cursor.execute("SELECT program_number, file_path FROM programs")
    existing_programs = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"  Found {len(existing_programs):,} existing programs")
    print()

    # Track statistics
    stats = {
        'total_generated': 0,
        'in_use': 0,
        'available': 0,
        'duplicates': 0,
        'by_range': {}
    }

    start_time = time.time()

    print("Step 3: Generating all 97,001 program numbers...")
    print("-" * 80)

    # Generate all program numbers for each range
    # Track which ranges we've already processed to avoid duplicates
    processed_ranges = set()

    for round_size, (range_start, range_end, range_name) in ranges.items():
        # Skip if we've already processed this range
        range_key = (range_start, range_end)
        if range_key in processed_ranges:
            continue
        processed_ranges.add(range_key)

        range_stats = {
            'total': 0,
            'in_use': 0,
            'available': 0
        }

        print(f"  {range_name:20s} (o{range_start:05d}-o{range_end:05d}): ", end='', flush=True)

        for prog_num in range(range_start, range_end + 1):
            program_number = f"o{prog_num}"

            # Check if this program exists in database
            if program_number in existing_programs:
                status = 'IN_USE'
                file_path = existing_programs[program_number]
                stats['in_use'] += 1
                range_stats['in_use'] += 1
            else:
                status = 'AVAILABLE'
                file_path = None
                stats['available'] += 1
                range_stats['available'] += 1

            # Insert into registry
            cursor.execute("""
                INSERT INTO program_number_registry
                (program_number, round_size, range_start, range_end, status, file_path, last_checked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (program_number, round_size, range_start, range_end, status, file_path,
                  datetime.now().isoformat()))

            stats['total_generated'] += 1
            range_stats['total'] += 1

        stats['by_range'][range_name] = range_stats

        # Print range summary
        usage_pct = (range_stats['in_use'] / range_stats['total'] * 100) if range_stats['total'] > 0 else 0
        print(f"{range_stats['in_use']:,}/{range_stats['total']:,} in use ({usage_pct:.1f}%)")

    print()

    print("Step 4: Checking for duplicate program numbers...")
    cursor.execute("""
        SELECT program_number, COUNT(*) as count
        FROM programs
        GROUP BY program_number
        HAVING count > 1
    """)

    duplicate_programs = cursor.fetchall()
    for prog_num, count in duplicate_programs:
        cursor.execute("""
            UPDATE program_number_registry
            SET duplicate_count = ?,
                notes = 'WARNING: Multiple files with this program number'
            WHERE program_number = ?
        """, (count, prog_num))
        stats['duplicates'] += 1

    if stats['duplicates'] > 0:
        print(f"  Found {stats['duplicates']} duplicate program numbers")
    else:
        print("  No duplicates found")

    print()

    print("Step 5: Committing changes to database...")
    conn.commit()
    conn.close()

    elapsed = time.time() - start_time

    # Print results
    print()
    print("=" * 80)
    print("REGISTRY POPULATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Total Program Numbers Generated: {stats['total_generated']:,}")
    print(f"Time Elapsed: {elapsed:.1f} seconds ({stats['total_generated']/elapsed:.0f} numbers/sec)")
    print()
    print("Status Breakdown:")
    print(f"  - IN USE: {stats['in_use']:,} ({stats['in_use']/stats['total_generated']*100:.2f}%)")
    print(f"  - AVAILABLE: {stats['available']:,} ({stats['available']/stats['total_generated']*100:.2f}%)")
    print(f"  - Duplicates: {stats['duplicates']}")
    print()

    print("Range Summary:")
    print("-" * 80)
    for range_name, range_stats in stats['by_range'].items():
        usage_pct = (range_stats['in_use'] / range_stats['total'] * 100) if range_stats['total'] > 0 else 0
        print(f"  {range_name:20s}: {range_stats['in_use']:5,}/{range_stats['total']:5,} in use ({usage_pct:5.1f}%) - {range_stats['available']:5,} available")

    print()
    print("Next steps:")
    print("1. Use find_next_available_number() to get available numbers for new programs")
    print("2. Review out-of-range programs (1,225 programs identified in Phase 1)")
    print("3. Implement Type 1 duplicate resolution (name conflicts)")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
