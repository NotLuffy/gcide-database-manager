"""
Diagnostic script to identify which INSERT statement is causing the error.
Run this to capture the exact error when processing files from F:\
"""

import sys
import traceback
import sqlite3

# Monkey-patch sqlite3.Cursor.execute to trace all INSERT statements
original_execute = sqlite3.Cursor.execute

def traced_execute(self, sql, parameters=()):
    """Wrapper to trace INSERT statements and catch errors"""
    if 'INSERT' in sql.upper() and 'programs' in sql:
        # Count placeholders
        placeholder_count = sql.count('?')

        # Count parameters
        param_count = len(parameters) if isinstance(parameters, (tuple, list)) else 0

        # Get first 100 chars of SQL for context
        sql_preview = sql.strip()[:200]

        print(f"\n{'='*70}")
        print(f"INSERT STATEMENT DETECTED:")
        print(f"{'='*70}")
        print(f"SQL Preview: {sql_preview}...")
        print(f"Placeholder count: {placeholder_count}")
        print(f"Parameter count: {param_count}")

        if placeholder_count != param_count:
            print(f"\n⚠️  MISMATCH DETECTED!")
            print(f"   Expected: {placeholder_count} values")
            print(f"   Got: {param_count} values")
            print(f"\nFull SQL:\n{sql}")
            print(f"\nStack trace:")
            traceback.print_stack()

    # Call original execute
    try:
        return original_execute(self, sql, parameters)
    except Exception as e:
        if 'INSERT' in sql.upper() and 'programs' in sql:
            print(f"\n❌ ERROR OCCURRED:")
            print(f"   {str(e)}")
            print(f"\nFull SQL:\n{sql}")
            print(f"\nParameters ({len(parameters) if isinstance(parameters, (tuple, list)) else 0}):")
            if isinstance(parameters, (tuple, list)) and len(parameters) < 60:
                for i, p in enumerate(parameters, 1):
                    print(f"   {i}. {repr(p)[:50]}")
        raise

# Apply the patch
sqlite3.Cursor.execute = traced_execute

print("="*70)
print("  INSERT STATEMENT DIAGNOSTIC MODE ENABLED")
print("="*70)
print()
print("Now import and run your file processing operation.")
print("All INSERT INTO programs statements will be traced.")
print()
print("Example:")
print("  from gcode_database_manager import GCodeDatabaseManager")
print("  app = GCodeDatabaseManager()")
print("  # Then use the GUI to process files from F:\\")
print()
print("="*70)
