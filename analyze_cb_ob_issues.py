import sqlite3

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('=' * 80)
print('CB/OB DETECTION ISSUES ANALYSIS')
print('=' * 80)
print()

# Find files with CB TOO LARGE or CB TOO SMALL errors
cursor.execute('''
    SELECT program_number, title, spacer_type, center_bore, hub_diameter,
           cb_from_gcode, ob_from_gcode, validation_issues
    FROM programs
    WHERE validation_issues LIKE "%CB TOO LARGE%"
       OR validation_issues LIKE "%CB TOO SMALL%"
    ORDER BY program_number
    LIMIT 30
''')

results = cursor.fetchall()

print(f'Found {len(results)} files with CB size errors\n')
print(f'{"Prog #":<10} {"Type":<15} {"CB Title":<12} {"CB G-code":<12} {"OB Title":<12} {"OB G-code":<12} {"Issue":<40}')
print('-' * 130)

for prog, title, sp_type, cb_title, hub_d, cb_gcode, ob_gcode, issues in results[:20]:
    # Parse issues to get the specific error
    issue_short = ''
    if 'CB TOO LARGE' in issues:
        issue_short = 'CB TOO LARGE'
    elif 'CB TOO SMALL' in issues:
        issue_short = 'CB TOO SMALL'

    # Format values
    cb_t_str = f'{cb_title:.1f}mm' if cb_title else 'None'
    cb_g_str = f'{cb_gcode:.1f}mm' if cb_gcode else 'None'
    ob_t_str = f'{hub_d:.1f}mm' if hub_d else 'None'
    ob_g_str = f'{ob_gcode:.1f}mm' if ob_gcode else 'None'

    print(f'{prog:<10} {sp_type:<15} {cb_t_str:<12} {cb_g_str:<12} {ob_t_str:<12} {ob_g_str:<12} {issue_short:<40}')

print()
print('=' * 80)
print('PATTERN ANALYSIS')
print('=' * 80)
print()

# Check for pattern: CB_gcode ≈ OB_title (CB is being detected as OB)
swapped_count = 0
for prog, title, sp_type, cb_title, hub_d, cb_gcode, ob_gcode, issues in results:
    if cb_title and cb_gcode and hub_d:
        # Check if CB from G-code is close to OB from title
        if abs(cb_gcode - hub_d) < 5.0:  # Within 5mm
            swapped_count += 1
            if swapped_count <= 10:
                print(f'{prog}: CB_gcode ({cb_gcode:.1f}mm) ≈ OB_title ({hub_d:.1f}mm) - LIKELY SWAPPED!')

print()
print(f'Files where CB_gcode ≈ OB_title (likely swapped): {swapped_count}')

conn.close()
