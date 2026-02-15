"""
Hub Break-Through Validator
Validates hub-centric parts to prevent breaking through the hub during boring operations.

Critical Safety Rule:
- When boring near hub diameter (OB), Z depth must be limited to preserve hub material
- Formula: Max Z = Total stock - Hub height - Safety margin

Applies to:
- Hub-centric parts (has hub_height)
- Where hub_diameter (OB) <= center_bore (CB)

Example from o76051 (11mm HC, 0.50" hub):
  Total stock: 1.00" (0.43" body + 0.50" hub)
  At X4.6 (near hub 4.7756"), limited to Z-0.43
  Material left: 1.00" - 0.43" = 0.57"
  Hub needs: 0.50"
  Safety margin: 0.07" (minimal but acceptable for 11mm parts)
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class HubBreakThroughResult:
    """Result from hub break-through validation"""
    critical_issues: List[str]
    warnings: List[str]
    notes: List[str]
    thickness_verified: bool
    stock_thickness: Optional[float]


class HubBreakThroughValidator:
    """Validates hub-centric parts to prevent hub break-through during boring"""

    def __init__(self):
        self.warning_zone_start = 0.35   # Start checking 0.35" before hub diameter
        self.critical_zone_start = 0.15  # Critical zone: < 0.15" from hub diameter
        self.min_safety_margin = 0.05    # Absolute minimum safety margin
        self.standard_safety_margin = 0.20  # Preferred safety margin
        self.tool_radius = 0.03          # Standard bore tool radius allowance
        self.drill_clearance = 0.15      # Typical drill clearance beyond part thickness

    def round_to_quarter_inch(self, value: float) -> float:
        """Round up to nearest 0.25" increment (stock thickness standard)"""
        import math
        return math.ceil(value / 0.25) * 0.25

    def applies_to_part(self, spacer_type: str, hub_height: Optional[float],
                       center_bore: Optional[float], hub_diameter: Optional[float]) -> bool:
        """
        Check if hub break-through validation applies to this part.

        Criteria:
        1. Must be hub-centric
        2. Must have hub height
        3. Must have both CB and OB values
        4. Hub diameter (OB) must be <= center bore (CB)
        """
        # Must be hub-centric
        if spacer_type != 'hub_centric':
            return False

        # Must have hub height
        if not hub_height or hub_height <= 0:
            return False

        # Must have both CB and OB values
        if not center_bore or not hub_diameter:
            return False

        # Hub diameter must be <= center bore
        # Convert CB to mm for comparison (hub_diameter is in mm, center_bore might be in inches)
        cb_mm = center_bore if center_bore > 10 else center_bore * 25.4
        if hub_diameter > cb_mm:
            return False  # Different geometry, skip validation

        return True

    def validate_file(self, lines: List[str], spacer_type: str, thickness: Optional[float],
                     hub_height: Optional[float], center_bore: Optional[float],
                     hub_diameter: Optional[float]) -> HubBreakThroughResult:
        """
        Validate hub-centric part for break-through risks.

        Args:
            lines: G-code file lines
            spacer_type: Part type (should be 'hub_centric')
            thickness: Body thickness in inches
            hub_height: Hub height in inches
            center_bore: Center bore in mm
            hub_diameter: Hub diameter (OB) in mm

        Returns:
            HubBreakThroughResult with critical issues, warnings, and notes
        """
        critical_issues = []
        warnings = []
        notes = []
        thickness_verified = False
        stock_thickness = None

        # Check if validation applies
        if not self.applies_to_part(spacer_type, hub_height, center_bore, hub_diameter):
            return HubBreakThroughResult([], [], [], False, None)

        # Validate inputs
        if not thickness or thickness <= 0:
            warnings.append("Cannot validate hub break-through: body thickness not available")
            return HubBreakThroughResult(critical_issues, warnings, notes, False, None)

        # Calculate expected stock thickness
        expected_stock = self.round_to_quarter_inch(thickness + hub_height)
        stock_thickness = expected_stock

        # Verify against drill depth (T101 operation)
        drill_depth = self._extract_drill_depth(lines)
        if drill_depth:
            estimated_stock = drill_depth - self.drill_clearance
            thickness_verified = True

            # Check if drill depth matches expected stock
            if abs(estimated_stock - expected_stock) > 0.1:
                warnings.append(
                    f"Stock thickness mismatch: Drill depth suggests {estimated_stock:.2f}\" "
                    f"but body+hub suggests {expected_stock:.2f}\" stock"
                )
            else:
                notes.append(
                    f"Stock thickness verified: {expected_stock:.2f}\" "
                    f"(body {thickness:.2f}\" + hub {hub_height:.2f}\")"
                )

        # Calculate maximum safe depth
        max_safe_depth = expected_stock - hub_height - self.min_safety_margin
        recommended_depth = expected_stock - hub_height - self.standard_safety_margin

        # Convert hub diameter to inches for comparison
        hub_diameter_inches = hub_diameter / 25.4

        # Determine if this is a thin part (11mm or less)
        is_thin_part = thickness < 0.45  # 11mm = 0.433"
        if is_thin_part:
            actual_margin = expected_stock - thickness - hub_height
            notes.append(
                f"THIN PART ({thickness:.2f}\" body) - Minimal safety margin: {actual_margin:.2f}\""
            )

        # Parse T121 bore operations
        in_bore_op = False
        side = 1
        current_x = None

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Track side
            if 'FLIP PART' in line_upper or 'SIDE 2' in line_upper:
                side = 2

            # Detect T121 bore operation
            if 'T121' in line_upper:
                in_bore_op = True
                continue

            # Exit bore operation on new tool
            if in_bore_op and re.match(r'^T\d+', line_upper.strip()):
                in_bore_op = False

            # Track current X position
            if in_bore_op:
                x_match = re.search(r'X\s*(-?\d+\.?\d*)', line_upper)
                if x_match:
                    current_x = float(x_match.group(1))

                # Check Z movements in warning and critical zones
                if current_x and ('G01' in line_upper or 'G1' in line_upper):
                    z_match = re.search(r'Z\s*(-?\d+\.?\d*)', line_upper)
                    if z_match:
                        z_value = float(z_match.group(1))
                        z_depth = abs(z_value)

                        # CRITICAL: Only check depth when X > hub diameter (OUTSIDE the bore)
                        # When X <= hub diameter, we're at or inside the bore - this is cleanup/thin lip creation
                        # Side 2 operations often go to hub diameter or just inside to clean up the bore
                        if current_x <= hub_diameter_inches:
                            continue  # At or inside bore - depth unrestricted for cleanup

                        # Calculate distance OUTSIDE hub diameter
                        distance_from_hub = current_x - hub_diameter_inches

                        # Determine which zone we're in (measured OUTWARD from hub)
                        in_warning_zone = (distance_from_hub > 0 and distance_from_hub <= self.warning_zone_start)
                        in_critical_zone = (distance_from_hub > self.warning_zone_start and
                                          distance_from_hub <= self.critical_zone_start)

                        if (in_warning_zone or in_critical_zone) and z_depth > 0.01:  # Ignore Z0
                            # Calculate material left
                            material_left = expected_stock - z_depth
                            margin = material_left - hub_height

                            side_str = f"Side {side}"

                            # CRITICAL: In critical zone and exceeding max safe depth
                            if in_critical_zone and z_depth > max_safe_depth:
                                critical_issues.append(
                                    f"HUB BREAK-THROUGH RISK - {side_str} Line {i+1}: "
                                    f"Z{z_value:.2f} at X{current_x:.2f} (hub @ X{hub_diameter_inches:.2f}) "
                                    f"- Max safe depth: Z-{max_safe_depth:.2f} "
                                    f"(leaves only {margin:.2f}\" for {hub_height:.2f}\" hub)"
                                )

                            # WARNING: In warning zone and approaching limit
                            elif in_warning_zone and z_depth > recommended_depth and not is_thin_part:
                                warnings.append(
                                    f"Approaching hub limit - {side_str} Line {i+1}: "
                                    f"Z{z_value:.2f} at X{current_x:.2f} ({distance_from_hub:.2f}\" from hub) "
                                    f"- Recommended max: Z-{recommended_depth:.2f} "
                                    f"(margin: {margin:.2f}\")"
                                )

                            # NOTE: Good practice - proper depth limiting in critical zone
                            elif in_critical_zone and z_depth <= max_safe_depth and distance_from_hub < 0.2:
                                notes.append(
                                    f"{side_str}: Proper depth limit Z{z_value:.2f} at X{current_x:.2f} "
                                    f"(leaves {margin:.2f}\" margin for {hub_height:.2f}\" hub)"
                                )

        return HubBreakThroughResult(
            critical_issues=critical_issues,
            warnings=warnings,
            notes=notes,
            thickness_verified=thickness_verified,
            stock_thickness=stock_thickness
        )

    def _extract_drill_depth(self, lines: List[str]) -> Optional[float]:
        """Extract drill depth from T101 operation (G83 command)"""
        in_drill_op = False

        for line in lines:
            line_upper = line.upper()

            # Detect T101 drill operation
            if 'T101' in line_upper:
                in_drill_op = True
                continue

            # Exit drill operation on new tool
            if in_drill_op and re.match(r'^T\d+', line_upper.strip()):
                return None  # Didn't find G83 in T101

            # Look for G83 (peck drilling cycle) or G01 Z (simple drilling)
            if in_drill_op:
                # G83 Z-1.15 Q0.8 R0.2 F0.008
                g83_match = re.search(r'G83\s+Z\s*(-?\d+\.?\d*)', line_upper)
                if g83_match:
                    return abs(float(g83_match.group(1)))

                # Simple G01 Z-1.15 (match G01 or G1 as word boundary, not substring)
                if re.search(r'\bG0?1\b', line_upper):
                    z_match = re.search(r'Z\s*(-?\d+\.?\d*)', line_upper)
                    if z_match:
                        z_value = float(z_match.group(1))
                        # Only return negative Z values (drilling down), ignore positive retractions
                        if z_value < 0:
                            return abs(z_value)

        return None


