import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))

file_path = r"I:/My Drive/Home/Test Export of Repository/mc file export/13.0/o13008.nc"

# Read file and look for OP2
with open(file_path, 'r') as f:
    lines = f.readlines()

in_op2 = False
ob_candidates = []

print('=' * 80)
print('DEBUGGING o13008 OB DETECTION')
print('=' * 80)
print()

for i, line in enumerate(lines):
    line_upper = line.upper()

    # Detect OP2 section
    if '(OP2)' in line_upper or '( OP2 )' in line_upper:
        in_op2 = True
        print(f'[Line {i+1}] OP2 section started')
        continue

    if not in_op2:
        continue

    # Look for T code (tool change ends current operation)
    if re.match(r'^\s*T\d+', line_upper):
        print(f'[Line {i+1}] Tool change: {line.strip()}')

    # Look for X movements in OP2
    x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
    z_match = re.search(r'Z\s*-?\s*([\d.]+)', line, re.IGNORECASE)

    if x_match:
        x_val = float(x_match.group(1))
        z_val = float(z_match.group(1)) if z_match else None

        # Check range
        if 2.2 < x_val < 10.5:
            # Check if next line has Z movement
            has_following_z = False
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if re.search(r'Z\s*-?\s*([\d.]+)', next_line, re.IGNORECASE) and not re.search(r'X\s*([\d.]+)', next_line, re.IGNORECASE):
                    next_z_match = re.search(r'Z\s*-?\s*([\d.]+)', next_line, re.IGNORECASE)
                    if next_z_match:
                        next_z_val = float(next_z_match.group(1))
                        if 0.05 <= next_z_val <= 2.0:
                            has_following_z = True

            ob_candidates.append((x_val, z_val, i+1, has_following_z))

            marker = '[FOLLOWING_Z]' if has_following_z else ''
            print(f'[Line {i+1}] X={x_val:.3f} Z={z_val} {marker} | {line.strip()}')

print()
print('=' * 80)
print('OB CANDIDATES SUMMARY')
print('=' * 80)
print(f'Total candidates found: {len(ob_candidates)}')
print()

if ob_candidates:
    print('Candidates with following Z movement:')
    with_z = [x for x, z, idx, has_z in ob_candidates if has_z]
    if with_z:
        for x in with_z:
            print(f'  X={x:.3f} ({x*25.4:.1f}mm)')
    else:
        print('  None')

    print()
    print('All X values:')
    unique_x = sorted(set([x for x, z, idx, has_z in ob_candidates]))
    for x in unique_x:
        print(f'  X={x:.3f} ({x*25.4:.1f}mm)')

    print()
    print(f'Expected OB: X8.661 = {8.661*25.4:.1f}mm (title spec = 225mm)')
else:
    print('[ERROR] No OB candidates found!')
