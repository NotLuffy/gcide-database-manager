"""
Crash Prevention Validator
Detects dangerous G-code patterns that can cause machine crashes.

Critical crash scenarios:
1. G00 rapid to negative Z (tool crashes into part)
2. Diagonal rapid movements with negative Z
3. Negative Z position before tool home
4. Jaw clearance violations

Based on real-world crash analysis and shop floor experience.
"""

import re
from typing import List, Tuple, Dict, Optional


class CrashPreventionValidator:
    """Validates G-code for crash-prone patterns"""

    def __init__(self):
        self.crash_issues = []
        self.crash_warnings = []

    def validate_all_crash_patterns(self, lines: List[str], parse_result=None) -> Dict:
        """
        Run all crash prevention checks.

        Args:
            lines: G-code file lines
            parse_result: Optional GCodeParseResult for context (thickness, etc.)

        Returns:
            Dictionary with crash_issues and crash_warnings lists
        """
        self.crash_issues = []
        self.crash_warnings = []

        # CRITICAL: G00 rapid to negative Z
        self._detect_rapid_to_negative_z(lines)

        # CRITICAL: Diagonal rapids with negative Z
        self._detect_diagonal_rapids_negative_z(lines)

        # CRITICAL: Negative Z before tool home (G53)
        self._detect_negative_z_before_tool_home(lines)

        # WARNING: Jaw clearance violations (if we have thickness)
        if parse_result and parse_result.thickness:
            self._detect_jaw_clearance_violations(lines, parse_result)

        # WARNING: Missing safety clearance before operations
        self._detect_missing_safety_clearance(lines)

        return {
            'crash_issues': self.crash_issues,
            'crash_warnings': self.crash_warnings
        }

    def _detect_rapid_to_negative_z(self, lines: List[str]):
        """
        Detect G00 rapid movements to negative Z that go DEEPER than current position.
        NOW WITH MODAL STATE TRACKING!

        CRITICAL CRASH RISK: Rapid into uncut material will crash tool.

        Safe:   G01 Z-2.5 F0.02  (feed into part - controlled cut)
        UNSAFE: G00 Z-2.5        (rapid into uncut material - CRASH!)
        SAFE:   G00 Z-0.05       (when last Z was -1.5, this is retraction toward surface)

        MODAL STATE TRACKING:
        - G00, G01, G02, G03 remain active until changed
        - Lines with just coordinates (e.g., "Z-0.09") use the active modal G-code
        - Pattern: "G154 P## G00" followed by "Z-0.09" → treats Z move as G00 rapid

        Key rule: If last Z was deeper (more negative) than target Z, material
        was already cut at the target depth, so rapid is safe (retraction).

        Note: Skips G53 lines - tool home uses machine coordinates
        """
        # Patterns to detect G-codes and coordinates
        g_code_pattern = re.compile(r'\b(G0*[0123])\b', re.IGNORECASE)  # Matches G00, G01, G02, G03, G0, G1, G2, G3
        canned_cycle_pattern = re.compile(r'\b(G7[3-6]|G8[0-9])\b', re.IGNORECASE)  # G73-G76, G80-G89 (drilling/boring cycles)
        z_pattern = re.compile(r'Z(-?\d+\.?\d*)', re.IGNORECASE)

        # Modal state tracking
        active_g_code = None  # Tracks current modal G-code (G00, G01, etc.)
        last_z = None  # Track current Z position (None = at home/positive/unknown)

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            # Remove inline comments
            code_part = line.split('(')[0] if '(' in line else line
            code_upper = code_part.upper()

            # Skip G53 lines and reset tracking (tool returns to home)
            if 'G53' in code_upper:
                last_z = None
                active_g_code = None  # Reset modal state at tool home
                continue

            # Reset modal state on tool change
            if re.search(r'\bT\d+\b', code_upper):
                last_z = None
                active_g_code = None
                continue

            # Check for canned cycles (G73-G89) - these are NOT rapids
            # Canned cycles are controlled feed operations
            canned_match = canned_cycle_pattern.search(code_upper)
            if canned_match:
                cycle_code = canned_match.group(1).upper()
                # Set modal state to the canned cycle (not G00)
                active_g_code = cycle_code
                # Don't continue - let G00/G01 check override if present on same line

            # Check for explicit G-code (G00, G01, G02, G03)
            # This can override canned cycles if both appear on same line (e.g., "G00 G80")
            g_match = g_code_pattern.search(code_upper)
            if g_match:
                # Update modal state - normalize to G00, G01, G02, G03 format
                g_code = g_match.group(1).upper()
                # Normalize: G0 → G00, G1 → G01, G2 → G02, G3 → G03
                if len(g_code) == 2:  # G0, G1, G2, G3
                    g_code = 'G0' + g_code[1]
                active_g_code = g_code

            # Check for Z movement
            z_match = z_pattern.search(code_part)
            if z_match:
                z_value = float(z_match.group(1))

                # Check if this is a G00 rapid movement (explicit or modal)
                is_rapid = (active_g_code == 'G00')

                if is_rapid:
                    # CRITICAL: Rapid to negative Z that goes DEEPER than current position
                    # If last_z is None (at home/unknown), any negative Z is crash risk
                    # If last_z is known, only flag if going deeper (more negative)
                    if z_value < 0 and (last_z is None or z_value < last_z):
                        # Determine if explicit or modal
                        move_type = "explicit G00" if 'G00' in code_upper or 'G0 ' in code_upper else f"modal G00 (line has no G-code, using active {active_g_code})"

                        self.crash_issues.append(
                            f"Line {line_num}: CRASH RISK - {move_type} rapid to Z{z_value:.3f}. "
                            f"Must use G01 (feed) when going deeper. "
                            f"Change to: G01 Z{z_value:.3f} F[feedrate]"
                        )

                # Update last Z position regardless of move type
                last_z = z_value

    def _detect_diagonal_rapids_negative_z(self, lines: List[str]):
        """
        Detect diagonal rapid movements (X and Z on same line) with negative Z
        that goes DEEPER than current position.
        NOW WITH MODAL STATE TRACKING!

        CRITICAL CRASH RISK: Diagonal rapid into uncut material can crash.

        Safe:   G00 Z0.2  then  X3.0  (retract first, then move)
        UNSAFE: G00 X3.0 Z-0.5        (diagonal into uncut material - CRASH!)

        MODAL STATE TRACKING:
        - Detects diagonal moves even when G00 is modal (not explicit on the line)
        - Pattern: "G00 X3.0" followed by "X2.5 Z-0.5" → treats as G00 diagonal

        Note: Skips G53 lines - tool home uses machine coordinates
        """
        # Patterns to detect G-codes and coordinates
        g_code_pattern = re.compile(r'\b(G0*[0123])\b', re.IGNORECASE)
        canned_cycle_pattern = re.compile(r'\b(G7[3-6]|G8[0-9])\b', re.IGNORECASE)  # G73-G76, G80-G89 (drilling/boring cycles)
        x_pattern = re.compile(r'X(-?\d+\.?\d*)', re.IGNORECASE)
        z_pattern = re.compile(r'Z(-?\d+\.?\d*)', re.IGNORECASE)

        # Modal state tracking
        active_g_code = None  # Tracks current modal G-code (G00, G01, etc.)
        last_z = None  # Track current Z position (None = at home/positive/unknown)

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            # Remove inline comments
            code_part = line.split('(')[0] if '(' in line else line
            code_upper = code_part.upper()

            # Skip G53 lines and reset tracking (tool returns to home)
            if 'G53' in code_upper:
                last_z = None
                active_g_code = None
                continue

            # Reset modal state on tool change
            if re.search(r'\bT\d+\b', code_upper):
                last_z = None
                active_g_code = None
                continue

            # Check for canned cycles FIRST (G73-G89) - these override motion modes
            canned_match = canned_cycle_pattern.search(code_upper)
            if canned_match:
                cycle_code = canned_match.group(1).upper()
                active_g_code = cycle_code
                # Don't skip - we still want to track Z positions from cycle definitions

            # Check for explicit G-code
            g_match = g_code_pattern.search(code_upper)
            if g_match:
                g_code = g_match.group(1).upper()
                # Normalize: G0 → G00, G1 → G01, etc.
                if len(g_code) == 2:
                    g_code = 'G0' + g_code[1]
                active_g_code = g_code

            # Check for diagonal movement (both X and Z on same line)
            x_match = x_pattern.search(code_part)
            z_match = z_pattern.search(code_part)

            if x_match and z_match:
                # Both X and Z on same line - check if it's a rapid
                z_value = float(z_match.group(1))

                # Check if this is a G00 rapid movement (explicit or modal)
                is_rapid = (active_g_code == 'G00')

                if is_rapid:
                    # Only flag if going DEEPER than current position
                    if z_value < 0 and (last_z is None or z_value < last_z):
                        # Determine if explicit or modal
                        move_type = "explicit G00" if 'G00' in code_upper or 'G0 ' in code_upper else f"modal G00 (line has no G-code, using active {active_g_code})"

                        self.crash_issues.append(
                            f"Line {line_num}: CRASH RISK - Diagonal {move_type} rapid with Z{z_value:.3f}. "
                            f"Never use G00 for diagonal moves going deeper. "
                            f"Separate into: G00 Z[positive] then X[value]"
                        )

                last_z = z_value
            elif z_match:
                # Only Z movement - track position
                last_z = float(z_match.group(1))

    def _detect_negative_z_before_tool_home(self, lines: List[str]):
        """
        Detect negative Z position before G53 tool home.

        CRITICAL CRASH RISK: Tool home with tool at negative Z will crash.

        Rules:
        - Z < 0 before G53 → CRITICAL ERROR (crash risk)
        - Z >= 0 before G53 → PASS (safe)
        - No Z movement before G53 → PASS (tool starts at home)
        - Best practice: Z0.2 provides safety margin

        Note: This overlaps with existing tool_home_status validation,
        but provides additional context as a crash prevention check.
        """
        # Pattern to match G53 (tool home)
        g53_pattern = re.compile(r'G53', re.IGNORECASE)

        # Pattern to extract Z position
        z_pattern = re.compile(r'Z(-?\d+\.?\d*)', re.IGNORECASE)

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            if g53_pattern.search(line):
                # Skip very early G53 commands (first 10 lines) - these are initialization
                # The tool starts at home, so no need to check
                if line_num <= 10:
                    continue

                # Found G53 - look back for last Z position (but NOT on the G53 line itself)
                last_z = None
                last_z_line = None

                # Look back up to 30 lines (but start from line BEFORE the G53)
                lookback_start = max(0, line_num - 31)
                for prev_line_num in range(line_num - 1, lookback_start, -1):
                    prev_line = lines[prev_line_num - 1] if prev_line_num > 0 else ""

                    # Skip comments
                    if prev_line.strip().startswith('(') or prev_line.strip().startswith('%'):
                        continue

                    # Skip empty/whitespace lines
                    if not prev_line.strip():
                        continue

                    # Remove inline comments
                    code_part = prev_line.split('(')[0] if '(' in prev_line else prev_line

                    # Look for Z movement (ignore if line contains G53 - don't look at G53 lines)
                    if 'G53' not in code_part.upper():
                        z_match = z_pattern.search(code_part)
                        if z_match:
                            last_z = float(z_match.group(1))
                            last_z_line = prev_line_num
                            break

                # CRITICAL: Z negative before G53 = crash risk
                # If no Z movement found (last_z is None), assume safe (tool at home)
                if last_z is not None and last_z < 0:
                    self.crash_issues.append(
                        f"Line {line_num}: CRASH RISK - G53 tool home with Z{last_z:.3f} "
                        f"(from line {last_z_line}). Tool must be at Z0 or positive before tool home. "
                        f"Add: G00 Z0.2 before G53 (best practice for safety margin)"
                    )
                # PASS: Z0 or positive is safe, or no Z movement found (tool at home)

    def _detect_jaw_clearance_violations(self, lines: List[str], parse_result):
        """
        Detect Z-depth movements that violate jaw clearance.

        WARNING: Jaws come up 0.3" from spindle.
        Rules:
        - CAUTION WARNING: total_height - 0.4" = approaching limit (be careful)
        - CRITICAL WARNING: total_height - 0.3" = hard limit (may collide)

        For hub-centric parts: total_height = thickness + hub_height
        For standard parts: total_height = thickness

        Only applies to turning tool operations (T3xx) - drills and bore bars
        operate inside the bore and don't interfere with jaws.

        This is only checked for the first half of the program (before M01/flip).
        """
        jaw_clearance_critical = 0.3  # inches - hard limit
        jaw_clearance_caution = 0.4   # inches - caution zone

        # Calculate total height (thickness + hub for hub-centric parts)
        thickness = parse_result.thickness
        hub_height = getattr(parse_result, 'hub_height', None) or 0.0
        total_height = thickness + hub_height

        max_safe_depth_critical = total_height - jaw_clearance_critical
        max_safe_depth_caution = total_height - jaw_clearance_caution

        # Pattern to extract Z depth (negative values)
        z_pattern = re.compile(r'Z(-\d+\.?\d*)', re.IGNORECASE)

        # Pattern to track tool changes
        tool_pattern = re.compile(r'T(\d+)', re.IGNORECASE)

        # Track if we've hit M01 (flip marker)
        found_flip = False

        # Track current tool - jaw clearance only applies to T3 (turning tool)
        is_turning_tool = False

        # Track which lines we've already warned about to avoid duplicates
        warned_lines = set()

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            # Check for M01 (optional stop - usually indicates flip)
            if 'M01' in line.upper() or 'M1' in line.upper():
                found_flip = True
                break  # Only check first half

            # Remove inline comments
            code_part = line.split('(')[0] if '(' in line else line

            # Skip G53 lines (tool home uses machine coordinates)
            if 'G53' in code_part.upper():
                continue

            # Track tool changes - jaw clearance only applies to T3 (turning tool)
            tool_match = tool_pattern.search(code_part)
            if tool_match:
                tool_num = tool_match.group(1)
                # T3xx = turning tool (first digit is 3)
                is_turning_tool = tool_num[0] == '3'

            # Skip jaw clearance check for non-turning tools
            if not is_turning_tool:
                continue

            # Look for Z movements
            z_match = z_pattern.search(code_part)
            if z_match:
                z_depth = abs(float(z_match.group(1)))  # Get absolute value

                # CRITICAL: Exceeds hard limit (0.3" clearance)
                if z_depth > max_safe_depth_critical:
                    if line_num not in warned_lines:
                        # Build descriptive message with hub info if applicable
                        if hub_height > 0:
                            part_desc = f"{total_height:.3f}\" total height ({thickness:.3f}\" + {hub_height:.3f}\" hub)"
                        else:
                            part_desc = f"{thickness:.3f}\" thick part"

                        self.crash_warnings.append(
                            f"Line {line_num}: JAW CLEARANCE CRITICAL - Z-{z_depth:.3f} exceeds safe depth "
                            f"(max: {max_safe_depth_critical:.3f}\" for {part_desc}). "
                            f"Jaws extend 0.3\" - may collide with tool."
                        )
                        warned_lines.add(line_num)

                # CAUTION: Approaching limit (0.4" clearance zone)
                elif z_depth > max_safe_depth_caution:
                    if line_num not in warned_lines:
                        # Build descriptive message with hub info if applicable
                        if hub_height > 0:
                            part_desc = f"{total_height:.3f}\" total height ({thickness:.3f}\" + {hub_height:.3f}\" hub)"
                        else:
                            part_desc = f"{thickness:.3f}\" thick part"

                        self.crash_warnings.append(
                            f"Line {line_num}: JAW CLEARANCE CAUTION - Z-{z_depth:.3f} is close to jaw limit "
                            f"({max_safe_depth_caution:.3f}\" - {max_safe_depth_critical:.3f}\" range for {part_desc}). "
                            f"Be careful - approaching 0.3\" jaw clearance limit."
                        )
                        warned_lines.add(line_num)

    def _detect_missing_safety_clearance(self, lines: List[str]):
        """
        Detect operations that move to negative Z without safety clearance.

        WARNING: Moving directly from one negative Z to another without
        retracting can indicate missing safety clearance.

        Pattern to watch:
        G01 Z-2.5  (cutting deep)
        X3.0       (move in X while still deep - might crash if not careful)

        Safe pattern:
        G01 Z-2.5  (cutting)
        G00 Z0.2   (retract first)
        X3.0       (then move in X)
        """
        # This is a more nuanced check - looking for X movements after negative Z
        # without intermediate Z retraction

        z_pattern = re.compile(r'Z(-?\d+\.?\d*)', re.IGNORECASE)
        x_pattern = re.compile(r'X(-?\d+\.?\d*)', re.IGNORECASE)

        last_z = None
        last_z_line = None

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            # Remove inline comments
            code_part = line.split('(')[0] if '(' in line else line

            # Check for Z movement
            z_match = z_pattern.search(code_part)
            if z_match:
                last_z = float(z_match.group(1))
                last_z_line = line_num

            # Check for X movement without Z on same line
            x_match = x_pattern.search(code_part)
            if x_match and not z_match:  # X movement without Z
                # If last Z was negative and no retraction happened
                if last_z is not None and last_z < 0:
                    # Check if this is a G00 or G01
                    if 'G00' in code_part.upper() or 'G0' in code_part.upper():
                        # This might be okay if it's a radial retraction (moving away from center)
                        # We'd need more context to be sure, so just warn
                        pass  # Too many false positives - skip this check for now

    def format_crash_report(self, crash_issues: List[str], crash_warnings: List[str]) -> str:
        """
        Generate human-readable crash prevention report.

        Args:
            crash_issues: List of critical crash risks
            crash_warnings: List of crash warnings

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("="*60)
        lines.append("  CRASH PREVENTION ANALYSIS")
        lines.append("="*60)
        lines.append("")

        if crash_issues:
            lines.append(f"🔴 CRITICAL CRASH RISKS ({len(crash_issues)}):")
            lines.append("-" * 60)
            for issue in crash_issues:
                lines.append(f"  {issue}")
                lines.append("")
        else:
            lines.append("✅ No critical crash risks detected")
            lines.append("")

        if crash_warnings:
            lines.append(f"⚠️  CRASH WARNINGS ({len(crash_warnings)}):")
            lines.append("-" * 60)
            for warning in crash_warnings:
                lines.append(f"  {warning}")
                lines.append("")

        if not crash_issues and not crash_warnings:
            lines.append("All crash prevention checks passed! ✅")

        return "\n".join(lines)


def validate_crash_patterns(lines: List[str], parse_result=None) -> Dict:
    """
    Convenience function to run all crash prevention checks.

    Args:
        lines: G-code file lines
        parse_result: Optional GCodeParseResult for context

    Returns:
        Dictionary with crash_issues and crash_warnings
    """
    validator = CrashPreventionValidator()
    return validator.validate_all_crash_patterns(lines, parse_result)
