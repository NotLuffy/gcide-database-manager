"""
Automatic INSERT Statement Verification

This script verifies that all INSERT INTO programs statements have the correct
column count to prevent "table has X columns but got Y values" errors.

Run this after modifying the programs table schema or INSERT statements.
"""

import sqlite3
import re
from pathlib import Path


def get_actual_column_count(db_path: str) -> int:
    """Get actual column count from database"""
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(programs)')
        count = len(cursor.fetchall())
        conn.close()
        return count
    except Exception as e:
        print(f"Warning: Could not access database ({e})")
        print("Using known column count: 56")
        return 56  # Known current count


def find_insert_statements(file_path: str) -> list:
    """Find all INSERT INTO programs statements"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find INSERT statements
    pattern = r'INSERT(?:\s+OR\s+REPLACE)?\s+INTO\s+programs\s+(?:VALUES|\()'
    matches = list(re.finditer(pattern, content, re.IGNORECASE))

    results = []
    for match in matches:
        line_num = content[:match.start()].count('\n') + 1

        # Get the full INSERT statement (next 2000 chars)
        statement = content[match.start():match.start()+2000]

        # Determine type
        if 'VALUES' in statement[:100].upper() and '(' in statement[:100]:
            # Named columns pattern
            insert_type = 'NAMED'

            # Extract column names
            columns_match = re.search(r'INTO\s+programs\s*\((.*?)\)\s*VALUES', statement, re.DOTALL | re.IGNORECASE)
            if columns_match:
                columns_text = columns_match.group(1)
                # Count columns (split by comma, clean up)
                columns = [c.strip() for c in columns_text.split(',') if c.strip()]
                column_count = len(columns)
            else:
                column_count = 0

            # Extract placeholders
            values_match = re.search(r'VALUES\s*\((.*?)\)', statement, re.DOTALL)
            if values_match:
                placeholders = values_match.group(1).count('?')
            else:
                placeholders = 0
        else:
            # VALUES-only pattern (all columns)
            insert_type = 'VALUES'
            column_count = None  # Should be all columns

            # Extract placeholders
            values_match = re.search(r'VALUES\s*\((.*?)\)', statement, re.DOTALL)
            if values_match:
                placeholders = values_match.group(1).count('?')
            else:
                placeholders = 0

        results.append({
            'line': line_num,
            'type': insert_type,
            'columns': column_count,
            'placeholders': placeholders,
            'statement_preview': statement[:150]
        })

    return results


def verify_inserts(db_path: str, code_file: str) -> dict:
    """Verify all INSERT statements"""
    actual_columns = get_actual_column_count(db_path)
    inserts = find_insert_statements(code_file)

    issues = []
    warnings = []

    for insert in inserts:
        if insert['type'] == 'VALUES':
            # VALUES inserts must have all columns
            if insert['placeholders'] != actual_columns:
                issues.append({
                    'line': insert['line'],
                    'issue': f"VALUES insert has {insert['placeholders']} placeholders, expected {actual_columns}",
                    'severity': 'ERROR'
                })
        else:
            # Named column inserts
            if insert['columns'] != insert['placeholders']:
                issues.append({
                    'line': insert['line'],
                    'issue': f"Column count ({insert['columns']}) doesn't match placeholders ({insert['placeholders']})",
                    'severity': 'ERROR'
                })

            # Warn if named insert doesn't use all columns
            if insert['columns'] < actual_columns:
                warnings.append({
                    'line': insert['line'],
                    'issue': f"Named insert uses {insert['columns']}/{actual_columns} columns (others will be NULL)",
                    'severity': 'WARNING'
                })

    return {
        'actual_columns': actual_columns,
        'inserts_found': len(inserts),
        'inserts': inserts,
        'issues': issues,
        'warnings': warnings
    }


def main():
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    code_file = r"l:\My Drive\Home\File organizer\gcode_database_manager.py"

    print("="*70)
    print("  INSERT STATEMENT VERIFICATION")
    print("="*70)

    # Run verification
    results = verify_inserts(db_path, code_file)

    print(f"\nDatabase Info:")
    print(f"  Actual column count: {results['actual_columns']}")
    print(f"  INSERT statements found: {results['inserts_found']}")

    # Show all INSERT statements
    print("\n" + "-"*70)
    print("INSERT Statements Found:")
    print("-"*70)
    for insert in results['inserts']:
        status = "OK"
        if insert['type'] == 'VALUES':
            if insert['placeholders'] != results['actual_columns']:
                status = "ERROR"
        elif insert['columns'] != insert['placeholders']:
            status = "ERROR"

        print(f"\nLine {insert['line']}: {insert['type']} - {status}")
        if insert['type'] == 'NAMED':
            print(f"  Columns: {insert['columns']}, Placeholders: {insert['placeholders']}")
        else:
            print(f"  Placeholders: {insert['placeholders']} (expected: {results['actual_columns']})")

    # Show issues
    print("\n" + "="*70)
    if results['issues']:
        print("ERRORS FOUND:")
        print("="*70)
        for issue in results['issues']:
            print(f"\n[ERROR] Line {issue['line']}:")
            print(f"  {issue['issue']}")
        print("\nACTION REQUIRED: Fix these errors before scanning/importing files!")
    else:
        print("NO ERRORS - All INSERT statements are correct!")

    # Show warnings
    if results['warnings']:
        print("\n" + "-"*70)
        print("WARNINGS:")
        print("-"*70)
        for warning in results['warnings']:
            print(f"\n[WARNING] Line {warning['line']}:")
            print(f"  {warning['issue']}")
        print("\nThese are informational - not errors.")

    print("\n" + "="*70)

    # Exit code
    if results['issues']:
        print("VERIFICATION FAILED - Errors found!")
        return 1
    else:
        print("VERIFICATION PASSED - All inserts correct!")
        return 0


if __name__ == "__main__":
    exit(main())
