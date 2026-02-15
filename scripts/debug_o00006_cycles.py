"""
Debug o00006.nc Hub Detection - Print Cycle Details
"""

import sys
import os
from improved_gcode_parser import ImprovedGCodeParser

parser = ImprovedGCodeParser()

repo_path = "l:\\My Drive\\Home\\File organizer\\repository"
path = os.path.join(repo_path, "o00006.nc")

print("="*80)
print("DEBUG o00006.nc Cycle Details")
print("="*80)
print()

# Read file
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Manually run hub detection to see what's in cycles
in_op2 = False
in_turn_op2 = False
x_movements = []
current_z = None

for i, line in enumerate(lines, 1):
    line_upper = line.upper()

    # Detect OP2
    if any(marker in line_upper for marker in ['OP2', 'OP 2', 'FLIP PART', 'FLIP', 'SIDE 2']):
        in_op2 = True
        print(f"Line {i}: OP2 detected")

    # Track turning operations in OP2
    if in_op2:
        if 'T303' in line_upper or ('TURN' in line_upper and 'TOOL' in line_upper):
            in_turn_op2 = True
            print(f"Line {i}: T303 turning operation started")
        elif line_upper.strip().startswith('T1') or line_upper.strip().startswith('T2'):
            if in_turn_op2:
                print(f"Line {i}: T303 turning operation ended")
            in_turn_op2 = False

    # Extract X and Z movements
    if in_turn_op2:
        import re
        x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
        z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

        if z_match:
            current_z = float(z_match.group(1))

        if x_match:
            x_val = float(x_match.group(1))
            x_movements.append((x_val, current_z, i))
            print(f"Line {i}: X movement - X{x_val:.3f} Z{current_z if current_z else 'N/A'}")

print()
print("="*80)
print(f"Total X movements collected: {len(x_movements)}")
print("="*80)
print()

# Build cycles
cycles = []
for j in range(len(x_movements) - 1):
    x1, z1, ln1 = x_movements[j]
    x2, z2, ln2 = x_movements[j + 1]

    if x1 > x2 + 0.3:
        if x1 > 4.0:
            cycles.append({
                'od_x': x1,
                'hub_x': x2,
                'z_depth': z2 if z2 else z1,
                'line': ln2
            })
            print(f"Cycle {len(cycles)}: OD={x1:.3f}\" => Hub={x2:.3f}\" at Z-{z2 if z2 else z1:.2f}\" (line {ln2})")

print()
print("="*80)
print(f"Total cycles detected: {len(cycles)}")
print("="*80)
print()

if cycles:
    hub_x_values = [c['hub_x'] for c in cycles]
    min_hub_x = min(hub_x_values)
    hub_diameter = min_hub_x - 0.01

    print(f"Hub X values: {', '.join([f'{x:.3f}' for x in hub_x_values])}")
    print(f"Minimum hub X: {min_hub_x:.3f}\"")
    print(f"Hub diameter (min - 0.01): {hub_diameter:.3f}\" ({hub_diameter * 25.4:.1f}mm)")
    print()
    print(f"Expected: ~4.872\" (123.7mm)")
    print(f"Difference: {abs(hub_diameter - 4.872):.3f}\"")
