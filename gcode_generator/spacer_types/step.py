"""
STEP Spacer Generator

Generates G-code for STEP wheel spacers.
STEP spacers have a counterbore shelf that allows them to fit over
a stepped hub or provide clearance for brake components.

Key features:
- Inner center bore (holder) - goes through the full thickness
- Counterbore shelf - a larger diameter pocket to a specific depth
- Two-zone boring: inner bore full depth, counterbore to step depth only
"""

from typing import List, Tuple

from .base import BaseSpacerGenerator, StepSpacerDimensions
from ..rules.pcodes import PCodeManager
from ..rules.depths import DepthTable
from ..rules.feeds_speeds import FeedsSpeedsCalculator
from ..rules.boring_passes import BoringPassCalculator


class StepSpacerGenerator(BaseSpacerGenerator):
    """
    Generator for STEP wheel spacers.

    STEP spacers have:
    - Inner bore (holder diameter) - full depth
    - Counterbore shelf - larger diameter, partial depth
    """

    dimensions: StepSpacerDimensions

    def __init__(self, dimensions: StepSpacerDimensions):
        """Initialize with STEP-specific dimensions."""
        super().__init__(dimensions)
        self.dimensions = dimensions

    def generate_header(self) -> List[str]:
        """Generate program header with STEP designation."""
        dim = self.dimensions

        # Build description: "7.0IN DIA 106.1/74MM B/C 1.50"
        description = (
            f"{dim.round_size}IN DIA "
            f"{dim.counterbore_mm}/{dim.cb_mm}M B/C "
            f"{dim.thickness_key}"
        )

        lines = [
            "%",
            f"{dim.program_number} ({description})",
            "",
            "(STEP)",
            "",
            self.generate_tool_change_position(),
            "G50 S2800 (MAX RPM)",
        ]

        return lines

    def generate_op1_drilling(self) -> Tuple[List[str], float]:
        """Generate OP1 drilling operation."""
        dim = self.dimensions

        # Get drill depth from table
        drill_depth = DepthTable.get_drill_depth(dim.thickness_key)

        # Get P-code
        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")

        # Get drilling parameters
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
        Generate OP1 boring for STEP spacer.

        Two-zone boring:
        1. Inner bore (holder) to full drill_depth
        2. Counterbore shelf to step_depth only
        """
        dim = self.dimensions

        # Get P-code
        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")

        # Get boring parameters
        bore_params = FeedsSpeedsCalculator.get_bore_params(
            dim.round_size,
            dim.thickness_inches,
            depth_of_cut=0.15,
            use_calculated=dim.use_calculated_feeds
        )

        # Convert step depth to negative Z
        step_depth_z = -abs(dim.step_depth_inches)

        # Calculate passes for inner bore
        holder_prefinish = dim.cb_inches - 0.1  # Use cb_inches as holder diameter
        inner_passes = []
        current_x = 2.6
        while current_x < holder_prefinish:
            inner_passes.append(round(current_x, 4))
            next_x = current_x + 0.300
            if next_x >= holder_prefinish:
                break
            current_x = next_x
        if inner_passes and inner_passes[-1] < holder_prefinish:
            inner_passes.append(round(holder_prefinish, 4))

        # Calculate passes for counterbore shelf
        counterbore_prefinish = dim.counterbore_inches - 0.1
        shelf_passes = []
        current_x = dim.cb_inches + 0.3
        while current_x < counterbore_prefinish:
            shelf_passes.append(round(current_x, 4))
            next_x = current_x + 0.300
            if next_x >= counterbore_prefinish:
                break
            current_x = next_x
        if shelf_passes and shelf_passes[-1] < counterbore_prefinish:
            shelf_passes.append(round(counterbore_prefinish, 4))

        lines = [
            "",
            "(---------------------------)",
            "(OP1: BORING STEP SPACER)",
            "(---------------------------)",
            "T121 (BORE)",
            f"G50 S{bore_params.max_rpm}",
            f"G97 S{bore_params.rpm} M03",
            f"G96 S{bore_params.css} M08",
            f"G00 G154 {pcode} X2.3 Z2.",
            "Z0.2",
            "",
            "(ZONE 1: Inner bore to holder diameter - full depth)",
        ]

        # Zone 1: Inner bore passes
        if inner_passes:
            lines.append(f"X{self.format_gcode_value(inner_passes[0])}")
            current_x = inner_passes[0]

            for i, x_pass in enumerate(inner_passes):
                if abs(current_x - x_pass) > 0.001:
                    lines.append(f"X{self.format_gcode_value(x_pass)}")
                    current_x = x_pass

                lines.append(
                    f"G01 Z{self.format_gcode_value(drill_depth)} "
                    f"F{self.format_gcode_value(bore_params.feed_rough)}"
                )

                clearance_x = x_pass - 0.1
                lines.append(f"X{self.format_gcode_value(clearance_x)}")
                lines.append("G00 Z0.2")
                current_x = clearance_x

                if i < len(inner_passes) - 1:
                    lines.append(f"X{self.format_gcode_value(inner_passes[i + 1])}")
                    current_x = inner_passes[i + 1]

        # Zone 2: Counterbore shelf passes
        lines.append("")
        lines.append("(ZONE 2: Counterbore shelf - step depth only)")

        if shelf_passes:
            lines.append(f"X{self.format_gcode_value(shelf_passes[0])}")

            for i, x_pass in enumerate(shelf_passes):
                if i > 0:
                    lines.append(f"X{self.format_gcode_value(x_pass)}")

                # Only bore to step depth!
                lines.append(
                    f"G01 Z{self.format_gcode_value(step_depth_z)} "
                    f"F{self.format_gcode_value(bore_params.feed_rough)}"
                )

                clearance_x = x_pass - 0.1
                lines.append(f"X{self.format_gcode_value(clearance_x)}")
                lines.append("G00 Z0.2")

                if i < len(shelf_passes) - 1:
                    lines.append(f"X{self.format_gcode_value(shelf_passes[i + 1])}")

        # Zone 3: Finishing with chamfer
        lines.append("")
        lines.append("(ZONE 3: Finishing with chamfer)")

        chamfer_depth = 0.15
        x_chamfer_start = dim.counterbore_inches + (chamfer_depth * 2)

        lines.extend([
            f"X{self.format_gcode_value(x_chamfer_start)}",
            f"G01 Z0 F{self.format_gcode_value(bore_params.feed_finish)}",
            # 45 degree chamfer at counterbore edge
            f"G01 X{self.format_gcode_value(dim.counterbore_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(bore_params.feed_chamfer)}",
            # Finish counterbore to step depth
            f"Z{self.format_gcode_value(step_depth_z)} "
            f"F{self.format_gcode_value(bore_params.feed_finish)}",
            # Move to holder diameter (continuous)
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"F{self.format_gcode_value(bore_params.feed_finish)}",
            # Finish holder bore to full depth
            f"Z{self.format_gcode_value(drill_depth)} "
            f"F{self.format_gcode_value(bore_params.feed_finish)}",
        ])

        # Final retract
        final_clearance_x = dim.cb_inches - 0.1
        lines.extend([
            f"X{self.format_gcode_value(final_clearance_x)}",
            "G00 Z2.",
            "M09",
            self.generate_home_position(),
        ])

        return lines

    def generate_op1_turning(self) -> List[str]:
        """Generate OP1 outer profile turning operation."""
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")
        profile_depth = DepthTable.get_profile_depth(dim.thickness_key)

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
        """Generate OP2 turning/facing operation."""
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op2")

        turn_params = FeedsSpeedsCalculator.get_turn_op2_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        start_x = round(dim.round_size - 0.05, 2)
        finish_x = round(dim.round_size - 0.08, 2)
        # For STEP, stop at holder - 0.1mm
        cut_to_x = round(dim.cb_inches - self.mm_to_inches(0.1), 4)

        lines = self.generate_flip_part_section()

        lines.extend([
            "G50 S2850 (MAX RPM)",
            "",
            "T303 (TURN TOOL)",
            f"G97 S{turn_params.rpm} M03",
            f"G00 G154 {pcode} X{start_x} Z0.1 M08",
            f"G96 S{turn_params.css}",
            "G00 Z0.",
            f"G01 X{self.format_gcode_value(finish_x)} "
            f"F{self.format_gcode_value(turn_params.feed_finish)}",
            f"Z-0.01 F{self.format_gcode_value(turn_params.feed_finish)}",
            f"X{self.format_gcode_value(cut_to_x)} "
            f"F{self.format_gcode_value(turn_params.feed_finish)}",
            "G00 Z0.1",
            "G00 Z1.",
            "M09",
            "G53 X-11. Z-13.",
            "M01",
        ])

        return lines

    def generate_op2_chamfer(self) -> List[str]:
        """Generate OP2 chamfer at holder bore."""
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op2")

        chamfer_params = FeedsSpeedsCalculator.get_chamfer_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        # Chamfer the holder (inner bore), not counterbore
        chamfer_depth = 0.1
        x_chamfer_start = dim.cb_inches + (chamfer_depth * 2)

        lines = [
            "",
            "(---------------------------)",
            "(OP2: CHAMFER HOLDER)",
            "(---------------------------)",
            "T121 (CHAMFER BORE)",
            f"G50 S{chamfer_params.max_rpm}",
            f"G97 S{chamfer_params.rpm} M03",
            f"G96 S{chamfer_params.css} M08",
            f"G154 {pcode} G00 X{self.format_gcode_value(x_chamfer_start)} Z1.",
            "Z0.",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(chamfer_params.feed)}",
            self.generate_home_position(),
        ]

        return lines

    def generate_footer(self) -> List[str]:
        """Generate program footer."""
        return self.generate_common_footer()
