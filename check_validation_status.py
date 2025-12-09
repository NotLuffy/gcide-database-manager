import sqlite3
import json

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("VALIDATION STATUS BREAKDOWN")
print("=" * 80)
print()

# Get overall counts
cursor.execute("""
    SELECT validation_status, COUNT(*)
    FROM programs
    WHERE file_path IS NOT NULL
    GROUP BY validation_status
    ORDER BY
        CASE validation_status
            WHEN 'CRITICAL' THEN 1
            WHEN 'BORE_WARNING' THEN 2
            WHEN 'DIMENSIONAL' THEN 3
            WHEN 'WARNING' THEN 4
            WHEN 'PASS' THEN 5
            WHEN 'REPEAT' THEN 6
            ELSE 7
        END
""")

status_results = cursor.fetchall()

total_files = sum(count for _, count in status_results)

print(f"{'Status':<20} {'Count':>8} {'Percentage':>12}")
print("-" * 45)

for status, count in status_results:
    status_display = status if status else "NULL"
    percentage = (count / total_files * 100) if total_files > 0 else 0
    print(f"{status_display:<20} {count:>8} {percentage:>11.1f}%")

print("-" * 45)
print(f"{'TOTAL':<20} {total_files:>8} {100.0:>11.1f}%")

# Break down CRITICAL errors by type
print()
print("=" * 80)
print("CRITICAL ERROR BREAKDOWN")
print("=" * 80)
print()

cursor.execute("""
    SELECT program_number, validation_issues
    FROM programs
    WHERE validation_status = 'CRITICAL'
      AND validation_issues IS NOT NULL
    ORDER BY program_number
""")

critical_results = cursor.fetchall()

# Categorize critical errors
error_types = {
    'FILENAME MISMATCH': 0,
    'THICKNESS ERROR': 0,
    'CB TOO SMALL': 0,
    'CB TOO LARGE': 0,
    'OB TOO SMALL': 0,
    'OB TOO LARGE': 0,
    'OTHER': 0
}

for prog_num, issues_str in critical_results:
    try:
        issues = json.loads(issues_str)
        for issue in issues:
            categorized = False
            for error_type in error_types.keys():
                if error_type in issue:
                    error_types[error_type] += 1
                    categorized = True
                    break
            if not categorized:
                error_types['OTHER'] += 1
    except:
        error_types['OTHER'] += 1

print(f"{'Error Type':<30} {'Count':>8}")
print("-" * 40)

for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
    if count > 0:
        print(f"{error_type:<30} {count:>8}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total files: {total_files}")
print(f"CRITICAL errors: {sum(1 for s, c in status_results if s == 'CRITICAL' for _ in range(c))}")
print(f"Files passing validation: {sum(c for s, c in status_results if s == 'PASS')}")
print()

# Calculate health percentage
if total_files > 0:
    pass_count = sum(c for s, c in status_results if s == 'PASS')
    health_pct = (pass_count / total_files * 100)
    print(f"Repository Health: {health_pct:.1f}% passing")

conn.close()
