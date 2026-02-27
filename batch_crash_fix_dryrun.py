"""
Batch Crash-Fix Dry-Run Report
===============================
Scans all files in the database that have crash_issues, runs all 4 auto-fix
passes in DRY-RUN mode (no files are written), and writes a detailed report.

Usage:
    python batch_crash_fix_dryrun.py              # dry-run report only (default)
    python batch_crash_fix_dryrun.py --apply      # apply fixes after reviewing report
    python batch_crash_fix_dryrun.py --program O48501   # single program dry-run

Output:
    batch_crash_fix_report.txt   — per-file proposed changes
    batch_crash_fix_summary.csv  — one row per file (program, n_changes, types)
"""

import os
import sys
import sqlite3
import csv
import shutil
from datetime import datetime

# ── resolve project root ──────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(SCRIPT_DIR, 'gcode_database.db')
REPORT_PATH = os.path.join(SCRIPT_DIR, 'batch_crash_fix_report.txt')
CSV_PATH    = os.path.join(SCRIPT_DIR, 'batch_crash_fix_summary.csv')

# ── import AutoFixer from the project ─────────────────────────────────────────
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'utils'))
from gcode_auto_fixer import AutoFixer


# ─────────────────────────────────────────────────────────────────────────────
def run_all_passes(content: str):
    """
    Run all 5 crash-fix passes on content and return
    (fixed_content, changes_offset, changes_explicit, changes_modal, changes_feed, changes_z0).
    No files are written.
    """
    fixed, chg_offset   = AutoFixer.fix_work_offset_z_clearance(content)
    fixed, chg_explicit = AutoFixer.fix_rapid_to_negative_z(fixed)
    fixed, chg_modal    = AutoFixer.fix_modal_g00_z_plunge(fixed)
    fixed, chg_feed     = AutoFixer.fix_g01_missing_feedrate(fixed)
    fixed, chg_z0       = AutoFixer.fix_bare_z0_approach(fixed)
    return fixed, chg_offset, chg_explicit, chg_modal, chg_feed, chg_z0


def format_section(label, changes):
    if not changes:
        return ''
    lines = [f"  [{label}]"]
    for c in changes:
        lines.append(f"    • {c}")
    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    apply_mode     = '--apply' in sys.argv
    single_program = None
    for arg in sys.argv[1:]:
        if arg.startswith('--program'):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith('--'):
                single_program = sys.argv[idx + 1].upper()

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if single_program:
        cursor.execute(
            "SELECT program_number, file_path, crash_issues FROM programs "
            "WHERE UPPER(program_number) = ? AND file_path IS NOT NULL",
            (single_program,)
        )
    else:
        cursor.execute(
            "SELECT program_number, file_path, crash_issues FROM programs "
            "WHERE file_path IS NOT NULL "
            "ORDER BY program_number"
        )
    rows = cursor.fetchall()
    conn.close()

    # ── stats accumulators ────────────────────────────────────────────────────
    total_files      = 0
    files_with_fixes = 0
    total_changes    = 0
    skipped_missing  = 0
    csv_rows         = []

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mode_label = "DRY-RUN" if not apply_mode else "APPLY MODE"

    report_lines = [
        "=" * 78,
        f"  BATCH CRASH-FIX REPORT  —  {mode_label}",
        f"  Generated: {ts}",
        f"  Database:  {DB_PATH}",
        "=" * 78,
        "",
    ]

    applied_files  = []
    no_change_files = []

    for program_number, file_path, _crash_json in rows:
        total_files += 1

        if not file_path or not os.path.exists(file_path):
            skipped_missing += 1
            report_lines.append(
                f"[SKIP] {program_number}  —  file not found: {file_path}"
            )
            csv_rows.append({
                'program':   program_number,
                'n_changes': 0,
                'types':     'FILE_MISSING',
                'file_path': file_path or '',
            })
            continue

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
            original = fh.read()

        fixed, chg_off, chg_exp, chg_mod, chg_feed, chg_z0 = run_all_passes(original)
        all_changes = chg_off + chg_exp + chg_mod + chg_feed + chg_z0
        n = len(all_changes)

        if n == 0:
            no_change_files.append(program_number)
            csv_rows.append({
                'program':   program_number,
                'n_changes': 0,
                'types':     'NONE',
                'file_path': file_path,
            })
            continue

        # ── there are proposed changes ─────────────────────────────────────
        files_with_fixes += 1
        total_changes    += n

        change_types = []
        if chg_off:   change_types.append('work_offset_z')
        if chg_exp:   change_types.append('explicit_g00')
        if chg_mod:   change_types.append('modal_g00')
        if chg_feed:  change_types.append('g01_missing_f')
        if chg_z0:    change_types.append('bare_z0_chamfer')

        csv_rows.append({
            'program':   program_number,
            'n_changes': n,
            'types':     '+'.join(change_types),
            'file_path': file_path,
        })

        sections = '\n'.join(filter(None, [
            format_section('Work-offset Z clearance',       chg_off),
            format_section('Explicit G00 rapids',           chg_exp),
            format_section('Modal G00 bare-Z plunges',      chg_mod),
            format_section('G01 transition missing F',      chg_feed),
            format_section('Bare Z0 chamfer approach',      chg_z0),
        ]))

        report_lines += [
            "-" * 78,
            f"  {program_number}   ({n} change{'s' if n != 1 else ''})",
            f"  File: {file_path}",
            sections,
        ]

        if apply_mode:
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'archive', 'crash_fix_backups')
            os.makedirs(backup_dir, exist_ok=True)
            backup = os.path.join(backup_dir, os.path.basename(file_path) + '.crash_fix_backup')
            shutil.copy2(file_path, backup)
            with open(file_path, 'w', encoding='utf-8') as fh:
                fh.write(fixed)
            report_lines.append(f"  ✔ APPLIED — backup: {backup}")
            applied_files.append(program_number)

        report_lines.append("")

    # ── summary footer ────────────────────────────────────────────────────────
    report_lines += [
        "=" * 78,
        "  SUMMARY",
        "=" * 78,
        f"  Files scanned:          {total_files}",
        f"  Files with fixes:       {files_with_fixes}",
        f"  Files with no changes:  {len(no_change_files)}",
        f"  Files not found:        {skipped_missing}",
        f"  Total individual fixes: {total_changes}",
    ]

    if apply_mode:
        report_lines.append(f"  Files written:          {len(applied_files)}")

    report_lines += ["", "  Files with no changes:"]
    for p in no_change_files:
        report_lines.append(f"    {p}")
    report_lines.append("")

    # ── write report ──────────────────────────────────────────────────────────
    report_text = '\n'.join(report_lines)
    with open(REPORT_PATH, 'w', encoding='utf-8') as fh:
        fh.write(report_text)

    # ── write CSV ─────────────────────────────────────────────────────────────
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['program', 'n_changes', 'types', 'file_path'])
        writer.writeheader()
        writer.writerows(csv_rows)

    # ── console summary ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Batch crash-fix {mode_label}")
    print(f"{'='*60}")
    print(f"  Files scanned:          {total_files}")
    print(f"  Files with fixes:       {files_with_fixes}")
    print(f"  Files with no changes:  {len(no_change_files)}")
    print(f"  Files not found:        {skipped_missing}")
    print(f"  Total individual fixes: {total_changes}")
    if apply_mode:
        print(f"  Files written:          {len(applied_files)}")
    print(f"\n  Report: {REPORT_PATH}")
    print(f"  CSV:    {CSV_PATH}")
    print()


if __name__ == '__main__':
    main()
