"""
Part Type Accuracy Checker
Scans repository for files where detected part type might not match the title/content
"""

import os
import glob
import re
from improved_gcode_parser import ImprovedGCodeParser
from collections import defaultdict

parser = ImprovedGCodeParser()

print("=" * 80)
print("PART TYPE ACCURACY CHECK")
print("=" * 80)
print()

repo_path = r"l:\My Drive\Home\File organizer\repository"

# Get all G-code files
all_files = glob.glob(os.path.join(repo_path, "*.nc"))
all_files.extend(glob.glob(os.path.join(repo_path, "*.NC")))
all_files.extend(glob.glob(os.path.join(repo_path, "*.txt")))

print(f"Scanning {len(all_files)} files...")
print()

# Track potential issues
issues = {
    'steel_ring_no_keyword': [],  # Detected as steel_ring but no "STEEL" in title
    'steel_ring_small_mm': [],    # Steel ring but MM value < 95mm (might be standard CB notation)
    'standard_with_steel': [],    # Detected as standard but has "STEEL" in title
    'hub_centric_no_hub': [],     # Detected as hub_centric but no hub dimensions
    'step_no_step': [],           # Detected as step but no "STEP" keyword
    'unknown_type': [],           # Type is None or empty
}

results = {
    'total': 0,
    'steel_ring': 0,
    'standard': 0,
    'hub_centric': 0,
    'step': 0,
    'unknown': 0,
    'errors': 0
}

for i, filepath in enumerate(all_files):
    filename = os.path.basename(filepath)

    # Progress indicator
    if (i + 1) % 100 == 0:
        print(f"Progress: {i+1}/{len(all_files)} files...", end='\r')

    try:
        result = parser.parse_file(filepath)
        results['total'] += 1

        title = result.title or ""
        spacer_type = result.spacer_type or ""

        # Count by type
        if spacer_type == 'steel_ring':
            results['steel_ring'] += 1
        elif spacer_type == 'standard':
            results['standard'] += 1
        elif spacer_type == 'hub_centric':
            results['hub_centric'] += 1
        elif spacer_type == 'step':
            results['step'] += 1
        else:
            results['unknown'] += 1

        # Check for potential mismatches
        title_upper = title.upper()

        # Issue 1: Steel ring detected but no "STEEL" keyword in title
        if spacer_type == 'steel_ring' and 'STEEL' not in title_upper:
            # Check if it has MM ID/CB notation
            mm_match = re.search(r'(\d+\.?\d*)\s*MM\s+(ID|CB)', title_upper)
            if mm_match:
                mm_value = float(mm_match.group(1))
                issues['steel_ring_no_keyword'].append({
                    'file': filename,
                    'title': title,
                    'mm_value': mm_value,
                    'type': spacer_type
                })

        # Issue 2: Steel ring with small MM value (< 95mm might be standard CB notation)
        if spacer_type == 'steel_ring':
            mm_match = re.search(r'(\d+\.?\d*)\s*MM\s+(ID|CB)', title_upper)
            if mm_match:
                mm_value = float(mm_match.group(1))
                if mm_value < 95:
                    issues['steel_ring_small_mm'].append({
                        'file': filename,
                        'title': title,
                        'mm_value': mm_value,
                        'has_steel': 'STEEL' in title_upper
                    })

        # Issue 3: Standard detected but has "STEEL" in title
        if spacer_type == 'standard' and 'STEEL' in title_upper:
            issues['standard_with_steel'].append({
                'file': filename,
                'title': title,
                'type': spacer_type
            })

        # Issue 4: Hub centric but no hub dimensions
        if spacer_type == 'hub_centric':
            if not result.hub_diameter and not result.hub_height:
                issues['hub_centric_no_hub'].append({
                    'file': filename,
                    'title': title,
                    'type': spacer_type
                })

        # Issue 5: Step type but no "STEP" keyword
        if spacer_type == 'step' and 'STEP' not in title_upper:
            issues['step_no_step'].append({
                'file': filename,
                'title': title,
                'type': spacer_type
            })

        # Issue 6: Unknown/empty type
        if not spacer_type or spacer_type.strip() == '':
            issues['unknown_type'].append({
                'file': filename,
                'title': title,
                'type': spacer_type or 'None'
            })

    except Exception as e:
        results['errors'] += 1

