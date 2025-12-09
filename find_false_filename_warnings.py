import sqlite3
import os
import re
import json

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("FINDING FALSE POSITIVE FILENAME MISMATCH WARNINGS")
print("=" * 80)
print()

# Find all files with CRITICAL status and filename mismatch in validation_issues
cursor.execute("""
    SELECT program_number, title, file_path, validation_issues
    FROM programs
    WHERE is_managed = 1
      AND validation_status = 'CRITICAL'
      AND validation_issues LIKE '%FILENAME MISMATCH%'
    ORDER BY program_number
""")

results = cursor.fetchall()

print(f"Found {len(results)} files with filename mismatch warnings\n")

false_positives = []
true_mismatches = []
cannot_verify = []

for prog_num, title, file_path, validation_issues_str in results:
    if not file_path or not os.path.exists(file_path):
        cannot_verify.append((prog_num, file_path, validation_issues_str))
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
                # FALSE POSITIVE - they actually match!
                false_positives.append((prog_num, filename_onumber, internal_onumber, validation_issues_str))
            else:
                # TRUE MISMATCH
                true_mismatches.append((prog_num, filename_onumber, internal_onumber, validation_issues_str))
        else:
            cannot_verify.append((prog_num, file_path, validation_issues_str))
    except Exception as e:
        cannot_verify.append((prog_num, file_path, f"Error: {e}"))

print("=" * 80)
print(f"FALSE POSITIVES: {len(false_positives)} files")
print("=" * 80)
print("Files flagged as CRITICAL but filename actually matches internal O-number:")
print()

for prog_num, filename_o, internal_o, issues_str in false_positives[:20]:
    # Parse the validation issue to see what it claims
    try:
        issues = json.loads(issues_str)
        issue_text = issues[0] if issues else "Unknown"
    except:
        issue_text = issues_str

    print(f"{prog_num}:")
    print(f"  Actual: Filename={filename_o}, Internal={internal_o} [MATCH!]")
    print(f"  Warning says: {issue_text}")
    print()

if len(false_positives) > 20:
    print(f"... and {len(false_positives) - 20} more false positives")

print()
print("=" * 80)
print(f"TRUE MISMATCHES: {len(true_mismatches)} files")
print("=" * 80)
print("Files that actually have filename != internal O-number:")
print()

for prog_num, filename_o, internal_o, issues_str in true_mismatches[:10]:
    print(f"{prog_num}: Filename={filename_o}, Internal={internal_o}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total filename mismatch warnings: {len(results)}")
print(f"  [!] FALSE POSITIVES: {len(false_positives)} (need to clear)")
print(f"  [OK] TRUE MISMATCHES: {len(true_mismatches)} (valid warnings)")
print(f"  [?] CANNOT VERIFY: {len(cannot_verify)} (file missing/error)")

conn.close()
