import sqlite3
import re

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('=' * 80)
print('2PC FILES WITH HC DIMENSIONS')
print('=' * 80)
print()

# Find all 2PC files with HC in title
cursor.execute('''
    SELECT program_number, title, spacer_type, thickness, hub_height, validation_status
    FROM programs
    WHERE spacer_type LIKE "2PC%"
      AND title LIKE "% HC %"
    ORDER BY program_number
    LIMIT 50
''')

results = cursor.fetchall()
print(f'Found {len(results)} 2PC files with HC in title\n')

# Analyze the HC patterns in titles
print('=' * 80)
print('HC PATTERN ANALYSIS')
print('=' * 80)
print()

print(f'{"Prog #":<10} {"Parsed T/H":<15} {"Should Be":<15} {"Status":<15} {"Title":<50}')
print('-' * 120)

likely_swapped = []
correct_parsing = []

for prog, title, sp_type, thick, hub_h, status in results:
    # Extract HC pattern from title
    # Pattern: "X.X HC Y.Y" where X.X=thickness, Y.Y=hub
    hc_match = re.search(r'(\d+\.?\d*)\s*-*HC\s*(\d*\.?\d+)', title, re.IGNORECASE)

    if hc_match:
        title_first = float(hc_match.group(1))
        title_second = float(hc_match.group(2))

        parsed_str = f'{thick}/{hub_h}' if thick and hub_h else 'None/None'
        should_be_str = f'{title_first}/{title_second}'

        # Check if values match or are swapped
        if thick == title_first and hub_h == title_second:
            correct_parsing.append(prog)
            status_str = '[OK]'
        elif thick == title_second and hub_h == title_first:
            likely_swapped.append(prog)
            status_str = '[SWAPPED!]'
        else:
            status_str = '[MISMATCH]'

        title_short = title[:47] + '...' if len(title) > 50 else title
        print(f'{prog:<10} {parsed_str:<15} {should_be_str:<15} {status_str:<15} {title_short}')

print()
print('=' * 80)
print('SUMMARY')
print('=' * 80)
print(f'Total 2PC files with HC: {len(results)}')
print(f'  Correctly parsed: {len(correct_parsing)}')
print(f'  Likely swapped (NEED FIX): {len(likely_swapped)}')
print()

if likely_swapped:
    print('Files with swapped thickness/hub values:')
    for prog in likely_swapped[:20]:
        print(f'  {prog}')
    if len(likely_swapped) > 20:
        print(f'  ... and {len(likely_swapped) - 20} more files')

print()
print('=' * 80)
print('13.0 ROUND FILES - HUB DIAMETER MISSING')
print('=' * 80)
print()

# Check 13.0 round files for missing hub_diameter
cursor.execute('''
    SELECT program_number, title, hub_height, hub_diameter, center_bore
    FROM programs
    WHERE title LIKE "13.0%"
      AND hub_height IS NOT NULL
      AND hub_diameter IS NULL
    LIMIT 30
''')

results_13 = cursor.fetchall()
print(f'Found {len(results_13)} 13.0 round files with hub but no hub_diameter\n')

for prog, title, hub_h, hub_d, cb in results_13[:15]:
    print(f'{prog}: {title}')
    print(f'  Hub Height={hub_h}, Hub Diameter={hub_d}, CB={cb}')

    # Try to extract hub diameter from title
    # Pattern: "X.XIN" where X.X is the hub diameter in inches
    # Example: "8.7IN/220MM" - 8.7" is the hub diameter
    hd_match = re.search(r'(\d+\.?\d*)\s*IN\s*/\s*\d+', title, re.IGNORECASE)
    if hd_match:
        possible_hd = float(hd_match.group(1))
        print(f'  Possible Hub Diameter from title: {possible_hd}"')
    print()

conn.close()
