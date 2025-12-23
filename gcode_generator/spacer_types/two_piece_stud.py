"""
Two-Piece STUD Spacer Generator

Generates G-code for 2-piece STUD wheel spacers.
STUD spacers have a simpler center hole with stepped profile for stud mounting.

Key features from real programs (o61030, o62500, o62515):
- Order: Drill → Bore → Turn
- Simple drilling (no peck, shallower)
- Fewer boring passes with VARIED depths (stepped profile)
- Creates stud mounting pocket
- Smaller round sizes (6")
- Higher spindle speeds
"""

from typing import List, Tuple

from .base import BaseSpacerGenerator, TwoPieceStudDimensions
from ..rules.pcodes import PCodeManager
from ..rules.depths import DepthTable
from ..rules.feeds_speeds import FeedsSpeedsCalculator
from ..rules.boring_passes import BoringPassCalculator


class TwoPieceStudGenerator(BaseSpacerGenerator):
    """
    Generator for 2-piece STUD wheel spacers.

    STUD spacers have:
    - CB (center bore)
    - OB (outer bore/hub diameter)
    - 0.25" hub pocket depth (typical)
    - Typically 0.75" thick
    - Similar to hub-centric but for stud mounting
    """

    dimensions: TwoPieceStudDimensions

    # Default hub pocket depth
    DEFAULT_HUB_HEIGHT = 0.25

    def __init__(self, dimensions: TwoPieceStudDimensions):
        """Initialize with 2PC STUD dimensions."""
        super().__init__(dimensions)
        self.dimensions = dimensions

    def generate_header(self) -> List[str]:
        """Generate program header with 2PC STUD designation."""
        dim = self.dimensions

        description = (
            f"{dim.round_size}IN DIA {dim.cb_mm}MM STUD-2PC"
        )

        lines = [
            "%",
            f"{dim.program_number} ({description})",
            "",
            "",
            self.generate_tool_change_position(),
        ]

        return lines

    def generate_op1_drilling(self) -> Tuple[List[str], float]:
        """
        Generate OP1 drilling operation.

        STUD spacers use simple drilling (G01, no peck).
        Pattern from o61030 lines 9-15.
        """
        dim = self.dimensions

        drill_depth = DepthTable.get_drill_depth(dim.thickness_key)
        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")

        # STUD uses higher speeds
        drill_rpm = 2600

        lines = [
            "T101 (DRILL)",
            f"G97 S{drill_rpm} M03",
            f"G00 G154 {pcode} X0. Z1. M08",
            "M31",
            "Z0.2",
            f"G01 Z{self.format_gcode_value(drill_depth)} F0.008",
            "G00 Z1.",
        ]

        return (lines, drill_depth)

    def generate_op1_boring(self, drill_depth: float) -> List[str]:
        """
        Generate OP1 boring operation for STUD spacer.

        STUD spacers use standard boring passes calculated from CB,
        then create a stepped profile at the top.
        Pattern from o61030 lines 18-35.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")

        # Use BoringPassCalculator to get passes based on CB
        boring_passes = BoringPassCalculator.calculate_diameters_only(dim.cb_inches)

        # STUD uses higher speeds
        bore_max_rpm = 2600
        bore_rpm = 2300
        bore_css = 1800

        # Step profile depths (from o61030 pattern)
        step_depth_1 = -0.25
        step_depth_2 = -0.35
        chamfer_depth = 0.1

        lines = [
            "",
            "T121 (BORE)",
            f"G50 S{bore_max_rpm}",
            f"G97 S{bore_rpm} M03",
            f"G96 S{bore_css} M08",
            f"G154 {pcode} G00 X2.3 Z0.1",
        ]

        # Boring passes to full depth using calculated diameters
        for x_pass in boring_passes:
            lines.extend([
                f"X{self.format_gcode_value(x_pass)}",
                f"G01 Z{self.format_gcode_value(drill_depth)} F0.016",
                "G00 Z0.2",
            ])

        # Create stepped profile at CB area
        chamfer_start_x = dim.cb_inches + 0.2

        lines.extend([
            "G00 Z0",
            f"X{self.format_gcode_value(chamfer_start_x)}",
            # Chamfer at CB
            f"G01 X{self.format_gcode_value(dim.cb_inches)} Z-{self.format_gcode_value(chamfer_depth)} F0.008",
            # Step profile
            f"Z{self.format_gcode_value(step_depth_1)}",
            f"X{self.format_gcode_value(dim.cb_inches - 0.2)}",
            f"Z{self.format_gcode_value(step_depth_2)}",
            # Final bore to full depth
            f"Z{self.format_gcode_value(drill_depth)}",
            f"X{self.format_gcode_value(dim.cb_inches - 0.3)}",
            "G00 Z0.",
            "M09",
            "G00 G53 X-11. Z-16.",
        ])

        return lines

    def generate_op1_turning(self) -> List[str]:
        """
        Generate OP1 outer profile turning operation.

        Pattern from o61030 lines 41-58.
        STUD spacers have simpler turning with shallower profile.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")
        profile_depth = DepthTable.get_profile_depth(dim.thickness_key)

        # STUD uses higher speeds
        turn_max_rpm = 3000
        turn_rpm = 2500
        turn_css = 1800

        final_od = dim.round_size - 0.05
        finish_od = dim.round_size - 0.08
        face_to_x = dim.cb_inches - 0.1

        lines = [
            "",
            "",
            f"G50 S{turn_max_rpm} (MAX RPM)",
            "",
            "T303 (TURN TOOL)",
            f"G97 S{turn_rpm} M03",
            "M31",
            f"G00 G154 {pcode} X{self.format_gcode_value(dim.round_size)} Z0.1 M08",
            f"G96 S{turn_css} (CCS ON)",
            # Face
            f"G01 X{self.format_gcode_value(final_od)} Z0. F0.015",
            f"G01 Z{self.format_gcode_value(profile_depth)} F0.009",
            f"X{self.format_gcode_value(dim.round_size - 0.04)}",
            "G00 Z-0.05",
            f"X{self.format_gcode_value(final_od)}",
            f"G01 X{self.format_gcode_value(finish_od)} Z0. F0.008",
            f"G01 X{self.format_gcode_value(face_to_x)} Z0. F0.008",
            "G00 Z0.1 M09",
            "M01",
            "M09",
            "G00 G53 X-11. Z-16.",
            "",
            "M00",
        ]

        return lines

    def generate_op2_turning(self) -> List[str]:
        """
        Generate OP2 turning/facing operation with hub pocket.

        STUD spacers have a 0.25" hub pocket similar to hub-centric.
        Pattern from o61030 lines 65-82.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op2")
        profile_depth = DepthTable.get_profile_depth(dim.thickness_key)

        # Hub pocket depth
        hub_height = dim.hub_height_inches if dim.hub_height_inches else self.DEFAULT_HUB_HEIGHT

        # STUD uses higher speeds
        turn_rpm = 2600
        turn_css = 2000

        final_od = dim.round_size - 0.05
        finish_od = dim.round_size - 0.08

        lines = [
            "",
            "",
            "",
            "(FLIP PART)",
            "",
            "",
            "T303 (TURN TOOL)",
            f"G97 S{turn_rpm} M03",
            "M31",
            f"G00 G154 {pcode} X{self.format_gcode_value(dim.round_size)} Z0.1 M08",
            f"G96 S{turn_css} (CCS ON)",
        ]

        # If OB is defined, create hub pocket
        if dim.ob_inches > 0:
            # Face to OB first
            lines.extend([
                f"G01 X{self.format_gcode_value(final_od)} Z0. F0.015",
                f"X{self.format_gcode_value(dim.ob_inches)} F0.012",
                # Hub pocket depth
                f"Z-{self.format_gcode_value(hub_height)} F0.01",
                # Face to CB
                f"X{self.format_gcode_value(dim.cb_inches - 0.1)} F0.012",
                "G00 Z0.1",
                # OD profile
                f"X{self.format_gcode_value(finish_od)}",
                "Z0.",
                f"G01 X{self.format_gcode_value(final_od)} Z-0.05 F0.008",
                f"Z{self.format_gcode_value(profile_depth)} F0.01",
                f"X{self.format_gcode_value(dim.round_size)}",
            ])
        else:
            # Simple face without hub pocket
            lines.extend([
                f"G01 X{self.format_gcode_value(final_od)} Z0. F0.015",
                f"X{self.format_gcode_value(dim.cb_inches - 0.1)} F0.012",
                "G00 Z0.1",
                f"X{self.format_gcode_value(finish_od)}",
                "Z0.",
                f"G01 X{self.format_gcode_value(final_od)} Z-0.05 F0.008",
                f"Z{self.format_gcode_value(profile_depth)} F0.01",
                f"X{self.format_gcode_value(dim.round_size)}",
            ])

        lines.extend([
            "G00 Z1. M09",
            "G00 G53 X-11. Z-16.",
            "M01",
        ])

        return lines

    def generate_op2_chamfer(self) -> List[str]:
        """
        Generate OP2 chamfer bore operation.

        Pattern from o61030 lines 85-94.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op2")

        # STUD chamfer parameters
        chamfer_max_rpm = 2800
        chamfer_rpm = 2600
        chamfer_css = 1800

        chamfer_depth = 0.12
        x_chamfer_start = dim.cb_inches + 0.3

        lines = [
            "",
            "T121 (CHAMPHER)",
            f"G50 S{chamfer_max_rpm}",
            f"G97 S{chamfer_rpm} M03",
            f"G96 S{chamfer_css} M08",
            f"G154 {pcode} G00 X{self.format_gcode_value(x_chamfer_start)} Z0.1",
            "Z0.",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} F0.008",
            "G00 Z0.",
            "M09",
            "G00 G53 X-11. Z-15.",
        ]

        return lines

    def generate_footer(self) -> List[str]:
        """Generate program footer."""
        return self.generate_common_footer()
