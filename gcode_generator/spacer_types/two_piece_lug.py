"""
Two-Piece LUG Spacer Generator

Generates G-code for 2-piece LUG wheel spacers.
LUG spacers have graduated bore pockets for mechanical lug-style connections.

Key features from real programs (o12000, o12001, o12002):
- Order: Drill → Bore → Turn
- Deep peck drilling (G83)
- Many progressive boring passes at same depth
- Creates graduated pocket for lug engagement
- Larger round sizes (10"+)
"""

from typing import List, Tuple

from .base import BaseSpacerGenerator, TwoPieceLugDimensions
from ..rules.pcodes import PCodeManager
from ..rules.depths import DepthTable
from ..rules.feeds_speeds import FeedsSpeedsCalculator
from ..rules.boring_passes import BoringPassCalculator


class TwoPieceLugGenerator(BaseSpacerGenerator):
    """
    Generator for 2-piece LUG wheel spacers.

    LUG spacers have:
    - CB (center bore) - inner bore
    - Counterbore diameter - outer recess
    - Z-0.31" recess depth for lug engagement
    - Many progressive boring passes
    """

    dimensions: TwoPieceLugDimensions

    # Default recess depth if not specified
    DEFAULT_RECESS_DEPTH = 0.31

    def __init__(self, dimensions: TwoPieceLugDimensions):
        """Initialize with 2PC LUG dimensions."""
        super().__init__(dimensions)
        self.dimensions = dimensions

    def generate_header(self) -> List[str]:
        """Generate program header with 2PC LUG designation."""
        dim = self.dimensions

        description = (
            f"{dim.round_size}IN DIA {dim.cb_mm} 2PC LUG"
        )

        lines = [
            "%",
            f"{dim.program_number} ({description})",
            "",
            "",
            self.generate_tool_change_position(),
            "G50 S2800 (MAX RPM)",
        ]

        return lines

    def generate_op1_drilling(self) -> Tuple[List[str], float]:
        """
        Generate OP1 drilling operation.

        LUG spacers use deep peck drilling (G83).
        Pattern from o12000 lines 15-19.
        """
        dim = self.dimensions

        drill_depth = DepthTable.get_drill_depth(dim.thickness_key)
        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")

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
            f"G83 Z{self.format_gcode_value(drill_depth)} R0.2 "
            f"Q{self.format_gcode_value(drill_params.peck)} "
            f"F{self.format_gcode_value(drill_params.feed)}",
            "G00 G80 Z2.",
        ]

        return (lines, drill_depth)

    def generate_op1_boring(self, drill_depth: float) -> List[str]:
        """
        Generate OP1 boring operation for LUG spacer.

        Two-zone boring:
        1. Inner bore (CB) to full depth
        2. Counterbore recess to Z-0.31" depth

        Pattern from o12000.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")

        # Calculate passes for inner bore (to CB)
        inner_passes = BoringPassCalculator.calculate_diameters_only(dim.cb_inches)

        # Calculate passes for counterbore recess (from CB to counterbore diameter)
        recess_passes = []
        if dim.counterbore_inches > dim.cb_inches:
            current_x = dim.cb_inches + 0.3
            while current_x < dim.counterbore_inches - 0.1:
                recess_passes.append(round(current_x, 3))
                current_x += 0.3
            # Add pre-finish pass
            if recess_passes and recess_passes[-1] < dim.counterbore_inches - 0.1:
                recess_passes.append(round(dim.counterbore_inches - 0.1, 3))

        bore_params = FeedsSpeedsCalculator.get_bore_params(
            dim.round_size,
            dim.thickness_inches,
            depth_of_cut=0.15,
            use_calculated=dim.use_calculated_feeds
        )

        # Recess depth (Z-0.31" default)
        recess_depth = -abs(dim.recess_depth_inches) if dim.recess_depth_inches else -self.DEFAULT_RECESS_DEPTH

        chamfer_depth = 0.15

        lines = [
            "",
            "",
            "T121 (BORE)",
            f"G50 S{bore_params.max_rpm}",
            f"G97 S{bore_params.rpm} M03",
            f"G96 S{bore_params.css} M08",
            f"G00 G154 {pcode} X2.3 Z2.",
            "Z0.2",
        ]

        # Zone 1: Inner bore passes to full depth
        for x_pass in inner_passes:
            lines.extend([
                f"X{self.format_gcode_value(x_pass)}",
                f"G01 Z{self.format_gcode_value(drill_depth)} "
                f"F{self.format_gcode_value(bore_params.feed_rough)}",
                "G00 Z0.2",
            ])

        # Chamfer at CB
        x_chamfer_start = dim.cb_inches + (chamfer_depth * 2)
        lines.extend([
            f"X{self.format_gcode_value(x_chamfer_start)}",
            f"G01 Z0 F{self.format_gcode_value(bore_params.feed_finish)}",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(bore_params.feed_chamfer)} (X IS CB)",
            f"Z{self.format_gcode_value(drill_depth)}",
            f"X{self.format_gcode_value(dim.cb_inches - 0.3)}",
            "G00 Z0.2",
        ])

        # Zone 2: Counterbore recess passes (to recess depth only)
        if recess_passes:
            lines.append("")
            lines.append("(COUNTERBORE RECESS)")
            for x_pass in recess_passes:
                lines.extend([
                    f"X{self.format_gcode_value(x_pass)}",
                    f"G01 Z{self.format_gcode_value(recess_depth)} "
                    f"F{self.format_gcode_value(bore_params.feed_rough)}",
                    "G00 Z0.2",
                ])

            # Finish counterbore with chamfer
            cb_chamfer_start = dim.counterbore_inches + (chamfer_depth * 2)
            lines.extend([
                f"X{self.format_gcode_value(cb_chamfer_start)}",
                f"G01 Z0 F{self.format_gcode_value(bore_params.feed_finish)}",
                f"G01 X{self.format_gcode_value(dim.counterbore_inches)} "
                f"Z-{self.format_gcode_value(chamfer_depth)} "
                f"F{self.format_gcode_value(bore_params.feed_chamfer)}",
                f"Z{self.format_gcode_value(recess_depth)}",
                f"X{self.format_gcode_value(dim.cb_inches)}",
            ])

        # Retract
        lines.extend([
            f"X{self.format_gcode_value(dim.cb_inches - 0.3)}",
            "G00 Z2. M09",
            self.generate_home_position(),
        ])

        return lines

    def generate_op1_turning(self) -> List[str]:
        """
        Generate OP1 outer profile turning operation.

        Pattern from o12000 lines 73-92.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")
        profile_depth = DepthTable.get_profile_depth(dim.thickness_key)

        turn_params = FeedsSpeedsCalculator.get_turn_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        final_od = dim.round_size - 0.05
        finish_od = dim.round_size - 0.08
        face_to_x = dim.cb_inches - 0.1

        lines = [
            "",
            "",
            "M31",
            "T303 (TURN TOOL)",
            f"G97 S{turn_params.rpm} M03",
            f"G00 G154 {pcode} X{self.format_gcode_value(dim.round_size)} Z1.",
            "/ M08",
            f"G96 S{turn_params.css} (CSS ON)",
            "G00 Z0.15",
            # Face
            f"G01 X{self.format_gcode_value(dim.round_size)} Z0. "
            f"F{self.format_gcode_value(turn_params.feed_profile)}",
            f"X{self.format_gcode_value(face_to_x)}",
            "G00 Z0.1",
            # OD profile
            f"X{self.format_gcode_value(finish_od)}",
            "Z0.",
            f"G01 X{self.format_gcode_value(final_od)} Z-0.05 "
            f"F{self.format_gcode_value(turn_params.feed_finish)}",
            f"G01 Z{self.format_gcode_value(profile_depth)} "
            f"F{self.format_gcode_value(turn_params.feed_profile)}",
            f"X{self.format_gcode_value(dim.round_size)}",
            "G00 Z0",
            "M09",
            "G53 X-11. Z-13.",
            "M01",
            "M00",
        ]

        return lines

    def generate_op2_turning(self) -> List[str]:
        """
        Generate OP2 turning/facing operation.

        Pattern from o12000 lines 111-135.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op2")
        profile_depth = DepthTable.get_profile_depth(dim.thickness_key)

        turn_params = FeedsSpeedsCalculator.get_turn_op2_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        final_od = dim.round_size - 0.05
        finish_od = dim.round_size - 0.08
        face_to_x = dim.cb_inches - 0.1

        lines = self.generate_flip_part_section()

        lines.extend([
            "G50 S2850 (MAX RPM)",
            "",
            "T303 (TURN TOOL)",
            f"G97 S{turn_params.rpm} M03",
            f"G00 G154 {pcode} X{self.format_gcode_value(final_od)} Z0.15 M08",
            f"G96 S{turn_params.css} (CCS ON)",
            # Face
            "G01 Z0 F0.01",
            f"G01 X{self.format_gcode_value(face_to_x)} "
            f"F{self.format_gcode_value(turn_params.feed_rough)}",
            "Z0.1",
            # OD profile
            f"G00 X{self.format_gcode_value(finish_od)}",
            "Z0.",
            f"G01 X{self.format_gcode_value(final_od)} Z-0.05 "
            f"F{self.format_gcode_value(turn_params.feed_finish)}",
            f"Z{self.format_gcode_value(profile_depth)} "
            f"F{self.format_gcode_value(turn_params.feed_profile)}",
            f"G00 X{self.format_gcode_value(dim.round_size)} Z0. M09",
            "G53 X-11. Z-13.",
            "M01",
        ])

        return lines

    def generate_op2_chamfer(self) -> List[str]:
        """
        Generate OP2 chamfer bore operation.

        Pattern from o12000 lines 142-154.
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op2")

        chamfer_params = FeedsSpeedsCalculator.get_chamfer_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        chamfer_depth = 0.12
        x_chamfer_start = dim.cb_inches + 0.3

        lines = [
            "",
            "T121 (CHAMFER BORE)",
            f"G50 S{chamfer_params.max_rpm}",
            f"G97 S{chamfer_params.rpm} M03",
            f"G96 S{chamfer_params.css} M08",
            f"G154 {pcode} G00 X{self.format_gcode_value(x_chamfer_start)} Z1.",
            "Z0.",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(chamfer_params.feed)}",
            "G00 Z0.",
            "",
            self.generate_home_position(),
        ]

        return lines

    def generate_footer(self) -> List[str]:
        """Generate program footer."""
        return self.generate_common_footer()
