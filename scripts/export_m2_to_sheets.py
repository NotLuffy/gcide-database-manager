"""
Export M2 flashdrive G-code files to CSV for Google Sheets
Extracts: File name, RND (round size), Thickness, CB, OB, Hub Thickness, Part Type
Organized by folder, then by CB lowest to highest
"""

import os
import csv
import re
from datetime import datetime
from improved_gcode_parser import ImprovedGCodeParser

def get_round_size_from_od(od):
    """Convert OD (inches) to round size string"""
    if od is None:
        return ""

    # Standard round sizes
    round_sizes = {
        5.75: "5.75",
        6.00: "6.00",
        6.25: "6.25",
        6.50: "6.50",
        7.00: "7.00",
        7.50: "7.50",
        8.00: "8.00",
        8.50: "8.50",
        9.50: "9.50",
        10.25: "10.25",
        10.50: "10.50",
        13.00: "13.00"
    }

    # Find closest match
    for std_od, name in round_sizes.items():
        if abs(od - std_od) <= 0.1:
            return name

    return str(round(od, 2))

def format_thickness(result):
    """Format thickness - prefer display format if available"""
    if result.thickness_display:
        return result.thickness_display
    elif result.thickness:
        # Check if it's a metric thickness (close to mm conversion)
        thickness_mm = result.thickness * 25.4
        common_mm = [10, 12, 15, 17, 20, 25, 30]
        for mm in common_mm:
            if abs(thickness_mm - mm) < 0.5:
                return f"{mm}MM"
        return str(result.thickness)
    return ""

def get_part_type(result):
    """Convert spacer_type to user-friendly part type"""
    type_map = {
        'standard': 'STD',
        'hub_centric': 'HC',
        'step': 'STEP',
        'steel_ring': 'STEEL RING',
        '2PC LUG': '2PC LUG',
        '2PC STUD': '2PC STUD',
        '2PC UNSURE': '2PC',
        'metric_spacer': 'METRIC'
    }
    return type_map.get(result.spacer_type, result.spacer_type.upper())

