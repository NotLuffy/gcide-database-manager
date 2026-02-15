"""
Debug o00006.nc - Large 13" round hub pattern
Investigate why OB isn't extracted
"""

import sys
import os
import re

file_path = "l:\\My Drive\\Home\\File organizer\\repository\\o00006.nc"

if not os.path.exists(file_path):
    print("File not found!")
    sys.exit(1)

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("=" * 80)
print("o00006.nc - OP2 HUB PATTERN ANALYSIS")
print("=" * 80)
print()

# Find OP2 section
in_op2 = False
in_turn = False
op2_start = None

for i, line in enumerate(lines):
    line_upper = line.upper()

    if any(marker in line_upper for marker in ['OP2', 'OP 2', 'FLIP PART', 'FLIP', 'SIDE 2']):
        in_op2 = True
        op2_start = i
        print(f"OP2 START at line {i}: {line.strip()}")
        print()
        break

if not in_op2:
    print("No OP2 section found!")
    sys.exit(1)

# Analyze X and Z movements in OP2
print("X AND Z MOVEMENTS IN OP2 (first 100 lines):")
print("-" * 80)

x_movements = []
z_movements = []
current_z = None

for i in range(op2_start, min(op2_start + 150, len(lines))):
    line = lines[i]
    line_upper = line.upper()

    # Track turning tool
    if 'T303' in line_upper or 'T202' in line_upper:
        in_turn = True
        print(f"\nLine {i}: {line.strip()} [TURNING TOOL]")
    elif re.search(r'T[1]\d{2}', line_upper):
        if in_turn:
            print(f"\nLine {i}: {line.strip()} [END TURNING]")
        in_turn = False

    if in_turn:
        x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
        z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

        if z_match:
            current_z = float(z_match.group(1))
            z_movements.append((current_z, i))

        if x_match:
            x_val = float(x_match.group(1))
            x_movements.append((x_val, current_z, i))
            z_str = f"{current_z:.2f}" if current_z else "N/A"
            print(f"Line {i:3}: X{x_val:6.3f} Z-{z_str:5}  {line.strip()[:50]}")

print()
print("=" * 80)
print("ANALYSIS")
print("=" * 80)

if x_movements:
    print(f"Total X movements: {len(x_movements)}")
    x_values = [x for x, z, ln in x_movements]
    print(f"X range: {min(x_values):.3f}\" to {max(x_values):.3f}\"")
    print()

    # Check for oscillating pattern
    oscillations = 0
    for j in range(len(x_movements) - 1):
        x1, z1, ln1 = x_movements[j]
        x2, z2, ln2 = x_movements[j + 1]
        if x1 > x2 + 0.3:  # Large to small (inward turn)
            oscillations += 1
            print(f"Oscillation {oscillations}: Line {ln1} X{x1:.3f} -> Line {ln2} X{x2:.3f} (diff: {x1-x2:.3f}\")")

    print()
    print(f"Total oscillations detected: {oscillations}")
    print()

if z_movements:
    print(f"Total Z movements: {len(z_movements)}")
    z_values = [z for z, ln in z_movements]
    print(f"Z range: {min(z_values):.2f}\" to {max(z_values):.2f}\"")
    print()

    # Check for stepped Z pattern
    if len(z_values) > 1:
        z_steps = [z_values[i+1] - z_values[i] for i in range(len(z_values)-1) if z_values[i+1] > z_values[i]]
        if z_steps:
            avg_step = sum(z_steps) / len(z_steps)
            print(f"Z steps detected: {len(z_steps)}")
            print(f"Average Z step: {avg_step:.2f}\"")
            print(f"Z step range: {min(z_steps):.2f}\" to {max(z_steps):.2f}\"")

print("=" * 80)
