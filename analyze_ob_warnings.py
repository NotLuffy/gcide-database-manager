"""
Analyze OB extraction warnings, especially for 5.75" rounds.
"""

import sqlite3

conn = sqlite3.connect('gcode_database.db')
cursor = conn.cursor()

# Count OB warnings
cursor.execute("""
    SELECT COUNT(*) FROM programs
    WHERE validation_warnings LIKE '%OB extraction uncertain%'
    OR validation_warnings LIKE '%OB%matches OD%'
""")
warning_count = cursor.fetchone()[0]
print(f"Programs with OB/OD match warnings: {warning_count}")

# Get sample 5.75" rounds with OB warnings
cursor.execute("""
    SELECT program_number, outer_diameter, hub_diameter, ob_from_gcode,
           validation_warnings, file_path
    FROM programs
    WHERE validation_warnings LIKE '%OB%'
    AND outer_diameter BETWEEN 5.7 AND 5.8
    AND spacer_type = 'hub_centric'
    LIMIT 10
""")

print("\nSample 5.75 rounds with OB warnings:")
print("=" * 100)

samples = []
for row in cursor.fetchall():
    prog_num, od, title_ob, extracted_ob, warnings, file_path = row
    print(f"\n{prog_num}:")
    print(f"  OD: {od:.2f}\"")
    print(f"  Title OB: {title_ob:.1f}mm")
    print(f"  Extracted OB: {extracted_ob:.1f}mm")
    print(f"  Difference: {abs(extracted_ob - title_ob):.1f}mm")
    print(f"  Warning: {warnings[:80]}...")
    samples.append((prog_num, file_path))

conn.close()

# Return first sample for detailed analysis
if samples:
    print(f"\n\nFirst sample for detailed analysis: {samples[0][0]}")
    print(f"File: {samples[0][1]}")
