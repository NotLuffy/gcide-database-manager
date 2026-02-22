"""
G-Code Auto-Fixer Module
Automatically fixes common G-code issues like tool home positions and coolant sequence

Extracted from test_phase1/duplicate_with_scan_test.py for integration into main application
"""

import re
from typing import List, Tuple


class AutoFixer:
    """
    Automatic fixer for common G-code issues
    """

    @staticmethod
    def fix_tool_home_z(content, expected_z):
        """
        Fix tool home Z position

        Args:
            content: G-code file content
            expected_z: Expected Z value (e.g., -10.0)

        Returns:
            str: Fixed content
        """
        # Pattern: G43 H## Z-##.#
        pattern = r'(G43\s+H\d+\s+Z)(-?\d+\.?\d*)'

        def replace_z(match):
            return f"{match.group(1)}{expected_z}"

        fixed = re.sub(pattern, replace_z, content, flags=re.IGNORECASE)
        return fixed

    @staticmethod
    def fix_coolant_sequence(content):
        """
        Fix M09/M05 sequence - ensure M09 comes before M05

        Args:
            content: G-code file content

        Returns:
            str: Fixed content
        """
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # Check if this line has M05 but no M09 before it
            if 'M05' in line.upper():
                # Look at previous line
                if i > 0 and 'M09' not in fixed_lines[-1].upper():
                    # Insert M09 before this line
                    fixed_lines.append('M09')

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    # --- compiled patterns shared by fix_rapid_to_negative_z helpers ---
    _G00_PAT  = re.compile(r'\bG0*0\b', re.IGNORECASE)
    _Z_PAT    = re.compile(r'Z(-?\d+\.?\d*)', re.IGNORECASE)
    _F_PAT    = re.compile(r'F(\d+\.?\d*)', re.IGNORECASE)
    _TOOL_PAT = re.compile(r'\bT\d+\b', re.IGNORECASE)

    @staticmethod
    def _lookup_feedrate(code_part: str, prior_lines: List[str]) -> str:
        """Return best feedrate: on current line, recent prior line, or safe default."""
        m = AutoFixer._F_PAT.search(code_part)
        if m:
            return m.group(1)
        for prev in reversed(prior_lines[-60:]):
            fm = AutoFixer._F_PAT.search(prev.split('(')[0])
            if fm:
                return fm.group(1)
        return '0.008'

    @staticmethod
    def _inject_feedrate(line: str, feedrate: str) -> str:
        """Append F<feedrate> to a line, respecting any trailing inline comment."""
        code = line.split('(')[0].rstrip()
        if '(' in line:
            return code + f' F{feedrate} ' + line[line.index('('):]
        return code + f' F{feedrate}'

    @staticmethod
    def _is_deeper_negative(z_val: float, last_z) -> bool:
        """True when z_val is negative AND deeper than the last known Z."""
        return z_val < 0 and (last_z is None or z_val < last_z)

    @staticmethod
    def _fix_g00_z_line(line: str, z_val: float, prior_lines: List[str], line_num: int):
        """
        Convert a G00 Z-plunge line to G01 with feedrate.

        Returns (fixed_line, change_description).
        """
        feedrate   = AutoFixer._lookup_feedrate(line.split('(')[0], prior_lines)
        fixed_line = AutoFixer._G00_PAT.sub('G01', line, count=1)
        if not AutoFixer._F_PAT.search(fixed_line.split('(')[0]):
            fixed_line = AutoFixer._inject_feedrate(fixed_line, feedrate)
        return fixed_line, f"Line {line_num}: G00 Z{z_val} → G01 Z{z_val} F{feedrate}"

    @staticmethod
    def fix_rapid_to_negative_z(content: str) -> Tuple[str, List[str]]:
        """
        Fix explicit G00 rapid moves that plunge to negative Z by converting
        them to G01 (controlled feed) with an appropriate feedrate.

        Only lines with an EXPLICIT G00 are modified.  Modal G00 cases are
        left alone — modifying bare coordinate lines can shift the modal state
        for surrounding moves in unexpected ways.

        Returns:
            (fixed_content, changes)  — changes is a list of human-readable
            descriptions of every line that was modified.
        """
        lines = content.split('\n')
        fixed_lines: List[str] = []
        changes: List[str] = []
        last_z = None

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('%') or stripped.startswith('('):
                fixed_lines.append(line)
                continue

            code_part  = line.split('(')[0]
            code_upper = code_part.upper()

            if 'G53' in code_upper or AutoFixer._TOOL_PAT.search(code_upper):
                last_z = None
                fixed_lines.append(line)
                continue

            z_match = AutoFixer._Z_PAT.search(code_part)
            if z_match:
                z_val = float(z_match.group(1))
                is_g00_plunge = (AutoFixer._G00_PAT.search(code_part)
                                 and AutoFixer._is_deeper_negative(z_val, last_z))
                if is_g00_plunge:
                    fixed_line, desc = AutoFixer._fix_g00_z_line(line, z_val, fixed_lines, line_num)
                    fixed_lines.append(fixed_line)
                    changes.append(desc)
                    last_z = z_val
                    continue
                last_z = z_val

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), changes

    # Patterns shared by fix_modal_g00_z_plunge and fix_work_offset_z_clearance
    _G_CODE_PAT      = re.compile(r'\b(G0*[0-3])\b', re.IGNORECASE)
    _X_PAT           = re.compile(r'X(-?\d+\.?\d*)', re.IGNORECASE)
    _WORK_OFFSET_PAT = re.compile(r'\b(G55|G154\s*P\d+|G155)\b', re.IGNORECASE)
    _Z_WORD_PAT      = re.compile(r'Z(-?\d+\.?\d*)', re.IGNORECASE)
    _CANNED_PAT      = re.compile(r'\bG8[0-9]\b', re.IGNORECASE)   # G80-G89 canned cycles

    @staticmethod
    def fix_work_offset_z_clearance(content: str) -> Tuple[str, List[str]]:
        """
        Ensure G55 / G154 P## / G155 positioning lines approach with Z >= 1.0,
        then insert a G00 Z0.2 working-clearance rapid immediately after so the
        subsequent G01 feed only travels from Z0.2, not the full inch from Z1.

        Applies to all tools — turning, chamfer bore, bore, and drill.

        Example:
            BEFORE:
                G55 G00 X8.55 Z0.1 M08    ← too low, and G01 would feed from Z0.1
                G01 Z-0.1 F0.013

            AFTER:
                G55 G00 X8.55 Z1. M08     ← safe positioning clearance
                G00 Z0.2                   ← rapid to working clearance
                G01 Z-0.1 F0.013          ← feed starts from Z0.2, not Z1.

        If a G00 to positive Z already follows the work-offset line, the
        G00 Z0.2 insertion is skipped to avoid redundant rapid moves.
        X and all other words on the original line are left unchanged.
        """
        lines  = content.split('\n')
        output: List[str] = []
        changes: List[str] = []

        for i, line in enumerate(lines):
            line_num  = i + 1
            code_part = line.split('(')[0]

            if AutoFixer._WORK_OFFSET_PAT.search(code_part):
                z_match = AutoFixer._Z_WORD_PAT.search(code_part)
                if z_match:
                    z_val = float(z_match.group(1))
                    if z_val < 1.0:
                        # Fix Z to Z1. on the positioning line
                        new_code = AutoFixer._Z_WORD_PAT.sub('Z1.', code_part, count=1)
                        suffix   = line[len(code_part):]
                        output.append(new_code + suffix)

                        # Check if the next non-empty / non-comment line is
                        # already a G00 to a positive Z — if so, skip insert
                        already_clear = False
                        for j in range(i + 1, min(i + 6, len(lines))):
                            nxt = lines[j].strip()
                            if not nxt or nxt.startswith('(') or nxt.startswith('%'):
                                continue
                            nxt_code = lines[j].split('(')[0]
                            if AutoFixer._G00_PAT.search(nxt_code):
                                zm = AutoFixer._Z_WORD_PAT.search(nxt_code)
                                if zm and float(zm.group(1)) > 0:
                                    already_clear = True
                            break   # only look at the first real line

                        if not already_clear:
                            indent = line[:len(line) - len(line.lstrip())]
                            output.append(f"{indent}G00 Z0.2")
                            changes.append(
                                f"Line {line_num}: work offset Z{z_val} → Z1."
                                f" + G00 Z0.2  [{code_part.strip()[:50]}]"
                            )
                        else:
                            changes.append(
                                f"Line {line_num}: work offset Z{z_val} → Z1."
                                f"  [{code_part.strip()[:50]}]"
                            )
                        continue
            output.append(line)

        return '\n'.join(output), changes

    @staticmethod
    def fix_modal_g00_z_plunge(content: str) -> Tuple[str, List[str]]:
        """
        Fix bare Z-plunge lines that execute as modal G00 rapids.

        A "modal G00 plunge" is a line containing only a Z coordinate (e.g.
        'Z-0.005') where the active G-code modal state is G00 — making it a
        rapid plunge into material with no feed rate protection.

        Fix applied to each detected line:
          1. Insert 'G00 Z0.2' before it  (safe clearance approach)
          2. Prepend 'G01' and append feedrate looked up from the NEXT lines

        Before:
            G55 G00 X5.794 Z1.
            Z-0.005                  ← modal G00 rapid plunge — CRASH RISK

        After:
            G55 G00 X5.794 Z1.
            G00 Z0.2                 ← safe clearance
            G01 Z-0.005 F0.008       ← controlled feed entry

        Returns:
            (fixed_content, changes)  — changes is a list of human-readable
            descriptions of every line modified.
        """
        lines = content.split('\n')
        output:  List[str] = []
        changes: List[str] = []

        active_g = None   # current modal G-code (G00, G01, G02, G03)
        last_z   = None   # most recent Z value seen

        def _lookahead_f(start: int) -> str:
            """Scan forward from start for the first F value."""
            for j in range(start, min(start + 60, len(lines))):
                code = lines[j].split('(')[0]
                m = AutoFixer._F_PAT.search(code)
                if m:
                    return m.group(1)
            return '0.008'

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('%') or stripped.startswith('('):
                output.append(line)
                continue

            code_part  = line.split('(')[0]
            code_upper = code_part.upper()

            # Tool change or tool-home resets modal state
            if 'G53' in code_upper or AutoFixer._TOOL_PAT.search(code_upper):
                active_g = None
                last_z   = None
                output.append(line)
                continue

            # Canned cycle lines (G80-G89) are handled by the controller — skip
            if AutoFixer._CANNED_PAT.search(code_upper):
                output.append(line)
                continue

            # Update modal G-code from any explicit G0x on this line
            g_match = AutoFixer._G_CODE_PAT.search(code_upper)
            if g_match:
                raw = g_match.group(1).upper()
                active_g = ('G0' + raw[1]) if len(raw) == 2 else raw

            # Check for a bare Z-only plunge under modal G00
            z_match = AutoFixer._Z_PAT.search(code_part)
            if z_match:
                z_val = float(z_match.group(1))
                is_modal_g00 = (active_g == 'G00') and (not g_match)
                is_z_only    = not AutoFixer._X_PAT.search(code_part)
                is_plunge    = z_val < 0 and (last_z is None or z_val < last_z)

                if is_modal_g00 and is_z_only and is_plunge:
                    feedrate = _lookahead_f(i + 1)
                    indent   = line[:len(line) - len(line.lstrip())]

                    # 1. Safe clearance approach
                    output.append(f"{indent}G00 Z0.2")

                    # 2. Controlled feed line (preserve any inline comment)
                    code_stripped = code_part.strip()
                    fixed = f"{indent}G01 {code_stripped}"
                    if not AutoFixer._F_PAT.search(fixed):
                        fixed += f" F{feedrate}"
                    if '(' in line:
                        fixed += ' ' + line[line.index('('):]

                    output.append(fixed)
                    changes.append(
                        f"Line {i + 1}: modal G00 Z{z_val} → G00 Z0.2 + G01 Z{z_val} F{feedrate}"
                    )
                    last_z = z_val
                    continue

                last_z = z_val

            output.append(line)

        return '\n'.join(output), changes

    @staticmethod
    def fix_g01_missing_feedrate(content: str) -> Tuple[str, List[str]]:
        """
        Ensure every G01 that opens a new feed-mode block carries an F word.

        Rule: when the active modal changes from anything other than G01 to G01
        (explicit G01 on the line), and that line has no F word, inject the last
        known feedrate seen anywhere earlier in the file.

        Canned-cycle lines (G80-G89), tool-change lines, and G53 lines are
        skipped (they don't affect the feed modal and need no correction).

        Example (o48501 line 129):
            G00 Z0.1          ← modal G00
            G01 Z-0.005       ← switches to G01, NO F  ← fixed to G01 Z-0.005 F0.007
            G01 X4.878 F0.007 ← continuing G01 modal, F present — OK
        """
        lines  = content.split('\n')
        output: List[str] = []
        changes: List[str] = []

        active_g = None
        last_f   = None

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('%') or stripped.startswith('('):
                output.append(line)
                continue

            code_part  = line.split('(')[0]
            code_upper = code_part.upper()

            # Tool change / tool-home resets modal state
            if 'G53' in code_upper or AutoFixer._TOOL_PAT.search(code_upper):
                active_g = None
                output.append(line)
                f_m = AutoFixer._F_PAT.search(code_part)
                if f_m:
                    last_f = f_m.group(1)
                continue

            # Canned cycles: skip (controller manages their internal motion)
            if AutoFixer._CANNED_PAT.search(code_upper):
                output.append(line)
                f_m = AutoFixer._F_PAT.search(code_part)
                if f_m:
                    last_f = f_m.group(1)
                continue

            g_match = AutoFixer._G_CODE_PAT.search(code_upper)
            if g_match:
                raw_g  = g_match.group(1).upper()
                new_g  = ('G0' + raw_g[-1]) if len(raw_g) == 2 else raw_g

                # G00→G01 (or G02/G03→G01, or None→G01) transition without F
                if new_g == 'G01' and active_g != 'G01':
                    if not AutoFixer._F_PAT.search(code_part):
                        feedrate = last_f if last_f else '0.008'
                        line = AutoFixer._inject_feedrate(line, feedrate)
                        changes.append(
                            f"Line {i}: G01 transition missing F → added F{feedrate}"
                            f"  [{code_part.strip()[:50]}]"
                        )

                active_g = new_g

            # Track last F seen on any line
            f_m = AutoFixer._F_PAT.search(code_part)
            if f_m:
                last_f = f_m.group(1)

            output.append(line)

        return '\n'.join(output), changes

    @staticmethod
    def apply_all_fixes(content, scan_results):
        """
        Apply all applicable fixes based on scan results

        Args:
            content: G-code file content
            scan_results: Results from FileScanner

        Returns:
            tuple: (fixed_content, list of fixes applied)
        """
        fixes_applied = []
        fixed = content

        # Check for tool home issues
        if scan_results['warnings']:
            for warning in scan_results['warnings']:
                msg = warning['message'].lower()

                # Fix tool home Z
                if 'tool home' in msg and 'z' in msg:
                    # Try to extract expected Z value from message
                    match = re.search(r'expected.*?z-?(\d+\.?\d*)', msg, re.IGNORECASE)
                    if match:
                        expected_z = f"-{match.group(1)}"
                        fixed = AutoFixer.fix_tool_home_z(fixed, expected_z)
                        fixes_applied.append(f"Fixed tool home Z to {expected_z}")

                # Fix M09/M05 sequence
                if 'm09' in msg and 'm05' in msg:
                    fixed = AutoFixer.fix_coolant_sequence(fixed)
                    fixes_applied.append("Fixed M09/M05 sequence")

        return fixed, fixes_applied
