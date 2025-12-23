"""
Hub-Centric Spacer Generator

Generates G-code for hub-centric wheel spacers.
These spacers have a raised hub ring that centers on the vehicle's hub bore.

Key features:
- Center bore (CB) that fits over the wheel studs
- Outer bore (OB) that fits over the vehicle hub
- Raised hub projection on one side
- OP2 creates the hub pocket/ring
"""

from typing import List, Tuple

from .base import BaseSpacerGenerator, HubCentricDimensions
from ..rules.pcodes import PCodeManager
from ..rules.depths import DepthTable
from ..rules.feeds_speeds import FeedsSpeedsCalculator
from ..rules.boring_passes import BoringPassCalculator


class HubCentricSpacerGenerator(BaseSpacerGenerator):
    """
    Generator for hub-centric wheel spacers.

    Hub-centric spacers have:
    - Center bore (CB) for wheel mounting
    - Outer bore (OB) that rides on the vehicle hub
    - Raised hub ring on one side for centering
    """

    dimensions: HubCentricDimensions  # Type hint for IDE

    def __init__(self, dimensions: HubCentricDimensions):
        """Initialize with hub-centric specific dimensions."""
        super().__init__(dimensions)
        self.dimensions = dimensions

    def _get_pcode_thickness_key(self) -> str:
        """
        Get the thickness key for P-code lookup.

        For hub-centric spacers, the effective thickness includes the hub height.
        """
        dim = self.dimensions
        total_thickness = dim.thickness_inches + dim.hub_height_inches

        # Round to nearest 0.25" increment for P-code lookup
        rounded_total = round(total_thickness * 4) / 4
        return f"{rounded_total:.2f}"

    def generate_header(self) -> List[str]:
        """Generate program header with description."""
        dim = self.dimensions

        # Build description: "7.0IN DIA 87.1/93.1MM 1.50 HC 0.5"
        description = (
            f"{dim.round_size}IN DIA {dim.cb_mm}/{dim.ob_mm}MM "
            f"{dim.thickness_key} HC {dim.hub_height_inches}"
        )

        lines = [
            "%",
            f"{dim.program_number} ({description})",
            "",
            self.generate_tool_change_position(),
            "G50 S2800 (MAX RPM)",
        ]

        return lines

    def generate_op1_drilling(self) -> Tuple[List[str], float]:
        """Generate OP1 drilling operation."""
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        # Get drill depth from table based on total height
        drill_depth = DepthTable.get_drill_depth(pcode_key)

        # Get P-code
        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op1")

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

        # Peck drilling
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
        """Generate OP1 boring operation with chamfer."""
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        # Get P-code
        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op1")

        # Calculate boring passes
        boring_passes = BoringPassCalculator.calculate_diameters_only(dim.cb_inches)

        # Get boring parameters
        bore_params = FeedsSpeedsCalculator.get_bore_params(
            dim.round_size,
            dim.thickness_inches,
            depth_of_cut=0.15,
            use_calculated=dim.use_calculated_feeds
        )

        # Calculate chamfer position
        chamfer_depth = 0.15
        x_chamfer_start = dim.cb_inches + (chamfer_depth * 2)

        lines = [
            "",
            "(---------------------------)",
            "(OP1: BORING CENTER BORE)",
            "(---------------------------)",
            "T121 (BORE)",
            f"G50 S{bore_params.max_rpm}",
            f"G97 S{bore_params.rpm} M03",
            f"G96 S{bore_params.css} M08",
            f"G00 G154 {pcode} X2.3 Z2.",
            "Z0.2",
        ]

        # Generate boring passes
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

        # Chamfer pass
        lines.extend([
            f"X{self.format_gcode_value(x_chamfer_start)}",
            f"G01 Z0 F{self.format_gcode_value(bore_params.feed_finish)}",
            f"G01 X{self.format_gcode_value(dim.cb_inches)} "
            f"Z-{self.format_gcode_value(chamfer_depth)} "
            f"F{self.format_gcode_value(bore_params.feed_chamfer)}",
            f"Z{self.format_gcode_value(drill_depth)}",
        ])

        # Final retract
        final_clearance_x = dim.cb_inches - 0.1
        lines.extend([
            f"X{self.format_gcode_value(final_clearance_x)}",
            "G00 Z0.2",
            f"X{self.format_gcode_value(boring_passes[-1] if boring_passes else 2.6)}",
            "G00 Z2.",
            "M09",
            self.generate_home_position(),
        ])

        return lines

    def generate_op1_turning(self) -> List[str]:
        """Generate OP1 outer profile turning operation."""
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        # Get P-code and depths
        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op1")
        profile_depth = DepthTable.get_profile_depth(pcode_key)

        # Get turning parameters
        turn_params = FeedsSpeedsCalculator.get_turn_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        # Calculate positions
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
        """Generate OP2 turning operation for hub creation."""
        dim = self.dimensions
        pcode_key = self._get_pcode_thickness_key()

        # Get P-code
        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op2")

        # Get turning parameters
        turn_params = FeedsSpeedsCalculator.get_turn_op2_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        # Calculate positions
        start_x = round(dim.round_size - 0.05, 2)
        finish_x = round(dim.round_size - 0.08, 2)
        cut_to_x = round(dim.ob_inches + 0.1, 3)  # Stop just outside OB
        hub_depth = dim.hub_height_inches

        lines = self.generate_flip_part_section()

        lines.extend([
            "G50 S2850 (MAX RPM)",
            "",
            "T303 (TURN TOOL)",
            f"G97 S{turn_params.rpm} M03",
            f"G00 G154 {pcode} X{start_x} Z0.1 M08",
            f"G96 S{turn_params.css}",
        ])

        # Hub turning - stair-step approach
        z_depth = 0.1
        z_increment = 0.2

        while z_depth < hub_depth:
            lines.extend([
                f"G01 Z-{self.format_gcode_value(z_depth)} "
                f"F{self.format_gcode_value(turn_params.feed_rough)}",
                f"X{self.format_gcode_value(cut_to_x)}",
                f"G00 X{self.format_gcode_value(start_x)}",
            ])
            z_depth += z_increment

        # Pre-finish pass - go slightly past hub depth, then come back up
        # Pattern from o11001: Z-0.8, Z-0.55, then chamfer
        lines.extend([
            f"G01 Z-{self.format_gcode_value(hub_depth + 0.1)} "
            f"F{self.format_gcode_value(turn_params.feed_rough)}",
            f"Z-{self.format_gcode_value(hub_depth + 0.05)}",
        ])

        # OD chamfer (diagonal move is correct for chamfer)
        lines.append(
            f"G01 X{self.format_gcode_value(finish_x)} "
            f"Z-{self.format_gcode_value(hub_depth)} "
            f"F{self.format_gcode_value(turn_params.feed_finish)}"
        )

        # Final finish pass at OB - X only, no Z (straight move)
        lines.append(
            f"G01 X{self.format_gcode_value(dim.ob_inches)} "
            f"F{self.format_gcode_value(turn_params.feed_finish)} (X IS OB)"
        )

        # Move up hub wall - Z only first (straight move)
        chamfer_z_start = 0.04
        chamfer_x = dim.ob_inches - (chamfer_z_start * 2)

        lines.append(
            f"Z-{self.format_gcode_value(chamfer_z_start)}"
        )

        # Chamfer to top (diagonal move is correct for chamfer)
        lines.append(
            f"G01 X{self.format_gcode_value(chamfer_x)} Z0. "
            f"F{self.format_gcode_value(turn_params.feed_finish)}"
        )

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

        # Get P-code
        pcode = PCodeManager.get_pcode(dim.lathe, pcode_key, "op2")

        # Get chamfer parameters
        chamfer_params = FeedsSpeedsCalculator.get_chamfer_params(
            dim.round_size,
            dim.thickness_inches,
            dim.use_calculated_feeds
        )

        # Calculate positions
        chamfer_depth = 0.1
        x_chamfer_start = dim.cb_inches + (chamfer_depth * 2)

        lines = [
            "",
            "(---------------------------)",
            "(OP2: CHAMFER BORE)",
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
