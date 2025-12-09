import sqlite3
import json

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("SAMPLE CRITICAL ERRORS")
print("=" * 80)
print()

cursor.execute("""
    SELECT program_number, title, validation_issues
    FROM programs
    WHERE validation_status = 'CRITICAL'
      AND validation_issues IS NOT NULL
    ORDER BY program_number
    LIMIT 30
""")

results = cursor.fetchall()

error_type_counts = {}

for prog_num, title, issues_str in results:
    try:
        issues = json.loads(issues_str)
        for issue in issues:
            # Extract error type (first part before colon)
            if ':' in issue:
                error_type = issue.split(':')[0].strip()
            else:
                error_type = issue[:30]

            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

            print(f"{prog_num}:")
            print(f"  {issue[:100]}")
            if len(issue) > 100:
                print(f"  ...")
            print()
    except:
        print(f"{prog_num}: Error parsing validation issues")
        print()

print("=" * 80)
print("ERROR TYPE SUMMARY (from first 30 files)")
print("=" * 80)

for error_type, count in sorted(error_type_counts.items(), key=lambda x: -x[1]):
    print(f"{error_type:<40} {count:>5}")

conn.close()
