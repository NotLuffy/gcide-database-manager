"""
Steel Ring Size Analysis
Scans all steel ring files to learn common counterbore diameters and depths
This data can be used to improve steel ring detection
"""

import os
import glob
import re
from improved_gcode_parser import ImprovedGCodeParser
from collections import defaultdict

parser = ImprovedGCodeParser()

print("=" * 80)
print("STEEL RING SIZE ANALYSIS")
print("=" * 80)
print()

repo_path = r"l:\My Drive\Home\File organizer\repository"

# Get all G-code files
all_files = glob.glob(os.path.join(repo_path, "*.nc"))
all_files.extend(glob.glob(os.path.join(repo_path, "*.NC")))
all_files.extend(glob.glob(os.path.join(repo_path, "*.txt")))

print(f"Scanning {len(all_files)} files for steel ring patterns...")
print()

# Collect steel ring data
steel_ring_data = []
cb_sizes = defaultdict(int)  # Counterbore diameter frequency
cb_depths = defaultdict(int)  # Counterbore depth frequency
round_sizes = defaultdict(int)  # Round size frequency

for i, filepath in enumerate(all_files):
    filename = os.path.basename(filepath)

    # Progress indicator
    if (i + 1) % 500 == 0:
        print(f"Progress: {i+1}/{len(all_files)} files...", end='\r')

    try:
        result = parser.parse_file(filepath)

        # Only process files with STEEL keyword (confirmed steel rings)
        title = result.title or ""
        if 'STEEL' not in title.upper():
            continue

        # Extract data
        round_size = result.outer_diameter or 0
        cb_diam = result.counter_bore_diameter or 0
        cb_depth = result.counter_bore_depth or 0

        if round_size > 0 or cb_diam > 0 or cb_depth > 0:
            steel_ring_data.append({
                'file': filename,
                'title': title,
                'round_size': round_size,
                'cb_diameter': cb_diam,
                'cb_depth': cb_depth,
                'thickness': result.thickness or 0
            })

            # Track frequencies (round to nearest 0.1)
            if cb_diam > 0:
                cb_sizes[round(cb_diam, 1)] += 1
            if cb_depth > 0:
                cb_depths[round(cb_depth, 2)] += 1
            if round_size > 0:
                round_sizes[round(round_size, 2)] += 1

    except Exception as e:
        pass

print()
print("=" * 80)
print("STEEL RING DATA COLLECTED")
print("=" * 80)
print()

print(f"Total steel ring files found: {len(steel_ring_data)}")
print()

# Show sample files
print("Sample Steel Ring Files:")
for item in steel_ring_data[:10]:
    print(f"  {item['file']}")
    print(f"    Title: {item['title']}")
    print(f"    Round Size: {item['round_size']:.2f}\" | CB Diam: {item['cb_diameter']:.1f}mm | CB Depth: {item['cb_depth']:.3f}\"")
    print()

# Analysis: Counterbore Diameters
print("=" * 80)
print("COUNTERBORE DIAMETER DISTRIBUTION")
print("=" * 80)
print()

sorted_cb_sizes = sorted(cb_sizes.items(), key=lambda x: x[1], reverse=True)
print(f"{'CB Diameter (mm)':<20} {'Count':<10} {'Bar Chart'}")
print("-" * 70)
for size, count in sorted_cb_sizes[:20]:  # Top 20
    bar = '#' * min(count, 50)
    print(f"{size:<20.1f} {count:<10} {bar}")

# Analysis: Counterbore Depths
print()
print("=" * 80)
print("COUNTERBORE DEPTH DISTRIBUTION")
print("=" * 80)
print()

sorted_cb_depths = sorted(cb_depths.items(), key=lambda x: x[1], reverse=True)
print(f"{'CB Depth (in)':<20} {'Count':<10} {'Bar Chart'}")
print("-" * 70)
for depth, count in sorted_cb_depths[:15]:  # Top 15
    bar = '#' * min(count, 50)
    print(f"{depth:<20.3f} {count:<10} {bar}")

# Analysis: Round Sizes
print()
print("=" * 80)
print("ROUND SIZE DISTRIBUTION")
print("=" * 80)
print()

sorted_round_sizes = sorted(round_sizes.items(), key=lambda x: x[1], reverse=True)
print(f"{'Round Size (in)':<20} {'Count':<10} {'Bar Chart'}")
print("-" * 70)
for size, count in sorted_round_sizes:
    bar = '#' * min(count, 50)
    print(f"{size:<20.2f} {count:<10} {bar}")

# Common patterns
print()
print("=" * 80)
print("COMMON STEEL RING PATTERNS")
print("=" * 80)
print()

# Group by round size and show common CB diameters for each
by_round_size = defaultdict(lambda: {'cb_diams': defaultdict(int), 'cb_depths': defaultdict(int)})

for item in steel_ring_data:
    rs = round(item['round_size'], 2)
    if rs > 0:
        if item['cb_diameter'] > 0:
            by_round_size[rs]['cb_diams'][round(item['cb_diameter'], 1)] += 1
        if item['cb_depth'] > 0:
            by_round_size[rs]['cb_depths'][round(item['cb_depth'], 2)] += 1

print("Round Size -> Common Counterbore Sizes:")
print()
for rs in sorted(by_round_size.keys()):
    cb_diams = by_round_size[rs]['cb_diams']
    if cb_diams:
        top_cbs = sorted(cb_diams.items(), key=lambda x: x[1], reverse=True)[:3]
        cb_str = ", ".join([f"{cb:.1f}mm ({count}x)" for cb, count in top_cbs])
        print(f"  {rs:.2f}\" -> {cb_str}")

print()
print("Round Size -> Common Counterbore Depths:")
print()
for rs in sorted(by_round_size.keys()):
    cb_depths_for_size = by_round_size[rs]['cb_depths']
    if cb_depths_for_size:
        top_depths = sorted(cb_depths_for_size.items(), key=lambda x: x[1], reverse=True)[:3]
        depth_str = ", ".join([f"{depth:.3f}\" ({count}x)" for depth, count in top_depths])
        print(f"  {rs:.2f}\" -> {depth_str}")

print()
print("=" * 80)
print("RECOMMENDATIONS FOR DETECTION")
print("=" * 80)
print()
print("Steel ring detection should:")
print("  1. REQUIRE 'STEEL' keyword in title (already implemented)")
print("  2. Expect counterbore diameters in range: ", end="")
if cb_sizes:
    min_cb = min(cb_sizes.keys())
    max_cb = max(cb_sizes.keys())
    print(f"{min_cb:.1f}mm - {max_cb:.1f}mm")
print("  3. Expect counterbore depths in range: ", end="")
if cb_depths:
    min_depth = min(cb_depths.keys())
    max_depth = max(cb_depths.keys())
    print(f"{min_depth:.3f}\" - {max_depth:.3f}\"")
print("  4. Most common CB sizes: ", end="")
if sorted_cb_sizes:
    top_3_cbs = sorted_cb_sizes[:3]
    print(", ".join([f"{cb:.1f}mm" for cb, _ in top_3_cbs]))
print()
