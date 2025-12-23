"""
Thin-Lip Hub-Centric Spacer Generator

Generates G-code for thin-lip hub-centric wheel spacers.
These are hub-centric spacers where the CB and OB are within ~5mm of each other,
creating a thin wall that requires special machining considerations.

Key differences from standard hub-centric:
- Slower feeds to prevent wall breakage
- Smaller Z increments (0.1" vs 0.2")
- Feed inward strategy to reduce lateral pressure on thin wall
- More careful chamfering
"""

from typing import List, Tuple

from .base import BaseSpacerGenerator, HubCentricDimensions
from ..rules.pcodes import PCodeManager
from ..rules.depths import DepthTable
from ..rules.feeds_speeds import FeedsSpeedsCalculator
from ..rules.boring_passes import BoringPassCalculator


class ThinLipSpacerGenerator(BaseSpacerGenerator):
    """
    Generator for thin-lip hub-centric wheel spacers.

    Thin-lip spacers have a CB and OB within ~5mm of each other,
    creating a thin wall that requires special care during machining.
    """

    dimensions: HubCentricDimensions

    # Thin-lip specific parameters
    THIN_LIP_Z_INCREMENT = 0.1  # Smaller increments
    FEED_REDUCTION = 0.7  # 30% slower feeds

    def __init__(self, dimensions: HubCentricDimensions):
        """Initialize with hub-centric dimensions."""
        super().__init__(dimensions)
        self.dimensions = dimensions

    def _get_pcode_thickness_key(self) -> str:
        """Get thickness key for P-code lookup including hub height."""
        dim = self.dimensions
        total_thickness = dim.thickness_inches + dim.hub_height_inches
        rounded_total = round(total_thickness * 4) / 4
        return f"{rounded_total:.2f}"

    def _is_thin_lip(self) -> bool:
        """Check if this spacer qualifies as thin-lip."""
        dim = self.dimensions
        wall_thickness_mm = dim.ob_mm - dim.cb_mm
        return wall_thickness_mm <= 5.0

    def generate_header(self) -> List[str]:
        """Generate program header with thin-lip designation."""
        dim = self.dimensions

        # Build description with "THIN LIP" indicator
        description = (
            f"{dim.round_size}IN DIA {dim.cb_mm}/{dim.ob_mm}MM "
            f"{dim.thickness_key} HC THIN LIP {dim.hub_height_inches}"
        )

        lines = [
            "%",
            f"{dim.program_number} ({description})",
            "",
            "(*** THIN LIP MODE - REDUCED FEEDS ***)",
            "",
            self.generate_tool_change_position(),
            "G50 S2800 (MAX RPM)",
        ]

        return lines

    def generate_op1_drilling(self) -> Tuple[List[str], float]:
        """Generate OP1 drilling operation (same as hub-centric)."""
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        drill_depth = DepthTable.get_drill_depth(pcode_key)
        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op1")

        drill_params = FeedsSpeedsCalculator.get_drill_params(
            dim.thickness_inches,
            dim.round_size,
            dim.use_calculated_feeds
        )

        lines = [
            "",
            "",
            "",
            "T101 (DRILL)",
            f"G97 S{drill_params.rpm} M03",
            f"G00 G154 {pcode} X0. Z1. M08",
        ]

        if abs(drill_depth) > 1.65:
            lines.extend([
                f"G83 Z{self.format_gcode_value(drill_depth)} R0.2 "
                f"Q{self.format_gcode_value(drill_params.peck)} "
                f"F{self.format_gcode_value(drill_params.feed)}",
                "G00 G80 Z2.",
            ])
        else:
            lines.extend([
                f"G83 Z{self.format_gcode_value(drill_depth)} "
                f"Q{self.format_gcode_value(drill_params.peck)} R0.2 "
                f"F{self.format_gcode_value(drill_params.feed)}",
                "G00 Z1.",
            ])

        return (lines, drill_depth)

    def generate_op1_boring(self, drill_depth: float) -> List[str]:
        """
        Generate OP1 boring operation with SAFETY SHELF for thin-lip.

        The safety shelf is a ring of material left at a larger diameter
        between the shelf depth and full bore depth. This prevents
        breakthrough when the hub pocket is cut on OP2.

        Pattern (from existing programs like o11001, o11007, o11027):
        1. Bore passes to full depth at smaller diameters
        2. Bore passes to SHELF depth at larger diameters (near CB)
        3. After CB chamfer, go to shelf depth
        4. Move inward to shelf diameter (smaller than CB)
        5. Go to full bore depth at shelf diameter

        This leaves material between CB and shelf_diameter from shelf_z to full depth.
        """
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op1")
        boring_passes = BoringPassCalculator.calculate_diameters_only(dim.cb_inches)

        bore_params = FeedsSpeedsCalculator.get_bore_params(
            dim.round_size,
            dim.thickness_inches,
            depth_of_cut=0.15,
            use_calculated=dim.use_calculated_feeds
        )

        chamfer_depth = 0.15
        x_chamfer_start = dim.cb_inches + (chamfer_depth * 2)

        # Safety shelf calculations
        # Shelf depth: should leave material above where OP2 hub pocket will be cut
        # Looking at examples:
        #   o11001: full=-3.65, shelf=-2.78, diff=0.87, hub=0.5" -> offset = hub + 0.37"
        #   o11007: full=-3.9, shelf=-2.78, diff=1.12, hub=0.75" -> offset = hub + 0.37"
        # Pattern: shelf_offset = hub_height + ~0.35-0.40" safety margin
        shelf_offset = dim.hub_height_inches + 0.37
        shelf_z = drill_depth + shelf_offset  # Less negative (shallower)

        # Shelf diameter: slightly smaller than CB to leave material ring
        # From examples: CB=6.701, shelf_dia=6.075, difference ~0.626"
        # This should be about CB - (0.5 to 0.7")
        shelf_diameter = dim.cb_inches - 0.625

        # Determine which passes go to full depth vs shelf depth
        # Passes at diameters > shelf_diameter go to shelf depth only
        # This leaves the ring of material between shelf_diameter and CB
        shelf_threshold = shelf_diameter

        lines = [
            "",
            "(---------------------------)",
            "(OP1: BORING CENTER BORE - THIN LIP WITH SAFETY SHELF)",
            "(---------------------------)",
            f"(SAFETY SHELF: Material left between X{self.format_gcode_value(shelf_diameter)} and X{self.format_gcode_value(dim.cb_inches)})",
            f"(SHELF DEPTH: Z{self.format_gcode_value(shelf_z)} / FULL DEPTH: Z{self.format_gcode_value(drill_depth)})",
            "",
            "T121 (BORE)",
            f"G50 S{bore_params.max_rpm}",
            f"G97 S{bore_params.rpm} M03",
            f"G96 S{bore_params.css} M08",
            f"G00 G154 {pcode} X2.3 Z2.",
            "Z0.2",
        ]

        current_x = 2.3
        for i, x_pass in enumerate(boring_passes):
            if abs(current_x - x_pass) > 0.001:
                lines.append(f"X{self.format_gcode_value(x_pass)}")
                current_x = x_pass

            # Determine depth for this pass: full depth or shelf depth
            if x_pass >= shelf_threshold:
                # Near CB - only go to shelf depth
                pass_depth = shelf_z
            else:
                # Further from CB - go to full depth
                pass_depth = drill_depth

            lines.append(
                f"G01 Z{self.format_gcode_value(pass_depth)} "
                f"F{self.format_gcode_value(bore_params.feed_rough)}"
            )

            clearance_x = x_pass - 0.1
            lines.append(f"X{self.format_gcode_value(clearance_x)}")
            current_x = clearance_x
            lines.append("G00 Z0.2")

            if i < len(boring_passes) - 1:
                next_x = boring_passes[i + 1]
                lines.append(f"X{self.format_gcode_value(next_x)}")
                current_x = next_x

        # Chamfer and finish CB at shelf depth first
        lines.extend([
            f"X{self.format_gcode_value(x_chamfer_start)}",
            f"G01 Z0 F{self.format_gcode_value(bore_params.feed_finish)}",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(bore_params.feed_chamfer)} (X IS CB)",
            f"Z{self.format_gcode_value(shelf_z)} (SHELF DEPTH)",
        ])

        # Now create the safety shelf: move inward then go to full depth
        lines.extend([
            f"X{self.format_gcode_value(shelf_diameter)} (SHELF DIAMETER)",
            f"Z{self.format_gcode_value(drill_depth)} (FULL DEPTH - SHELF CREATED)",
        ])

        # Retract
        final_clearance_x = shelf_diameter - 0.2
        lines.extend([
            f"G00 X{self.format_gcode_value(final_clearance_x)}",
            "G00 Z2.",
            "M09",
            self.generate_home_position(),
        ])

        return lines

    def generate_op1_turning(self) -> List[str]:
        """Generate OP1 outer profile turning (same as hub-centric)."""
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op1")
        profile_depth = DepthTable.get_profile_depth(pcode_key)

        turn_params = FeedsSpeedsCalculator.get_turn_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        final_od = dim.round_size - 0.05
        face_to_x = dim.cb_inches + 0.2
        inner_chamfer_x = dim.cb_inches

        lines = [
            "",
            "M31",
            "",
            "(---------------------------)",
            "(OP1: OUTER PROFILE TURNING)",
            "(---------------------------)",
            "T303 (TURN TOOL)",
            f"G97 S{turn_params.rpm} M03",
            f"G00 G154 {pcode} X{self.format_gcode_value(dim.round_size)} Z0.1 M08",
            f"G96 S{turn_params.css}",
            "Z0.",
            f"G01 X{self.format_gcode_value(final_od)} "
            f"F{self.format_gcode_value(turn_params.feed_profile)}",
            f"Z{self.format_gcode_value(profile_depth)} "
            f"F{self.format_gcode_value(turn_params.feed_profile)}",
            f"G00 X{self.format_gcode_value(dim.round_size)}",
            "Z-0.05",
            f"G01 X{self.format_gcode_value(final_od)} "
            f"F{self.format_gcode_value(turn_params.feed_finish)}",
            f"Z0. F{self.format_gcode_value(turn_params.feed_finish)}",
            f"G01 X{self.format_gcode_value(face_to_x)} Z0. "
            f"F{self.format_gcode_value(turn_params.feed_rough)}",
            f"G01 X{self.format_gcode_value(inner_chamfer_x)} Z-0.1 "
            f"F{self.format_gcode_value(turn_params.feed_finish)}",
            "G00 Z0.1 M09",
            "G53 X-11. Z-13.",
            "M01",
            "M00",
        ]

        return lines

    def generate_op2_turning(self) -> List[str]:
        """
        Generate OP2 turning with THIN LIP protection.

        Key differences from standard hub-centric:
        - 0.1" Z increments (vs 0.2" for standard)
        - Feed INWARD toward CB to reduce lateral wall pressure
        - Slower feed rates

        Note: Safety shelf was created in OP1 boring, so we can cut
        to full hub depth here - the shelf prevents breakthrough.
        """
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op2")

        turn_params = FeedsSpeedsCalculator.get_turn_op2_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        # Apply thin-lip feed reduction
        feed_rough = round(turn_params.feed_rough * self.FEED_REDUCTION, 4)
        feed_finish = round(turn_params.feed_finish * self.FEED_REDUCTION, 4)

        start_x = round(dim.round_size - 0.05, 2)
        cut_to_x = round(dim.ob_inches + 0.1, 3)
        hub_depth = dim.hub_height_inches

        lines = self.generate_flip_part_section()

        lines.extend([
            "G50 S2850 (MAX RPM)",
            "",
            "(*** THIN LIP MODE: Incremental passes to protect thin wall ***)",
            "(SAFETY SHELF CREATED IN OP1 BORING - PROTECTS FROM BREAKTHROUGH)",
            "",
            "T303 (TURN TOOL)",
            f"G97 S{turn_params.rpm} M03",
            f"G00 G154 {pcode} X{start_x} Z0.1 M08",
            f"G96 S{turn_params.css}",
        ])

        # THIN LIP: Incremental 0.1" passes with INWARD feed
        z_depth = self.THIN_LIP_Z_INCREMENT

        while z_depth <= hub_depth:
            lines.extend([
                # Feed down at outer diameter
                f"G01 Z-{self.format_gcode_value(z_depth)} F{self.format_gcode_value(feed_rough)}",
                # Feed INWARD (reduces lateral pressure on thin wall)
                f"X{self.format_gcode_value(cut_to_x)}",
                # Retract to starting X
                f"G00 X{self.format_gcode_value(start_x)}",
            ])
            z_depth += self.THIN_LIP_Z_INCREMENT

        # Finish pass to full hub depth
        lines.extend([
            f"(FINISH PASS)",
            f"G01 Z-{self.format_gcode_value(hub_depth)} "
            f"F{self.format_gcode_value(feed_finish)}",
            f"X{self.format_gcode_value(dim.ob_inches)} (X IS OB)",
        ])

        # Move up hub wall for chamfer
        chamfer_z_start = 0.06
        chamfer_x = dim.ob_inches - (chamfer_z_start * 2)

        lines.extend([
            f"G01 Z-{self.format_gcode_value(chamfer_z_start)} "
            f"F{self.format_gcode_value(feed_finish)}",
            f"G01 X{self.format_gcode_value(chamfer_x)} Z0. "
            f"F{self.format_gcode_value(feed_finish)}",
        ])

        # Rapid toward center
        rapid_x = max(dim.cb_inches - 0.5, 2.5)
        lines.extend([
            f"X{self.format_gcode_value(rapid_x)}",
            "G00 Z1.",
            "M09",
            "G53 X-11. Z-13.",
            "M01",
        ])

        return lines

    def generate_op2_chamfer(self) -> List[str]:
        """Generate OP2 chamfer bore operation."""
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op2")

        chamfer_params = FeedsSpeedsCalculator.get_chamfer_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        # Slightly slower feed for thin-lip
        feed = round(chamfer_params.feed * self.FEED_REDUCTION, 4)

        chamfer_depth = 0.1
        x_chamfer_start = dim.cb_inches + (chamfer_depth * 2)

        lines = [
            "",
            "(---------------------------)",
            "(OP2: CHAMFER BORE - THIN LIP)",
            "(---------------------------)",
            "T121 (CHAMFER BORE)",
            f"G50 S{chamfer_params.max_rpm}",
            f"G97 S{chamfer_params.rpm} M03",
            f"G96 S{chamfer_params.css} M08",
            f"G154 {pcode} G00 X{self.format_gcode_value(x_chamfer_start)} Z1.",
            "Z0.",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(feed)}",
            self.generate_home_position(),
        ]

        return lines

    def generate_footer(self) -> List[str]:
        """Generate program footer."""
        return self.generate_common_footer()
