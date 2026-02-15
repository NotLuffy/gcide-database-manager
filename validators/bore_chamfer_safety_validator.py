"""
Bore Chamfer Safety Validator

Validates Side 2 chamfer/bore setup positioning to prevent hub crashes.

CRITICAL SAFETY RULE:
When positioning for Side 2 chamfer/bore operations (G154/G55), the X value
must be at the PRE-CHAMFER position (close to CB), NOT at or near OD.

UNSAFE PATTERN (CRASH RISK):
    G154 P16 G00 X8.445 Z0.0    ; At OD, near part - DANGER!
    G00 X4.602                  ; Moving inward to CB - CRASH!

SAFE PATTERN:
    G154 P16 G00 X4.702 Z1.0    ; Pre-chamfer X (CB + margin), safe Z
    Z0.                         ; Approach to surface
    G01 X4.602 Z-0.1 F0.008    ; Chamfer to CB

The danger: Positioning at OD with Z at/near part surface, then moving inward
to CB causes the tool to crash into the hub material.
"""

import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class BoreChamferSafetyResult:
    """Result from bore chamfer safety validation"""
    critical_issues: List[str]
    warnings: List[str]
    notes: List[str]


class BoreChamferSafetyValidator:
    """Validates bore chamfer setup positioning for hub safety"""

    def __init__(self):
        # Distance from OD that's considered "at OD" (crash risk)
        self.od_proximity_critical = 1.0  # Within 1" of OD = critical
        self.od_proximity_warning = 1.5   # Within 1.5" of OD = warning

        # Maximum acceptable distance from CB for pre-chamfer position
        self.max_prechamfer_margin = 0.5  # CB + up to 0.5" is acceptable

    def validate_file(self, lines: List[str], outer_diameter: Optional[float],
                     center_bore: Optional[float], spacer_type: str) -> BoreChamferSafetyResult:
        """
        Validate bore chamfer setup positioning.

        Args:
            lines: G-code file lines
            outer_diameter: Outer diameter (round size) in inches
            center_bore: Center bore in mm
            spacer_type: Part type (should include 'hub_centric' for validation)

        Returns:
            BoreChamferSafetyResult with critical issues and warnings
        """
        critical_issues = []
        warnings = []
        notes = []

        # Only applies to hub-centric parts
        if 'hub_centric' not in spacer_type.lower():
            return BoreChamferSafetyResult([], [], [])

        # Need OD and CB for validation
        if not outer_diameter or not center_bore:
            return BoreChamferSafetyResult([], [], [])

        # Convert CB to inches for comparison
        cb_inches = center_bore / 25.4
        # OD turn-down is typically at X = OD - 0.055" (lathe in diameter mode)
        # For 7.5" part: OD turn-down ~X7.445
        od_turndown_x = outer_diameter - 0.055  # Standard OD turn-down X value

        # Track if we're on Side 2
        found_flip = False
        in_bore_chamfer = False
        tool_name = ""

        for i, line in enumerate(lines, 1):
            line_upper = line.upper()

            # Skip comments
            if line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            # Track flip to Side 2
            if 'M01' in line_upper or 'M1' in line_upper or 'FLIP' in line_upper:
                found_flip = True
                continue

            # Only check Side 2
            if not found_flip:
                continue

            # Remove inline comments
            code_part = line.split('(')[0] if '(' in line else line

            # Detect T121 bore/chamfer tool
            if 'T121' in code_part.upper():
                in_bore_chamfer = True
                # Extract tool comment if present
                if '(' in line:
                    tool_name = line[line.index('('):].strip()
                continue

            # Exit bore operation on new tool
            if in_bore_chamfer and re.match(r'^T\d+', code_part.strip(), re.IGNORECASE):
                in_bore_chamfer = False
                continue

            # Check G154/G55 positioning lines in bore/chamfer operations
            if in_bore_chamfer:
                # Look for G154 Pxx or G55 setup positioning
                if re.search(r'G154\s+P\d+|G55', code_part, re.IGNORECASE):
                    # Extract X value from this line or continuation
                    x_match = re.search(r'X\s*(-?\d+\.?\d*)', code_part, re.IGNORECASE)

                    if x_match:
                        setup_x = float(x_match.group(1))

                        # Check if X is dangerously close to OD
                        distance_from_od = od_turndown_x - setup_x
                        distance_from_cb = setup_x - cb_inches

                        # CRITICAL: Setup X is at or near OD (crash risk when moving inward)
                        if distance_from_od <= self.od_proximity_critical:
                            critical_issues.append(
                                f"BORE CHAMFER CRASH RISK - Side 2 Line {i}: "
                                f"Setup X{setup_x:.3f} is at OD (OD turndown ~X{od_turndown_x:.3f}) "
                                f"- Moving inward to CB (X{cb_inches:.3f}) will crash into hub! "
                                f"Use pre-chamfer X value (CB + 0.1-0.4\") instead"
                            )

                        # WARNING: Setup X is approaching OD
                        elif distance_from_od <= self.od_proximity_warning:
                            warnings.append(
                                f"Bore chamfer setup approaching OD - Side 2 Line {i}: "
                                f"Setup X{setup_x:.3f} is close to OD (~X{od_turndown_x:.3f}). "
                                f"Recommend using pre-chamfer X closer to CB (X{cb_inches:.3f})"
                            )

                        # NOTE: Proper pre-chamfer positioning
                        elif distance_from_cb <= self.max_prechamfer_margin and distance_from_cb > 0:
                            notes.append(
                                f"Side 2 Line {i}: Proper chamfer setup at X{setup_x:.3f} "
                                f"(CB + {distance_from_cb:.2f}\" margin)"
                            )

                        # Check for potentially incorrect positioning (inside CB)
                        elif setup_x < cb_inches:
                            warnings.append(
                                f"Bore chamfer setup inside CB - Side 2 Line {i}: "
                                f"Setup X{setup_x:.3f} is smaller than CB (X{cb_inches:.3f}). "
                                f"Verify this is intentional"
                            )

        return BoreChamferSafetyResult(
            critical_issues=critical_issues,
            warnings=warnings,
            notes=notes
        )


