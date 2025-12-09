"""
Fix validation statuses that were incorrectly set to SAFETY_ERROR.
Re-calculate validation status based on the actual validation_issues, bore_warnings, etc.
"""

import sqlite3
import json

db_path = 'gcode_database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all programs currently marked as SAFETY_ERROR
cursor.execute("""
    SELECT program_number, validation_issues, bore_warnings, dimensional_issues,
           validation_warnings, safety_blocks_status
    FROM programs
    WHERE validation_status = 'SAFETY_ERROR'
""")

programs = cursor.fetchall()
print(f"Found {len(programs)} programs with SAFETY_ERROR status")

fixed_count = 0
status_breakdown = {}

for prog_num, val_issues, bore_warns, dim_issues, val_warns, safety_status in programs:
    # Recalculate validation status (without safety/tool checks)
    new_status = "PASS"

    # Parse JSON fields if they exist
    try:
        if val_issues:
            if isinstance(val_issues, str):
                if val_issues.startswith('['):
                    issues = json.loads(val_issues)
                else:
                    issues = [x.strip() for x in val_issues.split('|') if x.strip()]
            else:
                issues = val_issues
            if issues:
                new_status = "CRITICAL"
    except:
        if val_issues:
            new_status = "CRITICAL"

    if new_status == "PASS":
        try:
            if bore_warns:
                if isinstance(bore_warns, str):
                    if bore_warns.startswith('['):
                        warns = json.loads(bore_warns)
                    else:
                        warns = [x.strip() for x in bore_warns.split('|') if x.strip()]
                else:
                    warns = bore_warns
                if warns:
                    new_status = "BORE_WARNING"
        except:
            if bore_warns:
                new_status = "BORE_WARNING"

    if new_status == "PASS":
        try:
            if dim_issues:
                if isinstance(dim_issues, str):
                    if dim_issues.startswith('['):
                        dims = json.loads(dim_issues)
                    else:
                        dims = [x.strip() for x in dim_issues.split('|') if x.strip()]
                else:
                    dims = dim_issues
                if dims:
                    new_status = "DIMENSIONAL"
        except:
            if dim_issues:
                new_status = "DIMENSIONAL"

    if new_status == "PASS":
        try:
            if val_warns:
                if isinstance(val_warns, str):
                    if val_warns.startswith('['):
                        warns = json.loads(val_warns)
                    else:
                        warns = [x.strip() for x in val_warns.split('|') if x.strip()]
                else:
                    warns = val_warns
                if warns or (safety_status == "WARNING"):
                    new_status = "WARNING"
        except:
            if val_warns or (safety_status == "WARNING"):
                new_status = "WARNING"

    # Update the status
    cursor.execute("UPDATE programs SET validation_status = ? WHERE program_number = ?",
                   (new_status, prog_num))

    fixed_count += 1
    status_breakdown[new_status] = status_breakdown.get(new_status, 0) + 1

    if fixed_count % 100 == 0:
        print(f"Fixed {fixed_count}/{len(programs)}...")

conn.commit()
conn.close()

print(f"\nFixed {fixed_count} programs")
print("\nNew status breakdown:")
for status, count in sorted(status_breakdown.items()):
    print(f"  {status}: {count}")

print("\nDone!")