def extract_from_title(title):
    """Extract CB and OB from title if parser didn't get them"""
    cb = None
    ob = None

    if not title:
        return cb, ob

    # Pattern for CB/OB in title like "6.5IN DIA 77/93.1MM" or "78.3MM ID"
    # First number is usually CB, second is OB (if present)

    # Try "XX/YY MM" pattern (CB/OB format)
    match = re.search(r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*MM', title, re.IGNORECASE)
    if match:
        cb = float(match.group(1))
        ob = float(match.group(2))
        return cb, ob

    # Try "XX-YY MM" pattern
    match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*MM', title, re.IGNORECASE)
    if match:
        cb = float(match.group(1))
        ob = float(match.group(2))
        return cb, ob

    # Try single "XXMM ID" pattern (CB only)
    match = re.search(r'(\d+\.?\d*)\s*MM\s*ID', title, re.IGNORECASE)
    if match:
        cb = float(match.group(1))
        return cb, ob

    # Try single "XXMM" after DIA
    match = re.search(r'DIA\s+(\d+\.?\d*)\s*MM', title, re.IGNORECASE)
    if match:
        cb = float(match.group(1))
        return cb, ob

    return cb, ob

def process_folder(folder_path, parser):
    """Process all G-code files in a folder and return results"""
    results = []

    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return results

    # Get folder name for organization
    folder_name = os.path.basename(folder_path)

    # Find all G-code files
    for root, dirs, files in os.walk(folder_path):
        subfolder = os.path.relpath(root, folder_path)
        if subfolder == '.':
            subfolder = folder_name
        else:
            subfolder = f"{folder_name}/{subfolder}"

        for filename in files:
            # Skip non-gcode files
            if filename.startswith('.'):
                continue

            file_path = os.path.join(root, filename)

            try:
                result = parser.parse_file(file_path)
                if result:
                    # Get CB and OB
                    cb = result.center_bore
                    ob = result.hub_diameter or result.ob_from_gcode

                    # If parser didn't get CB/OB, try extracting from title
                    if cb is None or ob is None:
                        title_cb, title_ob = extract_from_title(result.title)
                        if cb is None:
                            cb = title_cb
                        if ob is None:
                            ob = title_ob

                    # Also try cb_from_gcode if still None
                    if cb is None and result.cb_from_gcode:
                        cb = result.cb_from_gcode
                    if ob is None and result.ob_from_gcode:
                        ob = result.ob_from_gcode

                    row = {
                        'Folder': subfolder,
                        'File Name': filename,
                        'RND': get_round_size_from_od(result.outer_diameter),
                        'Thickness': format_thickness(result),
                        'CB': round(cb, 1) if cb else '',
                        'OB': round(ob, 1) if ob else '',
                        'Hub Thickness': result.hub_height if result.hub_height else '',
                        'Part Type': get_part_type(result),
                        'Title': result.title or '',
                        'CB_sort': cb if cb else 9999  # For sorting
                    }
                    results.append(row)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                # Still add the file with minimal info
                results.append({
                    'Folder': subfolder,
                    'File Name': filename,
                    'RND': '',
                    'Thickness': '',
                    'CB': '',
                    'OB': '',
                    'Hub Thickness': '',
                    'Part Type': 'ERROR',
                    'Title': f'Error: {str(e)[:50]}',
                    'CB_sort': 9999
                })

    return results

def main():
    m2_path = r"C:\Users\design2\My Drive\rework\m2 flashdrive"
    output_path = r"C:\Users\design2\My Drive\rework\m2_flashdrive_export.csv"

    print(f"Processing M2 flashdrive: {m2_path}")
    print("This may take a few minutes...")

    parser = ImprovedGCodeParser()

    # Process all files
    all_results = process_folder(m2_path, parser)

    print(f"\nProcessed {len(all_results)} files")

    # Part type sort order: STD, HC, STEP, 2PC (LUG/STUD), STEEL RING
    part_type_order = {
        'STD': 1,
        'HC': 2,
        'STEP': 3,
        '2PC LUG': 4,
        '2PC STUD': 5,
        '2PC': 6,
        'STEEL RING': 7,
        'METRIC': 8,
        'ERROR': 99
    }

    def thickness_sort_key(thickness_str):
        """
        Sort thickness: MM first (10MM, 12MM, 15MM...), then inches (0.5, 0.75, 1.0...)
        Returns tuple: (is_inches, numeric_value)
        - is_inches=0 for MM, is_inches=1 for inches
        - This ensures MM comes before inches
        """
        if not thickness_str:
            return (2, 9999)  # Empty goes last

        thickness_str = str(thickness_str).upper().strip()

        # Check if it's MM
        if 'MM' in thickness_str:
            try:
                val = float(thickness_str.replace('MM', '').strip())
                return (0, val)  # MM first (0), then by value
            except:
                return (0, 9999)

        # Otherwise it's inches
        try:
            val = float(thickness_str)
            return (1, val)  # Inches second (1), then by value
        except:
            return (2, 9999)

    # Sort by Folder, then by Part Type, then by Thickness (MM first, then inches), then by CB
    all_results.sort(key=lambda x: (
        x['Folder'],
        part_type_order.get(x['Part Type'], 50),
        thickness_sort_key(x['Thickness']),
        x['CB_sort']
    ))

    # Write to CSV
    fieldnames = ['Folder', 'File Name', 'RND', 'Thickness', 'CB', 'OB', 'Hub Thickness', 'Part Type', 'Title']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nExported to: {output_path}")
    print("\nTo import into Google Sheets:")
    print("1. Open Google Sheets")
    print("2. File > Import > Upload")
    print("3. Select the CSV file")
    print("4. Choose 'Replace spreadsheet' or 'Insert new sheet'")

    # Print summary by folder
    print("\n=== Summary by Folder ===")
    folder_counts = {}
    for r in all_results:
        folder = r['Folder']
        folder_counts[folder] = folder_counts.get(folder, 0) + 1

    for folder, count in sorted(folder_counts.items()):
        print(f"  {folder}: {count} files")

    # Print part type summary
    print("\n=== Summary by Part Type ===")
    type_counts = {}
    for r in all_results:
        pt = r['Part Type']
        type_counts[pt] = type_counts.get(pt, 0) + 1

    for pt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {pt}: {count} files")

if __name__ == '__main__':
    main()