# Example usage and testing
if __name__ == "__main__":
    validator = BoreChamferSafetyValidator()

    # Test 1: SAFE pattern (from o86046)
    print("TEST 1: SAFE PATTERN (o86046)")
    print("=" * 80)

    test_safe = """
M01

T121 (CHAMFER BORE)
G50 S2200
G97 S1750 M03
G96 S950 M08
G154 P16 G00 X4.702 Z1.
Z0.
G01 X4.602 Z-0.1 F0.008

G00 Z0
G00 G53 X-11. Z-13.
M30
    """.strip().split('\n')

    result1 = validator.validate_file(
        lines=test_safe,
        outer_diameter=7.5,
        center_bore=116.7,  # 4.6" diameter
        spacer_type='hub_centric'
    )

    print("CRITICAL ISSUES:", len(result1.critical_issues))
    for issue in result1.critical_issues:
        print(f"  {issue}")
    print("WARNINGS:", len(result1.warnings))
    for warning in result1.warnings:
        print(f"  {warning}")
    print("NOTES:", len(result1.notes))
    for note in result1.notes:
        print(f"  {note}")

    # Test 2: UNSAFE pattern (positioned at OD)
    print("\n" + "=" * 80)
    print("TEST 2: UNSAFE PATTERN (positioned at OD)")
    print("=" * 80)

    test_unsafe = """
M01

T121 (CHAMFER BORE)
G50 S2200
G97 S1750 M03
G96 S950 M08
G154 P16 G00 X7.445 Z0.2
G00 X4.602
G01 Z-0.1 F0.008

G00 Z0
G00 G53 X-11. Z-13.
M30
    """.strip().split('\n')

    result2 = validator.validate_file(
        lines=test_unsafe,
        outer_diameter=7.5,
        center_bore=116.7,
        spacer_type='hub_centric'
    )

    print("CRITICAL ISSUES:", len(result2.critical_issues))
    for issue in result2.critical_issues:
        print(f"  {issue}")
    print("WARNINGS:", len(result2.warnings))
    for warning in result2.warnings:
        print(f"  {warning}")
    print("NOTES:", len(result2.notes))
    for note in result2.notes:
        print(f"  {note}")

    if result2.critical_issues:
        print("\n[PASS] Unsafe pattern correctly detected!")
