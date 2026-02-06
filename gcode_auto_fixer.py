"""
G-Code Auto-Fixer Module
Automatically fixes common G-code issues like tool home positions and coolant sequence

Extracted from test_phase1/duplicate_with_scan_test.py for integration into main application
"""

import re


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
