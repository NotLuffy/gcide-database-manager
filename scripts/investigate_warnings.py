"""
Investigate Warning Files from 1000-File Test
Analyzes the 9 files with CB diff >10mm to understand root causes
"""

import sys
import os
if 'improved_gcode_parser_roughing_test' in sys.modules:
    del sys.modules['improved_gcode_parser_roughing_test']

from improved_gcode_parser_roughing_test import ImprovedGCodeParser

parser = ImprovedGCodeParser()

# Files with CB diff >10mm from 1000-file test
warning_files = [
    ("o13008.nc", "CB diff: 13.4mm"),
    ("o13939.nc", "CB diff: 29.2mm"),
    ("o57140.nc", "CB diff: 12.9mm"),
    ("o63718.nc", "CB diff: 14.2mm"),
    ("o73510.nc", "CB diff: 13.5mm"),
    ("o75845.nc", "CB diff: 10.5mm"),
    ("o75256.nc", "CB diff: 10.5mm"),
    ("o73999.nc", "CB diff: 42.6mm"),
    ("o80279.nc", "CB diff: 115.7mm"),
]

print("=" * 80)
print("WARNING FILES INVESTIGATION: 9 Files with CB Diff >10mm")
print("=" * 80)
print()

repo_path = "l:\\My Drive\\Home\\File organizer\\repository"

for filename, expected_issue in warning_files:
    path = os.path.join(repo_path, filename)

    if not os.path.exists(path):
        print(f"[SKIP] {filename} - File not found")
        continue

    try:
        result = parser.parse_file(path)

        # Extract key metrics
        title_cb = result.center_bore if result.center_bore else None
        gcode_cb = result.cb_from_gcode if result.cb_from_gcode else None
        gcode_ob = result.ob_from_gcode if result.ob_from_gcode else None
        spacer_type = result.spacer_type if result.spacer_type else "Unknown"

        # Calculate difference
        if title_cb and gcode_cb:
            diff = abs(gcode_cb - title_cb)
        else:
            diff = None

        # Analyze pattern
        analysis = []

        # Check if STEP spacer (counterbore + CB)
        if spacer_type and 'step' in str(spacer_type).lower():
            analysis.append("STEP spacer (counterbore + CB)")

        # Check if steel ring (metric CB in title)
        if result.title and ('MM CB' in result.title.upper() or 'MM ID' in result.title.upper()):
            analysis.append("Steel ring assembly (metric CB)")

        # Check if CB > OB (thin hub)
        if gcode_cb and gcode_ob and gcode_cb > gcode_ob + 5.0:
            analysis.append(f"Thin hub (CB>{gcode_ob:.1f}mm)")

        # Check if title has multiple CBs (counterbore pattern)
        if result.title:
            title_upper = result.title.upper()
            if 'COUNTERBORE' in title_upper or 'C/BORE' in title_upper:
                analysis.append("Counterbore in title")

        # Print detailed result
        print(f"{filename}")
        print(f"  Title: {result.title[:60] if result.title else 'N/A'}")
        print(f"  Type: {spacer_type}")

        if title_cb:
            print(f"  Title CB: {title_cb:.1f}mm")
        else:
            print(f"  Title CB: N/A")

        if gcode_cb:
            print(f"  G-code CB: {gcode_cb:.1f}mm")
        else:
            print(f"  G-code CB: N/A")

        if diff:
            print(f"  Difference: {diff:.1f}mm")

        if gcode_ob:
            print(f"  G-code OB: {gcode_ob:.1f}mm")

        if analysis:
            print(f"  Analysis: {' | '.join(analysis)}")

        # Root cause guess
        if diff and diff > 50.0:
            print(f"  → LIKELY: Metric CB in title, inch CB extracted from G-code")
        elif diff and diff > 20.0:
            print(f"  → LIKELY: STEP spacer or counterbore confusion")
        elif diff and diff > 10.0:
            print(f"  → LIKELY: Roughing sequence or chamfer pattern issue")

        print()

    except Exception as e:
        print(f"[ERROR] {filename}: {str(e)[:60]}")
        print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print("Common patterns in warning files:")
print("  1. STEP spacers (counterbore + CB) - parser may extract wrong diameter")
print("  2. Steel ring assemblies (metric CB in title) - unit conversion issue")
print("  3. Thin hub patterns (CB > OB) - rare edge case")
print("  4. Counterbore patterns - multiple CB values in G-code")
print()
print("Most warnings are expected behavior for complex patterns.")
print("These edge cases may require specialized logic or manual review.")
print("=" * 80)
