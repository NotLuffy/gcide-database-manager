import sqlite3
import os
import re
import json
import sys

# Add the current directory to path to import the parser
sys.path.insert(0, os.path.dirname(__file__))

from improved_gcode_parser import ImprovedGCodeParser

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

print("=" * 80)
print("REFRESHING FILENAME MISMATCH VALIDATIONS")
print("=" * 80)
print()

# Find all files with CRITICAL status and filename mismatch warnings
cursor.execute("""
    SELECT program_number, title, file_path, validation_issues, validation_status
    FROM programs
    WHERE is_managed = 1
      AND validation_status = 'CRITICAL'
      AND validation_issues LIKE '%FILENAME MISMATCH%'
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Found {len(results)} files with filename mismatch warnings")
print(f"Checking which ones are false positives...\n")

# Initialize parser
parser = ImprovedGCodeParser()

false_positives = []
true_mismatches = []
errors = []

for prog_num, title, file_path, validation_issues_str, validation_status in results:
    if not file_path or not os.path.exists(file_path):
        errors.append((prog_num, "File not found"))
        continue

    # Extract filename O-number
    filename = os.path.basename(file_path)
    filename_match = re.search(r'[oO](\d+)', filename)
    filename_onumber = 'o' + filename_match.group(1) if filename_match else None

    # Extract internal O-number from file
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        internal_onumber = None
        for line in lines[:10]:
            internal_match = re.match(r'^[oO](\d+)', line.strip())
            if internal_match:
                internal_onumber = 'o' + internal_match.group(1)
                break

        if filename_onumber and internal_onumber:
            if filename_onumber == internal_onumber:
                # FALSE POSITIVE - filename matches internal O-number
                false_positives.append(prog_num)
            else:
                # TRUE MISMATCH
                true_mismatches.append((prog_num, filename_onumber, internal_onumber))
        else:
            errors.append((prog_num, "Could not extract O-numbers"))
    except Exception as e:
        errors.append((prog_num, str(e)))

print("=" * 80)
print("ANALYSIS")
print("=" * 80)
print(f"Total files checked: {len(results)}")
print(f"  False positives: {len(false_positives)}")
print(f"  True mismatches: {len(true_mismatches)}")
print(f"  Errors: {len(errors)}")
print()

if true_mismatches:
    print("TRUE MISMATCHES (will keep CRITICAL status):")
    for prog_num, filename_o, internal_o in true_mismatches:
        print(f"  {prog_num}: File {filename_o} != Internal {internal_o}")
    print()

if errors:
    print("ERRORS:")
    for prog_num, error in errors[:10]:
        print(f"  {prog_num}: {error}")
    if len(errors) > 10:
        print(f"  ... and {len(errors) - 10} more errors")
    print()

print("=" * 80)
print(f"REFRESHING {len(false_positives)} FALSE POSITIVES")
print("=" * 80)
print()

response = input(f"Re-scan {len(false_positives)} files to refresh their validation? (yes/no): ")

if response.lower() != 'yes':
    print("Cancelled.")
    conn.close()
    exit()

print()
print("Re-scanning files...")
print()

fixed_count = 0
error_count = 0

for i, prog_num in enumerate(false_positives):
    # Get file path
    cursor.execute("SELECT file_path FROM programs WHERE program_number = ?", (prog_num,))
    result = cursor.fetchone()

    if not result or not result[0]:
        error_count += 1
        continue

    file_path = result[0]

    try:
        # Re-parse the file with current parser
        parse_result = parser.parse_file(file_path)

        if parse_result:
            # Determine validation status
            validation_status = "PASS"
            if parse_result.validation_issues:
                validation_status = "CRITICAL"
            elif parse_result.bore_warnings:
                validation_status = "BORE_WARNING"
            elif parse_result.dimensional_issues:
                validation_status = "DIMENSIONAL"
            elif parse_result.validation_warnings:
                validation_status = "WARNING"

            # Update validation fields
            cursor.execute("""
                UPDATE programs
                SET validation_status = ?,
                    validation_issues = ?,
                    validation_warnings = ?,
                    bore_warnings = ?,
                    dimensional_issues = ?
                WHERE program_number = ?
            """, (
                validation_status,
                json.dumps(parse_result.validation_issues) if parse_result.validation_issues else None,
                json.dumps(parse_result.validation_warnings) if parse_result.validation_warnings else None,
                json.dumps(parse_result.bore_warnings) if parse_result.bore_warnings else None,
                json.dumps(parse_result.dimensional_issues) if parse_result.dimensional_issues else None,
                prog_num
            ))

            fixed_count += 1

            if (i + 1) % 50 == 0:
                print(f"  ... processed {i + 1}/{len(false_positives)} files")
                conn.commit()
        else:
            error_count += 1
    except Exception as e:
        error_count += 1
        print(f"  Error processing {prog_num}: {e}")

conn.commit()
conn.close()

print()
print("=" * 80)
print("COMPLETE")
print("=" * 80)
print(f"Successfully refreshed: {fixed_count} files")
print(f"Errors: {error_count} files")
print()
print("The false positive filename mismatch warnings have been cleared.")
print(f"True mismatches ({len(true_mismatches)} files) remain as CRITICAL.")