print("\n" + "=" * 80)
print("SCAN COMPLETE")
print("=" * 80)
print()

print("Statistics:")
print(f"  Total files scanned: {results['total']}")
print(f"  Steel ring: {results['steel_ring']}")
print(f"  Standard: {results['standard']}")
print(f"  Hub centric: {results['hub_centric']}")
print(f"  Step: {results['step']}")
print(f"  Unknown/None: {results['unknown']}")
print(f"  Parse errors: {results['errors']}")
print()

# Report potential issues
print("=" * 80)
print("POTENTIAL PART TYPE ISSUES")
print("=" * 80)
print()

if issues['steel_ring_no_keyword']:
    print(f"WARNING: STEEL RING without 'STEEL' keyword ({len(issues['steel_ring_no_keyword'])} files)")
    print("   These might be false positives (standard spacers with MM ID notation)")
    print()
    for item in issues['steel_ring_no_keyword'][:10]:  # Show first 10
        print(f"   {item['file']}")
        print(f"      Title: {item['title']}")
        print(f"      MM Value: {item['mm_value']}")
        print()
    if len(issues['steel_ring_no_keyword']) > 10:
        print(f"   ... and {len(issues['steel_ring_no_keyword']) - 10} more")
    print()

if issues['steel_ring_small_mm']:
    print(f"WARNING: STEEL RING with small MM value < 95mm ({len(issues['steel_ring_small_mm'])} files)")
    print("   These might be standard spacers with CB/ID in MM notation")
    print()
    for item in issues['steel_ring_small_mm'][:10]:
        print(f"   {item['file']}")
        print(f"      Title: {item['title']}")
        print(f"      MM Value: {item['mm_value']}, Has STEEL: {item['has_steel']}")
        print()
    if len(issues['steel_ring_small_mm']) > 10:
        print(f"   ... and {len(issues['steel_ring_small_mm']) - 10} more")
    print()

if issues['standard_with_steel']:
    print(f"WARNING: STANDARD type with 'STEEL' keyword ({len(issues['standard_with_steel'])} files)")
    print("   These might be steel rings misclassified as standard")
    print()
    for item in issues['standard_with_steel'][:10]:
        print(f"   {item['file']}")
        print(f"      Title: {item['title']}")
        print()
    if len(issues['standard_with_steel']) > 10:
        print(f"   ... and {len(issues['standard_with_steel']) - 10} more")
    print()

if issues['hub_centric_no_hub']:
    print(f"WARNING: HUB CENTRIC without hub dimensions ({len(issues['hub_centric_no_hub'])} files)")
    print("   Parser detected hub centric but couldn't extract hub dimensions")
    print()
    for item in issues['hub_centric_no_hub'][:5]:
        print(f"   {item['file']}: {item['title']}")
    if len(issues['hub_centric_no_hub']) > 5:
        print(f"   ... and {len(issues['hub_centric_no_hub']) - 5} more")
    print()

if issues['step_no_step']:
    print(f"WARNING: STEP type without 'STEP' keyword ({len(issues['step_no_step'])} files)")
    print()
    for item in issues['step_no_step'][:5]:
        print(f"   {item['file']}: {item['title']}")
    if len(issues['step_no_step']) > 5:
        print(f"   ... and {len(issues['step_no_step']) - 5} more")
    print()

if issues['unknown_type']:
    print(f"WARNING: UNKNOWN/None type ({len(issues['unknown_type'])} files)")
    print("   Parser couldn't determine spacer type")
    print()
    for item in issues['unknown_type'][:10]:
        print(f"   {item['file']}: {item['title']}")
    if len(issues['unknown_type']) > 10:
        print(f"   ... and {len(issues['unknown_type']) - 10} more")
    print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
total_issues = sum(len(v) for v in issues.values())
if total_issues == 0:
    print("OK - No part type issues detected!")
else:
    print(f"Found {total_issues} potential issues across {len([k for k, v in issues.items() if v])} categories")
    print()
    print("Recommendations:")
    if issues['steel_ring_no_keyword'] or issues['steel_ring_small_mm']:
        print("  - Review steel ring detection logic - might need stricter criteria")
    if issues['standard_with_steel']:
        print("  - Files with 'STEEL' keyword should probably be steel_ring type")
    if issues['unknown_type']:
        print("  - Some files have no type detected - might need better fallback logic")

print()