# Example usage
if __name__ == "__main__":
    validator = HubBreakThroughValidator()

    # Test with o76051 example (11mm HC, 0.50" hub)
    test_gcode = """
O76051 (7.5 IN DIA  121.3/121.3MM .11MM HC )
T101 (DRILL)
G83 Z-1.15 Q0.8 R0.2 F0.008

T121 ( BORE)
G01 Z-1.15 F0.02
X4.3
G01 Z-1.15 F0.02
X4.6
G01 Z-0.43 F0.02
X5.0795
G01 Z0 F0.01
    """.strip().split('\n')

    result = validator.validate_file(
        lines=test_gcode,
        spacer_type='hub_centric',
        thickness=0.433,  # 11mm
        hub_height=0.50,
        center_bore=121.3,
        hub_diameter=121.3
    )

    print("Test Results for o76051 (11mm HC):")
    print("=" * 80)
    if result.critical_issues:
        print("CRITICAL ISSUES:")
        for issue in result.critical_issues:
            print(f"  [CRITICAL] {issue}")
    if result.warnings:
        print("\nWARNINGS:")
        for warning in result.warnings:
            print(f"  [WARNING] {warning}")
    if result.notes:
        print("\nNOTES:")
        for note in result.notes:
            print(f"  [NOTE] {note}")
    if not result.critical_issues and not result.warnings:
        print("\n[PASS] No hub break-through risks detected")

    print(f"\nStock thickness: {result.stock_thickness:.2f}\"")
    print(f"Thickness verified: {result.thickness_verified}")
