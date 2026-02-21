"""
OD Turn-Down Validator
Validates that OD turn-down values match common practice standards

Common Practice:
- In T303 (TURN TOOL) operations on both Side 1 and Side 2
- Find the G01 X value that comes RIGHT BEFORE the line that cuts down the side (Z negative)
- This X value should match the standard OD turn-down for that round size

Example from o75974 (7.5" round):
  G01 x7.445 Z0.1 F0.015   <- X value before cutting
  G01 Z-0.35 F0.012         <- Cutting down the side
  -> X7.445 is the standard for 7.5" rounds
"""

import re
from typing import List, Tuple, Optional

class ODTurnDownValidator:
    """Validates OD turn-down values match common practice standards"""

    # Standard OD turn-down values by round size (in inches)
    STANDARD_OD_TURNDOWN = {
        5.75: 5.700,
        6.00: 5.950,
        6.25: 6.200,
        6.50: 6.450,
        7.00: 6.945,   # From production data: 620/729 samples (85.0%)
        7.50: 7.445,
        8.00: 7.945,
        8.50: 8.440,
        9.50: 9.450,
        10.25: 10.170,
        10.50: 10.450,
        13.00: 12.903,
    }

    def __init__(self):
        self.tolerance = 0.01  # ±0.01" tolerance

    def validate_file(self, lines: List[str], round_size: Optional[float]) -> Tuple[List[str], List[str]]:
        """
        Validate OD turn-down values in a G-code file.

        Args:
            lines: G-code file lines
            round_size: Round size of the part

        Returns:
            (warnings, notes) - Lists of validation messages
        """
        warnings = []
        notes = []

        # Skip if no round size or not a standard size
        if not round_size or round_size not in self.STANDARD_OD_TURNDOWN:
            return warnings, notes

        standard_od = self.STANDARD_OD_TURNDOWN[round_size]

        # Find T303 (TURN TOOL) operations and extract OD turn-down values
        in_turn_tool = False
        side = None

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Track which side we're on
            if 'FLIP PART' in line_upper or 'SIDE 2' in line_upper:
                side = 2
            elif i < 100 and 'SIDE 1' in line_upper:
                side = 1
            elif side is None and i < 100:
                side = 1  # Assume Side 1 if not specified

            # Detect T303 TURN TOOL operations
            if 'T303' in line_upper or ('T3' in line_upper and 'TURN' in line_upper):
                in_turn_tool = True
                continue

            # Exit turn tool operation when another tool is called
            if in_turn_tool and re.match(r'T\d+', line_upper):
                in_turn_tool = False

            # Look for OD turn-down pattern in T303 operations
            if in_turn_tool and 'G01' in line_upper:
                # Check if this line has an X value
                x_match = re.search(r'X\s*(-?\d+\.?\d*)', line_upper)
                if x_match:
                    x_value = float(x_match.group(1))

                    # Filter 1: X must be in OD territory (within 1.0" of standard).
                    # Hub face plunges (X3.x for a 6.25" round) are not OD turn-downs.
                    if x_value < standard_od - 1.0:
                        continue

                    # Check if next line is cutting down the side (G01 Z-negative)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].upper()
                        if 'G01' in next_line:
                            z_match = re.search(r'Z\s*(-\d+\.?\d*)', next_line)
                            if z_match:
                                # Filter 2: Z depth must be meaningful (>= 0.10").
                                # Hub face cleanup passes (Z-0.06) are not OD turn-downs.
                                z_value = abs(float(z_match.group(1)))
                                if z_value < 0.10:
                                    continue

                                # Found OD turn-down! Check if it matches standard
                                side_str = f"Side {side}" if side else "unknown side"

                                if abs(x_value - standard_od) <= self.tolerance:
                                    notes.append(
                                        f"{side_str}: OD turn-down X{x_value:.3f}\" matches standard (X{standard_od:.3f}\")"
                                    )
                                else:
                                    warnings.append(
                                        f"OUT OF COMMON PRACTICE - {side_str}: OD turn-down X{x_value:.3f}\" "
                                        f"does not match standard X{standard_od:.3f}\" for {round_size:.2f}\" rounds "
                                        f"(Line {i+1})"
                                    )

        return warnings, notes

    def get_standard_od(self, round_size: float) -> Optional[float]:
        """Get the standard OD turn-down value for a given round size"""
        return self.STANDARD_OD_TURNDOWN.get(round_size)


# Example usage
if __name__ == "__main__":
    validator = ODTurnDownValidator()

    # Test with o75974 example
    test_gcode = """
T303 (TURN TOOL)
G97 S2350 M03
M31
G00 G154 P3 X7.46 Z0.15 M08 (X IS OD)
G96 S1200 (CCS ON)
G01 x7.445 Z0.1 F0.015
G01 Z-0.35 F0.012
x7.46
G00 Z-0.05
x7.445
G01 x7.4 Z0. F0.006
G01 X3.8 Z0. F0.016
G00 Z0.1 M09
    """.strip().split('\n')

    warnings, notes = validator.validate_file(test_gcode, 7.50)

    print("Test Results for 7.5\" round:")
    print("=" * 60)
    if notes:
        print("Notes:")
        for note in notes:
            print(f"  OK: {note}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  WARNING: {warning}")
    if not notes and not warnings:
        print("  No OD turn-down detected")
