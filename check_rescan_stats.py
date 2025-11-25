"""Check database statistics after rescan"""
import sqlite3

conn = sqlite3.connect('gcode_database.db')
c = conn.cursor()

print('=' * 80)
print('DATABASE STATISTICS AFTER RESCAN')
print('=' * 80)
print()

# Total programs
c.execute('SELECT COUNT(*) FROM programs')
total = c.fetchone()[0]
print(f'Total programs: {total}')
print()

# Validation status
print('Validation Status:')
c.execute('SELECT validation_status, COUNT(*) FROM programs GROUP BY validation_status ORDER BY COUNT(*) DESC')
for status, count in c.fetchall():
    pct = (count / total) * 100
    print(f'  {status}: {count:5d} ({pct:5.1f}%)')
print()

# 2PC Classification
print('2PC Classification:')
c.execute('SELECT spacer_type, COUNT(*) FROM programs WHERE spacer_type LIKE "%2PC%" GROUP BY spacer_type ORDER BY COUNT(*) DESC')
twopc_types = c.fetchall()
for stype, count in twopc_types:
    print(f'  {stype}: {count}')

c.execute('SELECT COUNT(*) FROM programs WHERE spacer_type LIKE "%2PC%"')
total_2pc = c.fetchone()[0]
print(f'  Total 2PC: {total_2pc}')
print()

# Type changes summary
print('Type Changes from Rescan:')
print('  2PC UNSURE -> 2PC LUG/STUD: 117 files')
print('  standard/hub_centric -> step: 8 files')
print('  Total type changes: 125 files')
print()

# CRITICAL error comparison
print('CRITICAL Error Reduction:')
c.execute('SELECT COUNT(*) FROM programs WHERE validation_status = "CRITICAL"')
critical_now = c.fetchone()[0]
critical_before = 648
reduction = critical_before - critical_now
reduction_pct = (reduction / critical_before) * 100
print(f'  Before rescan: {critical_before} (10.4%)')
print(f'  After rescan: {critical_now} ({(critical_now/total)*100:.1f}%)')
print(f'  Reduction: {reduction} files ({reduction_pct:.1f}%)')

conn.close()
