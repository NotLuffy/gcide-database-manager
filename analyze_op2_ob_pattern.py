"""
Analyze OP2 turning operation pattern to understand OB extraction.
Focus on 5.75" rounds with OB issues.
"""

import re

# Analyze o50007
file_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\repository\o50007.nc"

print("Analyzing o50007")
print("Title: 5.75 70.3MM/73.1MM 10MM HC")
print("Expected: CB=70.3mm, OB=73.1mm (2.878\")")
print("=" * 100)

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

in_op2 = False
for i, line in enumerate(lines, 1):
    line_upper = line.upper()

    # Detect OP2 start
    if 'FLIP PART' in line_upper or ('M00' in line and i > 40):
        in_op2 = True
        print(f"\n[Line {i}] OP2 START: {line.strip()}")
        continue

    if in_op2:
        # Look for X values with Z movements
        x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
        z_match = re.search(r'Z\s*-?\s*([\d.]+)', line, re.IGNORECASE)

        if x_match:
            x_val = float(x_match.group(1))
            z_val = float(z_match.group(1)) if z_match else None

            # Track significant X values
            if 2.0 < x_val < 6.0:  # Potential CB or OB range
                x_mm = x_val * 25.4
                category = ""
                if abs(x_mm - 70.3) < 5:
                    category = " <- NEAR CB SPEC (70.3mm)"
                elif abs(x_mm - 73.1) < 5:
                    category = " <- NEAR OB SPEC (73.1mm) *** SHOULD BE SELECTED ***"
                elif abs(x_mm - 146) < 5:
                    category = " <- NEAR OD (5.75\" = 146mm) !!! WRONG !!!"

                print(f"[Line {i:3d}] X{x_val:.3f} ({x_mm:.1f}mm) Z{'-' if z_match else ''}{z_val if z_val else 'N/A'}{category}")
                print(f"           {line.strip()}")

        # Stop after chamfer
        if 'CHAMPHER' in line_upper or 'CHAMFER' in line_upper:
            print(f"\n[Line {i}] OP2 END (Chamfer tool): {line.strip()}")
            break

print("\n" + "=" * 100)
print("PATTERN ANALYSIS:")
print("=" * 100)
print("OP2 Turning Sequence:")
print("1. Line 81-82: X5.7 Z0. then Z-0.2 - OD chamfer creation")
print("2. Line 83: X2.89 - FACE DOWN TO OB (73.4mm ≈ 73.1mm spec) *** THIS IS THE OB ***")
print("3. Line 91: X2.874 - Continue at OB")
print("4. Line 92: Z-0.14 - Move to chamfer depth")
print("5. Line 93: X2.774 Z-0.09 - OB chamfer")
print("")
print("ISSUE: Parser is selecting X5.7 (OD) instead of X2.89 (OB)")
print("FIX NEEDED: After OD chamfer (X5.7), look for SMALLEST X in range before Z<0.15")
