"""
Steel Ring Spacer Generator

Generates G-code for steel ring wheel spacers.
Steel ring spacers are designed to accept a pressed-in steel centering ring.

Key features from real programs (o80004, o80651, o80652, o11022):
- OP1: Turn OD profile FIRST, then drill/bore
- Center bore with step/shelf for ring seating
- OP2: Turn profile both sides, then chamfer bore with ring pocket (Z-0.55)
- Step diameter typically around CB - 0.1 to 0.2"
"""

from typing import List, Tuple

from .base import BaseSpacerGenerator, SpacerDimensions
from ..rules.pcodes import PCodeManager
from ..rules.depths import DepthTable
from ..rules.feeds_speeds import FeedsSpeedsCalculator
from ..rules.boring_passes import BoringPassCalculator


class SteelRingSpacerGenerator(BaseSpacerGenerator):
    """
    Generator for steel ring wheel spacers.

    Steel ring spacers have:
    - Center bore sized for press-fit steel ring
    - Step/shelf in bore for ring seating
    - Ring pocket chamfer (Z-0.55 depth) in OP2
    - OP1 turning done BEFORE drilling/boring
    """

    # Steel ring specific parameters
    RING_POCKET_DEPTH = 0.55  # Depth of ring seating pocket
    STEP_OFFSET = 0.15  # Difference between full depth and step depth

    def __init__(self, dimensions: SpacerDimensions):
        """Initialize with standard dimensions."""
        super().__init__(dimensions)

    def generate(self) -> str:
        """
        Generate the complete G-code program.

        Steel ring programs have a different order:
        1. Header
        2. OP1 Turning (BEFORE drilling/boring)
        3. OP1 Drilling
        4. OP1 Boring with step
        5. Flip part
        6. OP2 Turning
        7. OP2 Chamfer with ring pocket
        8. Footer
        """
        self.gcode_lines = []

        # Generate each section in steel ring order
        header = self.generate_header()
        self.add_lines(header)

        # OP1 Turning FIRST (before drilling)
        turning = self.generate_op1_turning()
        self.add_lines(turning)

        # Then drilling
        drilling, drill_depth = self.generate_op1_drilling()
        self.add_lines(drilling)

        # Then boring with step
        boring = self.generate_op1_boring(drill_depth)
        self.add_lines(boring)

        # OP2
        op2_turning = self.generate_op2_turning()
        self.add_lines(op2_turning)

        op2_chamfer = self.generate_op2_chamfer()
        self.add_lines(op2_chamfer)

        footer = self.generate_footer()
        self.add_lines(footer)

        return "\n".join(self.gcode_lines)

    def generate_header(self) -> List[str]:
        """Generate program header with steel ring designation."""
        dim = self.dimensions

        # Build description matching real files (e.g., "8IN DIA 116.7MM 2.5 STEEL HCS-1")
        description = (
            f"{dim.round_size}IN DIA {dim.cb_mm}MM "
            f"{dim.thickness_key} STEEL S-1"
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

    def generate_op1_turning(self) -> List[str]:
        """
        Generate OP1 outer profile turning operation.

        For steel rings, this comes BEFORE drilling/boring.
        Pattern from o11022 lines 16-33.
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
            f"X{self.format_gcode_value(face_to_x)} "
            f"F{self.format_gcode_value(turn_params.feed_rough)}",
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
        ]

        return lines

    def generate_op1_drilling(self) -> Tuple[List[str], float]:
        """Generate OP1 drilling operation."""
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
                "G00 G80 Z2.",
            ])

        return (lines, drill_depth)

    def generate_op1_boring(self, drill_depth: float) -> List[str]:
        """
        Generate OP1 boring operation for steel ring bore WITH STEP.

        Creates a step/shelf in the bore for ring seating.
        Pattern from real programs (o11022 lines 46-96):
        1. Bore passes to full depth
        2. Chamfer to CB
        3. Go to step depth (full_depth + 0.15")
        4. Move inward to step diameter (CB - 0.1 to 0.2")
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op1")
        boring_passes = BoringPassCalculator.calculate_diameters_only(dim.cb_inches)

        bore_params = FeedsSpeedsCalculator.get_bore_params(
            dim.round_size,
            dim.thickness_inches,
            depth_of_cut=0.15,
            use_calculated=dim.use_calculated_feeds
        )

        chamfer_depth = 0.15
        x_chamfer_start = dim.cb_inches + (chamfer_depth * 2)

        # Step calculations - from o11022: step_z = -2.0 when full = -2.15
        step_z = drill_depth + self.STEP_OFFSET  # Less negative (shallower)
        step_diameter = dim.cb_inches - 0.175  # Step inward from CB

        lines = [
            "",
            "T121 (BORE)",
            f"G50 S{bore_params.max_rpm}",
            f"G97 S{bore_params.rpm} M03",
            f"G96 S{bore_params.css} M08",
            f"G00 G154 {pcode} X2.3 Z2.",
            "Z0.2",
        ]

        # Generate boring passes - all go to full depth
        current_x = 2.3
        for i, x_pass in enumerate(boring_passes):
            if abs(current_x - x_pass) > 0.001:
                lines.append(f"X{self.format_gcode_value(x_pass)}")
                current_x = x_pass

            lines.append(
                f"G01 Z{self.format_gcode_value(drill_depth)} "
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

        # Chamfer and step creation (matching o11022 pattern lines 90-95)
        lines.extend([
            f"X{self.format_gcode_value(x_chamfer_start)}",
            f"G01 Z0 F{self.format_gcode_value(bore_params.feed_finish)}",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(bore_params.feed_chamfer)}",
            f"Z{self.format_gcode_value(step_z)}",
            f"X{self.format_gcode_value(step_diameter)}",
        ])

        # Retract
        lines.extend([
            "G00 Z2.",
            "M09",
            self.generate_home_position(),
            "",
            "M00",
        ])

        return lines

    def generate_op2_turning(self) -> List[str]:
        """
        Generate OP2 turning/facing operation.

        Pattern from real steel ring files - face and profile.
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
        Generate OP2 chamfer bore operation with ring pocket.

        Creates the ring seating pocket at Z-0.55 depth.
        Pattern from real files (o80651 lines 125-133, o11022 lines 134-145):
        - Position at larger X
        - Go to ring pocket depth (Z-0.55)
        - Feed inward to create pocket
        """
        dim = self.dimensions

        pcode = PCodeManager.get_pcode(dim.lathe, dim.thickness_key, "op2")

        chamfer_params = FeedsSpeedsCalculator.get_chamfer_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        # Ring pocket dimensions
        pocket_start_x = dim.cb_inches + 0.4  # Start wider
        pocket_end_x = dim.cb_inches  # End at CB

        lines = [
            "",
            "T121 (CHAMFER BORE)",
            f"G50 S{chamfer_params.max_rpm}",
            f"G97 S{chamfer_params.rpm} M03",
            f"G96 S{chamfer_params.css} M08",
            f"G154 {pcode} G00 X{self.format_gcode_value(pocket_start_x)} Z1.",
            "Z0.2",
            # Ring pocket pass
            f"G01 Z-{self.format_gcode_value(self.RING_POCKET_DEPTH)} "
            f"F{self.format_gcode_value(chamfer_params.feed)}",
            f"X{self.format_gcode_value(pocket_end_x)}",
            "G00 Z0",
            "",
            self.generate_home_position(),
        ]

        return lines

    def generate_footer(self) -> List[str]:
        """Generate program footer."""
        return self.generate_common_footer()
