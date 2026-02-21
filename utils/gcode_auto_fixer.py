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
