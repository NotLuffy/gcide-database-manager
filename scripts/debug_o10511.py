"""
Debug o10511.nc CB extraction to understand why X4.4 (111.76mm) is selected
instead of correct X5.567 (141.4mm)
"""

import sys
import re
# Clear cached module
if 'improved_gcode_parser_roughing_test' in sys.modules:
    del sys.modules['improved_gcode_parser_roughing_test']

# Read the file manually to trace CB candidates
file_path = "l:\\My Drive\\Home\\File organizer\\repository\\o10511.nc"

with open(file_path, 'r') as f:
    lines = f.readlines()

print("=" * 80)
print("DEBUGGING o10511.nc CB EXTRACTION")
print("=" * 80)
print()

# Scan for CB candidates in OP1 BORE
in_bore_op1 = False
in_flip = False
cb_candidates_found = []

for i, line in enumerate(lines, 1):
    line_upper = line.upper()

    # Track operations
    if 'FLIP' in line_upper:
        in_flip = True
        in_bore_op1 = False
        print(f"\nLine {i}: FLIP PART detected - exiting OP1")
        break
    elif 'T121' in line_upper or 'BORE' in line_upper:
        if not in_flip:
            in_bore_op1 = True
            print(f"Line {i}: Entering BORE operation")
    elif 'T101' in line_upper or 'DRILL' in line_upper:
        in_bore_op1 = False

    # Look for X values in BORE operation
    if in_bore_op1 and not in_flip:
        x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
        z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

        if x_match:
            x_val = float(x_match.group(1))
            z_val = float(z_match.group(1)) if z_match else None

            # Look ahead for Z on next lines if not on same line
            max_z_depth = z_val
            if not z_val or z_val < 0.5:
                for j in range(i, min(i+5, len(lines))):
                    next_z = re.search(r'Z\s*-\s*([\d.]+)', lines[j], re.IGNORECASE)
                    if next_z:
                        z_depth = float(next_z.group(1))
                        if max_z_depth is None or z_depth > max_z_depth:
                            max_z_depth = z_depth

            # Check if this is a boring operation (not rapid)
            is_g00 = line.strip().startswith('G00')
            is_g01 = line.strip().startswith('G01')
            has_marker = '(X IS CB)' in line_upper or 'X IS CB' in line

            # Track CB range candidates (1.5-10.0 inches)
            if 1.5 < x_val < 10.0:
                cb_candidates_found.append({
                    'line': i,
                    'x': x_val,
                    'x_mm': x_val * 25.4,
                    'z': max_z_depth,
                    'is_g00': is_g00,
                    'is_g01': is_g01,
                    'has_marker': has_marker,
                    'text': line.strip()
                })

                # Print significant candidates
                if max_z_depth and max_z_depth > 0.3:  # Significant depth
                    marker_str = " (X IS CB)" if has_marker else ""
                    move_type = "G00" if is_g00 else "G01" if is_g01 else "???"
                    print(f"  Line {i:3}: {move_type} X{x_val:.3f} Z-{max_z_depth:.2f}{marker_str} = {x_val*25.4:.1f}mm")

print()
print("=" * 80)
print("CB CANDIDATES SUMMARY")
print("=" * 80)
print()

# Analyze candidates
full_depth_candidates = [c for c in cb_candidates_found if c['z'] and c['z'] > 2.0 and not c['is_g00']]
chamfer_depth_candidates = [c for c in cb_candidates_found if c['z'] and 0.1 <= c['z'] <= 0.25 and not c['is_g00']]
shallow_candidates = [c for c in cb_candidates_found if c['z'] and 0.3 < c['z'] < 2.0 and not c['is_g00']]
marker_candidates = [c for c in cb_candidates_found if c['has_marker']]

print(f"Full depth (Z > 2.0\") candidates: {len(full_depth_candidates)}")
for c in full_depth_candidates:
    print(f"  Line {c['line']}: X{c['x']:.4f} ({c['x_mm']:.1f}mm) at Z-{c['z']:.2f}")

print()
print(f"Chamfer depth (Z 0.1-0.25\") candidates: {len(chamfer_depth_candidates)}")
for c in chamfer_depth_candidates:
    marker = " (X IS CB)" if c['has_marker'] else ""
    print(f"  Line {c['line']}: X{c['x']:.4f} ({c['x_mm']:.1f}mm) at Z-{c['z']:.2f}{marker}")

print()
print(f"Shallow/shelf (Z 0.3-2.0\") candidates: {len(shallow_candidates)}")
for c in shallow_candidates[:5]:  # First 5
    print(f"  Line {c['line']}: X{c['x']:.4f} ({c['x_mm']:.1f}mm) at Z-{c['z']:.2f}")
if len(shallow_candidates) > 5:
    print(f"  ... and {len(shallow_candidates)-5} more")

print()
print(f"Marker \"(X IS CB)\" candidates: {len(marker_candidates)}")
for c in marker_candidates:
    z_str = f"{c['z']:.2f}" if c['z'] else "N/A"
    print(f"  Line {c['line']}: X{c['x']:.4f} ({c['x_mm']:.1f}mm) at Z-{z_str}")

print()
print("=" * 80)
print("EXPECTED vs ACTUAL")
print("=" * 80)
print("Title CB: 141.3mm")
print("Expected CB: X5.567 (141.4mm) at Z-2.4 - FULL DEPTH")
print("Misleading marker: X6.69 (169.9mm) at Z-0.15 - CHAMFER at COUNTERBORE")
print()

# Now run the actual parser to see what it extracts
from improved_gcode_parser_roughing_test import ImprovedGCodeParser
parser = ImprovedGCodeParser()
result = parser.parse_file(file_path)

print("PARSER RESULT:")
print(f"  CB extracted: {result.cb_from_gcode:.1f}mm ({result.cb_from_gcode/25.4:.4f}\")")
print()

# Identify what was extracted
if result.cb_from_gcode:
    cb_inches = result.cb_from_gcode / 25.4
    matching = [c for c in cb_candidates_found if abs(c['x'] - cb_inches) < 0.01]
    if matching:
        c = matching[0]
        print(f"MATCHED to Line {c['line']}: {c['text']}")
        print(f"  Move type: {'G00 (RAPID!)' if c['is_g00'] else 'G01' if c['is_g01'] else 'Unknown'}")
        print(f"  Z depth: {c['z']}")
        print()
        if c['is_g00']:
            print("[ERROR] Parser selected a G00 RAPID MOVE, not a boring operation!")
    else:
        print("[WARNING] No matching candidate found in scan")

print("=" * 80)
