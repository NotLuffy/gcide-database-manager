"""
Parse Steel Ring Titles Directly
Extract MM values and dimensions from title format
"""

import os
import glob
import re
from collections import defaultdict

print("=" * 80)
print("STEEL RING TITLE PARSING")
print("=" * 80)
print()

repo_path = r"l:\My Drive\Home\File organizer\repository"

# Get all G-code files
all_files = glob.glob(os.path.join(repo_path, "*.nc"))
all_files.extend(glob.glob(os.path.join(repo_path, "*.NC")))
all_files.extend(glob.glob(os.path.join(repo_path, "*.txt")))

steel_ring_files = []
cb_sizes = defaultdict(int)
thicknesses = defaultdict(int)

for filepath in all_files:
    try:
        with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                # Look for title line with program number
                if re.match(r'^O\d+', line, re.IGNORECASE):
                    # Check if it's a steel ring file
                    if 'STEEL' in line.upper():
                        # Extract title from parentheses
                        match = re.search(r'\((.*?)\)', line)
                        if match:
                            title = match.group(1)

                            # Parse steel ring title format:
                            # Examples:
                            # "8IN 121.3MM 3.5 STEEL HCS-1" -> CB: 121.3mm, Thickness: 3.5"
                            # "9.5IN DIA 154.2MM 3.0 STEEL S-1" -> CB: 154.2mm, Thickness: 3.0"
                            # "9.5IN$ 141.3MM 2.0 THK STEEL S-1" -> CB: 141.3mm, Thickness: 2.0"

                            # Extract MM value (counterbore diameter)
                            mm_match = re.search(r'(\d+\.?\d*)\s*MM', title.upper())
                            if mm_match:
                                cb_mm = float(mm_match.group(1))
                                cb_sizes[round(cb_mm, 1)] += 1
                            else:
                                cb_mm = None

                            # Extract thickness (number before STEEL keyword)
                            thick_match = re.search(r'(\d+\.?\d+)\s+(?:THK\s+)?STEEL', title.upper())
                            if thick_match:
                                thickness = float(thick_match.group(1))
                                thicknesses[round(thickness, 2)] += 1
                            else:
                                thickness = None

                            steel_ring_files.append({
                                'file': os.path.basename(filepath),
                                'title': title,
                                'cb_mm': cb_mm,
                                'thickness': thickness
                            })

                    break  # Only need first Oxxxxx line
    except:
        pass

print(f"Total steel ring files found: {len(steel_ring_files)}")
print()

# Show samples
print("Sample Parsed Steel Ring Files:")
for item in steel_ring_files[:15]:
    print(f"  {item['file']}")
    print(f"    Title: {item['title']}")
    print(f"    CB: {item['cb_mm']}mm | Thickness: {item['thickness']}\"")
    print()

# Counterbore distribution
print("=" * 80)
print("COUNTERBORE DIAMETER DISTRIBUTION")
print("=" * 80)
print()

sorted_cbs = sorted(cb_sizes.items(), key=lambda x: x[1], reverse=True)
print(f"{'CB Diameter (mm)':<20} {'Count':<10} {'Bar Chart'}")
print("-" * 70)
for cb, count in sorted_cbs:
    bar = '#' * min(count, 50)
    print(f"{cb:<20.1f} {count:<10} {bar}")

# Thickness distribution
print()
print("=" * 80)
print("THICKNESS DISTRIBUTION")
print("=" * 80)
print()

sorted_thick = sorted(thicknesses.items(), key=lambda x: x[1], reverse=True)
print(f"{'Thickness (in)':<20} {'Count':<10} {'Bar Chart'}")
print("-" * 70)
for thick, count in sorted_thick:
    bar = '#' * min(count, 50)
    print(f"{thick:<20.2f} {count:<10} {bar}")

print()
print("=" * 80)
print("KEY FINDINGS")
print("=" * 80)
print()

if sorted_cbs:
    print("Most common counterbore diameters:")
    for cb, count in sorted_cbs[:5]:
        print(f"  {cb:.1f}mm ({count} files)")
    print()

if sorted_thick:
    print("Most common thicknesses:")
    for thick, count in sorted_thick[:5]:
        print(f"  {thick:.2f}\" ({count} files)")
    print()

if cb_sizes:
    min_cb = min(cb_sizes.keys())
    max_cb = max(cb_sizes.keys())
    print(f"Counterbore range: {min_cb:.1f}mm - {max_cb:.1f}mm")
    print()

print("=" * 80)
print("PARSER ENHANCEMENT NEEDED")
print("=" * 80)
print()
print("Steel ring titles use format:")
print("  [ROUND_SIZE] [CB_MM]MM [THICKNESS] STEEL [TYPE]")
print()
print("Examples:")
print("  8IN 121.3MM 3.5 STEEL HCS-1")
print("  9.5IN DIA 154.2MM 3.0 STEEL S-1")
print("  9.5IN$ 141.3MM 2.0 THK STEEL S-1")
print()
print("Parser should extract:")
print("  counter_bore_diameter = MM value (e.g., 121.3mm)")
print("  thickness = number before STEEL (e.g., 3.5\")")
print()
