"""Check current database schema"""
import sqlite3

conn = sqlite3.connect('gcode_database.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(programs)')
columns = cursor.fetchall()

print('Current columns in programs table:')
print('=' * 80)
for row in columns:
    print(f'{row[0]:>2}. {row[1]:<35} {row[2]:<15} NULL={row[3]}')

print(f'\nTotal columns: {len(columns)}')

# Check if tool/safety columns exist
tool_safety_cols = ['tool_validation_status', 'tool_validation_issues',
                    'safety_blocks_status', 'safety_blocks_issues']
existing_tool_safety = [col[1] for col in columns if col[1] in tool_safety_cols]

if existing_tool_safety:
    print(f'\nTool/Safety columns still in database: {existing_tool_safety}')
    print('These columns exist but are set to NULL (not used in validation)')
else:
    print('\nNo tool/safety columns found in database')

conn.close()
