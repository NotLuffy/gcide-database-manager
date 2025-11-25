"""
Scan database for false positive validation errors

This script identifies patterns that indicate parser bugs vs real errors:
1. Dash pattern (XX-YY) step spacers misclassified
2. Small CB values (< 10mm) likely title parsing errors
3. 2PC parts with validation errors (should skip validation)
4. Thickness errors in specific patterns
"""

import sqlite3

def scan_false_positives():
    conn = sqlite3.connect('gcode_database.db')
    cursor = conn.cursor()

    print('=' * 80)
    print('FALSE POSITIVE PATTERN SCAN')
    print('=' * 80)
    print()

    # Pattern 1: Dash pattern step spacers
    print('1. DASH PATTERN STEP SPACERS (XX-YY instead of XX/YY)')
    print('-' * 80)
    cursor.execute('''
        SELECT COUNT(*) FROM programs
        WHERE title LIKE '%-%MM%'
          AND validation_issues LIKE '%CB TOO%'
    ''')
    dash_count = cursor.fetchone()[0]
    print(f'Files with dash pattern showing CB errors: {dash_count}')

    if dash_count > 0:
        cursor.execute('''
            SELECT program_number, title, spacer_type
            FROM programs
            WHERE title LIKE '%-%MM%'
              AND validation_issues LIKE '%CB TOO%'
            LIMIT 5
        ''')
        print('\nSample files:')
        for prog, title, stype in cursor.fetchall():
            print(f'  {prog}: {title[:60]} (Type: {stype})')
    print()

    # Pattern 2: Very small CB values (< 10mm)
    print('2. VERY SMALL CB VALUES (< 10mm) - Likely title parsing errors')
    print('-' * 80)
    cursor.execute('''
        SELECT COUNT(*) FROM programs
        WHERE center_bore < 10
          AND center_bore > 0
    ''')
    small_cb_count = cursor.fetchone()[0]
    print(f'Files with CB < 10mm: {small_cb_count}')

    if small_cb_count > 0:
        cursor.execute('''
            SELECT program_number, title, center_bore, hub_diameter
            FROM programs
            WHERE center_bore < 10
              AND center_bore > 0
            ORDER BY center_bore
        ''')
        print('\nAll files with CB < 10mm:')
        for prog, title, cb, ob in cursor.fetchall():
            ob_str = f'{ob:.1f}' if ob else 'None'
            print(f'  {prog}: {title[:50]}')
            print(f'    CB={cb:.1f}mm, OB={ob_str}mm')
    print()

    # Pattern 3: 2PC parts with validation errors (should skip)
    print('3. 2PC PARTS WITH VALIDATION ERRORS (should skip CB/OB/thickness)')
    print('-' * 80)
    cursor.execute('''
        SELECT COUNT(*) FROM programs
        WHERE spacer_type LIKE '%2PC%'
          AND (validation_issues LIKE '%CB TOO%'
               OR validation_issues LIKE '%OB TOO%'
               OR validation_issues LIKE '%THICKNESS ERROR%')
    ''')
    twopc_errors = cursor.fetchone()[0]
    print(f'2PC parts with validation errors: {twopc_errors}')

    if twopc_errors > 0:
        cursor.execute('''
            SELECT program_number, title, spacer_type, validation_issues
            FROM programs
            WHERE spacer_type LIKE '%2PC%'
              AND (validation_issues LIKE '%CB TOO%'
                   OR validation_issues LIKE '%OB TOO%'
                   OR validation_issues LIKE '%THICKNESS ERROR%')
            LIMIT 10
        ''')
        print('\nSample 2PC errors:')
        for prog, title, stype, issues in cursor.fetchall():
            print(f'  {prog}: {title[:50]}')
            print(f'    Type: {stype}')
            print(f'    Issue: {issues[:70]}')
            print()

    # Pattern 4: CB/OB swapped (CB > OB for hub-centric)
    print('4. CB > OB FOR HUB-CENTRIC (values likely swapped)')
    print('-' * 80)
    cursor.execute('''
        SELECT COUNT(*) FROM programs
        WHERE spacer_type = 'hub_centric'
          AND center_bore > hub_diameter
          AND hub_diameter IS NOT NULL
    ''')
    swapped_count = cursor.fetchone()[0]
    print(f'Hub-centric parts with CB > OB: {swapped_count}')

    if swapped_count > 0:
        cursor.execute('''
            SELECT program_number, title, center_bore, hub_diameter
            FROM programs
            WHERE spacer_type = 'hub_centric'
              AND center_bore > hub_diameter
              AND hub_diameter IS NOT NULL
            LIMIT 10
        ''')
        print('\nSample files:')
        for prog, title, cb, ob in cursor.fetchall():
            print(f'  {prog}: {title[:60]}')
            print(f'    CB={cb:.1f}mm > OB={ob:.1f}mm (should be CB < OB!)')
    print()

    # Pattern 5: Standard type with XX/YY pattern (might be step)
    print('5. STANDARD TYPE WITH XX/YY PATTERN (might be step spacers)')
    print('-' * 80)
    cursor.execute('''
        SELECT COUNT(*) FROM programs
        WHERE spacer_type = 'standard'
          AND title LIKE '%/%MM%'
          AND validation_issues LIKE '%CB TOO%'
    ''')
    standard_slash_count = cursor.fetchone()[0]
    print(f'Standard type with XX/YY and CB errors: {standard_slash_count}')

    if standard_slash_count > 0:
        cursor.execute('''
            SELECT program_number, title, center_bore, validation_issues
            FROM programs
            WHERE spacer_type = 'standard'
              AND title LIKE '%/%MM%'
              AND validation_issues LIKE '%CB TOO%'
            LIMIT 5
        ''')
        print('\nSample files:')
        for prog, title, cb, issues in cursor.fetchall():
            print(f'  {prog}: {title[:60]}')
            print(f'    CB={cb:.1f}mm, Issue: {issues[:60]}')
    print()

    # Summary
    print('=' * 80)
    print('SUMMARY OF FALSE POSITIVE PATTERNS')
    print('=' * 80)
    total_false_positives = dash_count + small_cb_count + twopc_errors
    print(f'Dash pattern step spacers: {dash_count}')
    print(f'Small CB parsing errors: {small_cb_count}')
    print(f'2PC validation errors: {twopc_errors}')
    print(f'CB > OB swapped: {swapped_count}')
    print(f'Standard with XX/YY: {standard_slash_count}')
    print(f'\nTotal estimated false positives: {total_false_positives}+')
    print()
    print('Note: Some files may appear in multiple categories')

    conn.close()

if __name__ == '__main__':
    scan_false_positives()
