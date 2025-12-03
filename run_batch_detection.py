#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Batch Round Size Detection
This will detect and update round sizes for all programs in the database
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
print("BATCH ROUND SIZE DETECTION")
print("=" * 80)
print()

# Import detection functions from main module
sys.path.insert(0, os.path.dirname(__file__))

try:
    # We'll implement the detection logic directly here for standalone operation
    import re

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
        }

    def detect_round_size_from_title(title):
        if not title:
            return None
        patterns = [
            r'(\d+\.?\d*)\s*(?:OD|od|rnd|RND|round|IN\s+DIA)',
            r'(\d+)\.(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    if len(match.groups()) == 2:
                        round_size = float(f"{match.group(1)}.{match.group(2)}")
                    else:
                        round_size = float(match.group(1))
                    if 5.0 <= round_size <= 15.0:
                        return round_size
                except:
                    continue
        return None

    def get_range_for_round_size(round_size):
        ranges = get_round_size_ranges()

        # Exact match
        if round_size in ranges:
            return ranges[round_size][:2]

        # Only consider positive round sizes
        positive_ranges = {k: v for k, v in ranges.items() if k > 0}
        if not positive_ranges:
            return None

        closest_size = min(positive_ranges.keys(), key=lambda x: abs(x - round_size))

        # Tight tolerance for very close matches (6.24 → 6.25)
        tight_tolerance = 0.1
        if abs(closest_size - round_size) <= tight_tolerance:
            return ranges[closest_size][:2]

        # Smart fallback for orphaned round sizes (like 5.0, 5.5, etc.)
        # Use a more generous tolerance to find the nearest logical range
        smart_fallback_tolerance = 1.0
        if abs(closest_size - round_size) <= smart_fallback_tolerance:
            return ranges[closest_size][:2]

        # If still no match, find the nearest range by distance
        # Example: 5.0" → use 5.75" range (smallest available)
        # Example: 11.0" → use 10.25/10.50" range (nearest)
        if round_size > 0:
            nearest = min(positive_ranges.items(),
                         key=lambda x: abs(x[0] - round_size))
            return nearest[1][:2]

        return None

    def is_in_correct_range(program_number, round_size):
        if not round_size:
            return True
        try:
            prog_num = int(str(program_number).replace('o', '').replace('O', ''))
        except:
            return False
        range_info = get_range_for_round_size(round_size)
        if not range_info:
            return False
        range_start, range_end = range_info
        return range_start <= prog_num <= range_end

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all programs
    print("Fetching all programs...")
    cursor.execute("SELECT program_number, title, ob_from_gcode, outer_diameter FROM programs")
    programs = cursor.fetchall()

    print(f"Found {len(programs):,} programs to process")
    print()

    # Process each program
    results = {
        'processed': 0,
        'detected_title': 0,
        'detected_gcode': 0,
        'detected_dimension': 0,
        'manual_needed': 0,
        'in_correct_range': 0,
        'out_of_range': 0,
        'errors': 0
    }

    start_time = time.time()

    print("Processing programs...")
    print("-" * 80)

    for i, (program_number, title, ob_from_gcode, outer_diameter) in enumerate(programs):
        try:
            # Detect round size using priority order
            round_size = None
            confidence = 'NONE'
            source = 'MANUAL'

            # Method 1: Title
            if title:
                title_match = detect_round_size_from_title(title)
                if title_match:
                    round_size = title_match
                    confidence = 'HIGH'
                    source = 'TITLE'
                    results['detected_title'] += 1

            # Method 2: G-code OB
            if not round_size and ob_from_gcode:
                if 5.0 <= ob_from_gcode <= 15.0:
                    round_size = ob_from_gcode
                    confidence = 'HIGH'
                    source = 'GCODE'
                    results['detected_gcode'] += 1

            # Method 3: Outer Diameter
            if not round_size and outer_diameter:
                if 5.0 <= outer_diameter <= 15.0:
                    round_size = outer_diameter
                    confidence = 'MEDIUM'
                    source = 'DIMENSION'
                    results['detected_dimension'] += 1

            # Check if in correct range
            in_correct_range = 1 if is_in_correct_range(program_number, round_size) else 0

            if round_size:
                if in_correct_range:
                    results['in_correct_range'] += 1
                else:
                    results['out_of_range'] += 1
            else:
                results['manual_needed'] += 1

            # Update database
            cursor.execute("""
                UPDATE programs
                SET round_size = ?,
                    round_size_confidence = ?,
                    round_size_source = ?,
                    in_correct_range = ?
                WHERE program_number = ?
            """, (round_size, confidence, source, in_correct_range, program_number))

            results['processed'] += 1

            # Progress indicator
            if (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining = (len(programs) - (i + 1)) / rate
                print(f"Progress: {i+1:,}/{len(programs):,} ({(i+1)/len(programs)*100:.1f}%) - ETA: {remaining:.0f}s")

        except Exception as e:
            results['errors'] += 1
            print(f"Error processing {program_number}: {e}")

    # Commit changes
    print()
    print("Committing changes to database...")
    conn.commit()
    conn.close()

    elapsed = time.time() - start_time

    # Print results
    print()
    print("=" * 80)
    print("BATCH DETECTION COMPLETE")
    print("=" * 80)
    print()
    print(f"Total Processed: {results['processed']:,}")
    print(f"Time Elapsed: {elapsed:.1f} seconds ({results['processed']/elapsed:.0f} programs/sec)")
    print()
    print("Detection Sources:")
    print(f"  - From Title: {results['detected_title']:,} ({results['detected_title']/results['processed']*100:.1f}%)")
    print(f"  - From G-code: {results['detected_gcode']:,} ({results['detected_gcode']/results['processed']*100:.1f}%)")
    print(f"  - From Dimension: {results['detected_dimension']:,} ({results['detected_dimension']/results['processed']*100:.1f}%)")
    print(f"  - Manual Needed: {results['manual_needed']:,} ({results['manual_needed']/results['processed']*100:.1f}%)")
    print()
    print("Range Validation:")
    print(f"  - In Correct Range: {results['in_correct_range']:,} ({results['in_correct_range']/results['processed']*100:.1f}%)")
    print(f"  - Out of Range: {results['out_of_range']:,} ({results['out_of_range']/results['processed']*100:.1f}%)")
    print()
    print(f"Errors: {results['errors']}")
    print()

    # Query programs out of range
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT program_number, round_size, round_size_source
        FROM programs
        WHERE in_correct_range = 0
        AND round_size IS NOT NULL
        LIMIT 20
    """)

    out_of_range_programs = cursor.fetchall()

    if out_of_range_programs:
        print("Sample Programs in WRONG RANGE:")
        print("-" * 80)
        for prog_num, round_size, source in out_of_range_programs:
            correct_range = get_range_for_round_size(round_size)
            if correct_range:
                print(f"  {prog_num}: Round Size {round_size} (from {source})")
                print(f"    → Should be in range: {correct_range[0]}-{correct_range[1]}")
        print()
        print(f"Total out of range: {results['out_of_range']:,}")
        print("These programs need to be renamed to match their round size ranges")

    conn.close()

    print()
    print("Next steps:")
    print("1. Review programs out of range (see above)")
    print("2. Continue to Phase 2: Populate program number registry")
    print("3. Implement Type 1 duplicate resolution (name conflicts)")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
