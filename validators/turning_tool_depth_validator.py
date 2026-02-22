"""
Turning Tool Depth Validator

Validates turning tool (T3xx) operations against production-proven depth standards.
These standards are MORE CONSERVATIVE than absolute jaw clearance limits for safety and best practices.

Standard Depth Limits by Total Thickness:
- Absolute jaw clearance limit: total_height - 0.3" (MUST NOT EXCEED)
- Standard depth limits: Production-proven safe depths (RECOMMENDED)

The standard limits provide a safety buffer beyond the hard jaw clearance limits.
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TurningDepthResult:
    """Result from turning tool depth validation"""
    warnings: List[str]
    notes: List[str]
    total_height: Optional[float]
    standard_max_depth: Optional[float]


class TurningToolDepthValidator:
    """Validates turning tool depth against production standards"""

    # Production-proven standard depth limits by total thickness
    # Format: {total_thickness: max_z_depth}
    #
    # For parts < 2.00": conservative limits account for stock sizing variation
    #   (~0.15" tolerance) which is a significant % of thin stock.
    #   Formula keeps ~0.15" buffer even on undersized stock.
    #
    # For parts >= 2.00": liberal limits using (total - 0.50").
    #   Jaw limit = total - 0.30".  New limit leaves 0.20" buffer at ideal
    #   stock and 0.05" buffer if stock is 0.15" undersized — acceptable
    #   because 0.15" variation is a much smaller % of thick stock.
    STANDARD_DEPTH_LIMITS = {
        0.75: 0.35,
        1.00: 0.55,
        1.25: 0.70,
        1.50: 0.80,
        1.75: 1.00,
        2.00: 1.50,
        2.25: 1.75,
        2.50: 2.00,
        2.75: 2.25,
        3.00: 2.50,
        3.25: 2.75,
        3.50: 3.00,
        3.75: 3.25,
        4.00: 3.50,
    }

    def __init__(self):
        self.tolerance = 0.05  # Allow 0.05" tolerance for standard limits

    def get_standard_depth(self, total_thickness: float) -> Optional[float]:
        """
        Get standard max depth for a given total thickness.
        Uses nearest thickness if exact match not found.
        """
        if not total_thickness or total_thickness <= 0:
            return None

        # Check for exact match (within tolerance)
        for thickness, max_depth in self.STANDARD_DEPTH_LIMITS.items():
            if abs(total_thickness - thickness) < 0.01:
                return max_depth

        # Find nearest thickness
        thicknesses = sorted(self.STANDARD_DEPTH_LIMITS.keys())

        # If thinner than thinnest standard, use thinnest
        if total_thickness < thicknesses[0]:
            return self.STANDARD_DEPTH_LIMITS[thicknesses[0]]

        # If thicker than thickest standard, use thickest
        if total_thickness > thicknesses[-1]:
            return self.STANDARD_DEPTH_LIMITS[thicknesses[-1]]

        # Find bracketing values and interpolate
        for i in range(len(thicknesses) - 1):
            if thicknesses[i] <= total_thickness <= thicknesses[i + 1]:
                # Use the more conservative (lower) limit
                return self.STANDARD_DEPTH_LIMITS[thicknesses[i]]

        return None

    # Max incremental Z pass depth for hub creation (production standard)
    HUB_PASS_MAX = {
        # hub_height_min: max_z_per_pass
        0.50: 0.20,  # hubs >= 0.50": max 0.20" per pass
    }

    def validate_file(self, lines: List[str], thickness: Optional[float],
                     hub_height: Optional[float],
                     outer_diameter: Optional[float] = None) -> TurningDepthResult:
        """
        Validate turning tool operations against standard depth limits.

        Args:
            lines: G-code file lines
            thickness: Body thickness in inches
            hub_height: Hub height in inches (0 for non-hub parts)
            outer_diameter: Part outer diameter (used for hub pass depth check)

        Returns:
            TurningDepthResult with warnings and notes
        """
        warnings = []
        notes = []

        # Calculate total height
        if not thickness or thickness <= 0:
            return TurningDepthResult([], [], None, None)

        hub_height = hub_height or 0.0
        outer_diameter = outer_diameter or 0.0
        total_height = thickness + hub_height

        # Get standard max depth for this thickness
        standard_max_depth = self.get_standard_depth(total_height)
        if not standard_max_depth:
            return TurningDepthResult([], [], total_height, None)

        # Determine whether to check incremental hub pass depth:
        # For hubs >= 0.50", each hub face plunge must be <= 0.20" deeper than the previous.
        check_hub_passes = hub_height >= 0.50
        hub_pass_max = 0.20

        # Track state
        in_turning_tool = False
        side = 1
        current_x = None   # last known X position
        current_z = 0.0    # last known Z position
        prev_hub_face_z = None  # Z at the last hub face plunge (X < OD - 2.0")
        flagged_lines = set()

        for i, line in enumerate(lines, 1):
            line_upper = line.upper()

            # Skip comments and empty lines
            if line.strip().startswith('(') or line.strip().startswith('%') or not line.strip():
                continue

            # Track flip
            if 'M01' in line_upper or 'M1' in line_upper or 'FLIP' in line_upper:
                side = 2
                in_turning_tool = False
                current_x = None
                current_z = 0.0
                prev_hub_face_z = None
                continue

            # Remove inline comments
            code_part = line.split('(')[0]

            # Skip G53 lines (tool home)
            if 'G53' in code_part.upper():
                continue

            # Track tool changes - only check T3xx (turning tool)
            tool_match = re.search(r'T(\d+)', code_part, re.IGNORECASE)
            if tool_match:
                tool_num = tool_match.group(1)
                in_turning_tool = tool_num[0] == '3'
                current_x = None
                current_z = 0.0
                prev_hub_face_z = None
                continue

            if not in_turning_tool:
                continue

            # Track current X and Z position
            x_match = re.search(r'X\s*(-?\d+\.?\d*)', code_part, re.IGNORECASE)
            if x_match:
                new_x = abs(float(x_match.group(1)))

                # --- Check 2: hub face plunge incremental depth ---
                # Detect when X dips from OD territory into hub-face territory.
                # Hub face X is much smaller than OD (< OD - 2.0").
                # Each successive plunge Z must be <= 0.20" deeper than the last.
                if check_hub_passes and outer_diameter > 0:
                    hub_face_threshold = outer_diameter - 2.0
                    was_at_od = current_x is None or current_x >= outer_diameter - 0.5
                    now_at_hub = new_x < hub_face_threshold
                    if was_at_od and now_at_hub and i not in flagged_lines:
                        baseline = prev_hub_face_z if prev_hub_face_z is not None else 0.0
                        increment = current_z - baseline
                        if increment > hub_pass_max:
                            side_str = f"Side {side}"
                            warnings.append(
                                f"{side_str} Line {i}: Hub face plunge at Z-{current_z:.2f} "
                                f"is {increment:.2f}\" deeper than previous pass Z-{baseline:.2f} "
                                f"- exceeds {hub_pass_max:.2f}\" max per pass for "
                                f"{hub_height:.2f}\" hub (take 0.20\" incremental passes)"
                            )
                            flagged_lines.add(i)
                        prev_hub_face_z = current_z

                current_x = new_x

            z_match = re.search(r'Z\s*(-?\d+\.?\d*)', code_part, re.IGNORECASE)
            if z_match:
                z_val = float(z_match.group(1))
                # Only track depth when cutting into the part (negative Z).
                # Positive Z is a clearance/approach move — reset depth to 0.
                current_z = abs(z_val) if z_val < 0 else 0.0

            # --- Check 1: total depth vs standard limit (negative Z only) ---
            neg_z_match = re.search(r'Z\s*(-\d+\.?\d*)', code_part, re.IGNORECASE)
            if not neg_z_match or i in flagged_lines:
                continue

            z_depth = abs(float(neg_z_match.group(1)))
            side_str = f"Side {side}"

            if z_depth > standard_max_depth + self.tolerance:
                margin = z_depth - standard_max_depth
                if hub_height > 0:
                    part_desc = f"{total_height:.2f}\" total ({thickness:.2f}\" + {hub_height:.2f}\" hub)"
                else:
                    part_desc = f"{thickness:.2f}\" part"
                warnings.append(
                    f"{side_str} Line {i}: Turning tool Z-{z_depth:.2f} exceeds standard depth "
                    f"(max: Z-{standard_max_depth:.2f} for {part_desc}) "
                    f"- Over by {margin:.2f}\""
                )
                flagged_lines.add(i)

            elif z_depth <= standard_max_depth and z_depth > 0.1:
                notes.append(
                    f"{side_str} Line {i}: Proper depth Z-{z_depth:.2f} "
                    f"(within standard Z-{standard_max_depth:.2f})"
                )
                flagged_lines.add(i)

        return TurningDepthResult(
            warnings=warnings,
            notes=notes,
            total_height=total_height,
            standard_max_depth=standard_max_depth
        )


# Example usage and testing
if __name__ == "__main__":
    validator = TurningToolDepthValidator()

    # Test with different thicknesses
    test_cases = [
        (0.75, 0.0, "0.75\" standard part"),
        (1.00, 0.0, "1.00\" standard part"),
        (0.43, 0.50, "11mm + 0.50\" hub (1.00\" total)"),
        (0.75, 0.50, "0.75\" + 0.50\" hub (1.25\" total)"),
    ]

    print("TURNING TOOL DEPTH STANDARDS")
    print("=" * 80)
    print("\nStandard Depth Limits:")
    for thickness, max_depth in sorted(validator.STANDARD_DEPTH_LIMITS.items()):
        jaw_limit = thickness - 0.3
        buffer = jaw_limit - max_depth
        print(f"  {thickness:.2f}\" = Z-{max_depth:.2f}  (jaw limit: Z-{jaw_limit:.2f}, buffer: {buffer:.2f}\")")

    print("\n" + "=" * 80)
    print("TEST CASES")
    print("=" * 80)

    for thickness, hub, desc in test_cases:
        total = thickness + hub
        standard = validator.get_standard_depth(total)
        jaw_limit = total - 0.3
        buffer = jaw_limit - standard if standard else 0

        print(f"\n{desc}:")
        print(f"  Total height: {total:.2f}\"")
        print(f"  Standard max depth: Z-{standard:.2f}")
        print(f"  Absolute jaw limit: Z-{jaw_limit:.2f}")
        print(f"  Safety buffer: {buffer:.2f}\"")

    # Test actual G-code validation
    print("\n" + "=" * 80)
    print("G-CODE VALIDATION TEST")
    print("=" * 80)

    test_gcode = """
O99999 (TEST - 1.0 INCH PART)
T303 (TURN TOOL)
G97 S1800 M03
G00 G54 X7.46 Z0.15 M08
G01 Z-0.5 F0.01    ; Within standard (0.55)
G00 Z0.2
G01 Z-0.65 F0.01   ; Exceeds standard (0.55), triggers warning
G00 G53 X-11. Z-13.
M01

(FLIP PART - SIDE 2)
T303 (TURN TOOL)
G01 Z-0.5 F0.01    ; Within standard
M30
    """.strip().split('\n')

    result = validator.validate_file(
        lines=test_gcode,
        thickness=1.00,
        hub_height=0.0
    )

    print(f"\nTest: 1.00\" part (standard max: Z-{result.standard_max_depth:.2f})")
    print("-" * 80)

    if result.warnings:
        print("WARNINGS:")
        for warning in result.warnings:
            print(f"  {warning}")

    if result.notes:
        print("\nNOTES:")
        for note in result.notes:
            print(f"  {note}")

    if not result.warnings:
        print("✓ All turning tool depths within standard limits")
