"""
Analyze turning tool depths across production files to validate standards
"""
import os
import re
import sqlite3
from collections import defaultdict

# Connect to database to get file info
db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

# Get files with known dimensions (thickness and hub_height)
cursor.execute("""
    SELECT program_number, file_path, thickness, hub_height, spacer_type
    FROM programs
    WHERE file_path IS NOT NULL
      AND thickness IS NOT NULL
      AND thickness > 0
      AND (is_deleted IS NULL OR is_deleted = 0)
    ORDER BY thickness, hub_height
""")

files = cursor.fetchall()
conn.close()

print(f"Analyzing {len(files)} files with known dimensions...")
print("=" * 100)

# Group files by total thickness (rounded to 0.25")
thickness_groups = defaultdict(list)

# Analyze each file
analyzed_count = 0
for prog_num, file_path, thickness, hub_height, spacer_type in files:
    if not os.path.exists(file_path):
        continue

    hub_height = hub_height or 0.0
    total_height = thickness + hub_height

    # Round to nearest 0.25"
    import math
    rounded_total = round(total_height / 0.25) * 0.25

    try:
        with open(file_path, 'r', errors='ignore') as f:
            lines = f.readlines()

        # Find turning tool (T3xx) Z depths
        in_turning_tool = False
        max_depth = 0.0

        for line in lines:
            # Skip comments
            if line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            # Stop at M01 (only check first side)
            if 'M01' in line.upper() or 'M1' in line.upper():
                break

            # Track tool changes
            tool_match = re.search(r'T(\d+)', line, re.IGNORECASE)
            if tool_match:
                tool_num = tool_match.group(1)
                in_turning_tool = tool_num[0] == '3'  # T3xx = turning tool
                continue

            # Skip G53 lines (tool home - machine coordinates)
            if 'G53' in line.upper():
                continue

            # Check Z depths for turning tool - ONLY G01 feed movements (not G00 rapids)
            if in_turning_tool:
                # Only count G01 feed movements (actual cutting)
                if re.search(r'\bG0?1\b', line.upper()):
                    z_match = re.search(r'Z\s*(-\d+\.?\d*)', line, re.IGNORECASE)
                    if z_match:
                        z_depth = abs(float(z_match.group(1)))
                        # Sanity check - ignore depths > 5" (likely errors or wrong coordinate system)
                        if z_depth <= 5.0:
                            max_depth = max(max_depth, z_depth)

        if max_depth > 0:
            thickness_groups[rounded_total].append({
                'program': prog_num,
                'thickness': thickness,
                'hub': hub_height,
                'total': total_height,
                'max_depth': max_depth
            })
            analyzed_count += 1

    except Exception as e:
        continue

print(f"Successfully analyzed {analyzed_count} files with turning tool operations\n")

# Report by thickness group
from turning_tool_depth_validator import TurningToolDepthValidator
validator = TurningToolDepthValidator()

print("TURNING TOOL DEPTH ANALYSIS BY THICKNESS")
print("=" * 100)

for rounded_total in sorted(thickness_groups.keys()):
    group = thickness_groups[rounded_total]

    # Get standard for this thickness
    standard = validator.get_standard_depth(rounded_total)
    jaw_limit = rounded_total - 0.3

    # Calculate stats
    depths = [item['max_depth'] for item in group]
    min_depth = min(depths)
    max_depth = max(depths)
    avg_depth = sum(depths) / len(depths)

    # Count how many exceed standard
    exceed_count = sum(1 for d in depths if d > standard + 0.05)  # 0.05" tolerance

    print(f"\n{rounded_total:.2f}\" TOTAL HEIGHT ({len(group)} files)")
    print("-" * 100)
    print(f"  Standard max depth: Z-{standard:.2f}")
    print(f"  Absolute jaw limit: Z-{jaw_limit:.2f}")
    print(f"  Actual depths used:")
    print(f"    Min:     Z-{min_depth:.2f}")
    print(f"    Average: Z-{avg_depth:.2f}")
    print(f"    Max:     Z-{max_depth:.2f}")
    print(f"  Files exceeding standard: {exceed_count}/{len(group)} ({exceed_count/len(group)*100:.1f}%)")

    # Show examples if many exceed
    if exceed_count > len(group) * 0.3:  # More than 30% exceed
        print(f"  [!] NOTE: {exceed_count/len(group)*100:.0f}% of files exceed standard - may need adjustment")

        # Show a few examples
        exceeding = [item for item in group if item['max_depth'] > standard + 0.05]
        print(f"  Examples of files exceeding standard:")
        for item in exceeding[:3]:
            print(f"    {item['program']}: {item['thickness']:.2f}\" + {item['hub']:.2f}\" hub = {item['total']:.2f}\" total, max depth: Z-{item['max_depth']:.2f}")

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

# Overall stats
all_groups = []
for rounded_total, group in thickness_groups.items():
    standard = validator.get_standard_depth(rounded_total)
    depths = [item['max_depth'] for item in group]
    exceed_count = sum(1 for d in depths if d > standard + 0.05)
    all_groups.append({
        'thickness': rounded_total,
        'files': len(group),
        'exceeding': exceed_count,
        'percent': exceed_count/len(group)*100 if group else 0
    })

total_files = sum(g['files'] for g in all_groups)
total_exceeding = sum(g['exceeding'] for g in all_groups)

print(f"Total files analyzed: {total_files}")
print(f"Files exceeding standards: {total_exceeding} ({total_exceeding/total_files*100:.1f}%)")
print(f"\nThickness groups needing attention (>30% exceed):")

for g in all_groups:
    if g['percent'] > 30:
        standard = validator.get_standard_depth(g['thickness'])
        print(f"  {g['thickness']:.2f}\" (standard: Z-{standard:.2f}): {g['exceeding']}/{g['files']} files exceed ({g['percent']:.0f}%)")
