"""
Boring Pass Calculator

Calculates the boring passes needed to open up the center bore from the
initial drill size to the final CB diameter.

The boring strategy follows these rules:
1. Start at X2.300 (just above the 2.3" drill hole)
2. Maximum increment of +0.300" per pass
3. Short-step to CB - 0.100" if next pass would exceed CB
4. Final pass to full CB diameter with chamfer

This approach ensures:
- Consistent chip load per pass
- No excessive tool deflection
- Smooth bore finish
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BoringPass:
    """Represents a single boring pass."""
    diameter: float  # X diameter to bore
    depth: float  # Z depth (negative)
    is_roughing: bool  # True for roughing, False for finishing
    is_chamfer: bool  # True if this is a chamfer pass


class BoringPassCalculator:
    """Calculates boring passes for center bore operations."""

    # Starting diameter (just above drill hole size)
    START_DIAMETER = 2.300

    # Maximum diameter increment per pass
    MAX_INCREMENT = 0.300

    # Pre-finish offset (CB - this value = pre-finish pass)
    PREFINISH_OFFSET = 0.100

    # Standard chamfer depth
    CHAMFER_DEPTH = 0.15

    @classmethod
    def calculate_passes(
        cls,
        cb_inches: float,
        drill_depth: float,
        include_chamfer: bool = True
    ) -> List[BoringPass]:
        """
        Calculate all boring passes to reach the target CB.

        Args:
            cb_inches: Target center bore diameter in inches
            drill_depth: Drill depth (negative Z value)
            include_chamfer: Whether to include chamfer pass

        Returns:
            List of BoringPass objects in order of execution
        """
        passes = []
        current_x = cls.START_DIAMETER

        # Calculate roughing passes
        while current_x < cb_inches:
            next_x = current_x + cls.MAX_INCREMENT

            # Check if next pass would exceed or get close to CB
            if next_x >= cb_inches:
                # Add pre-finish pass if we haven't reached it
                prefinish_x = cb_inches - cls.PREFINISH_OFFSET
                if current_x < prefinish_x:
                    passes.append(BoringPass(
                        diameter=round(prefinish_x, 4),
                        depth=drill_depth,
                        is_roughing=True,
                        is_chamfer=False
                    ))
                break
            else:
                passes.append(BoringPass(
                    diameter=round(next_x, 4),
                    depth=drill_depth,
                    is_roughing=True,
                    is_chamfer=False
                ))
                current_x = next_x

        # Add chamfer pass if requested
        if include_chamfer:
            chamfer_start_x = cb_inches + (cls.CHAMFER_DEPTH * 2)
            passes.append(BoringPass(
                diameter=round(chamfer_start_x, 4),
                depth=-cls.CHAMFER_DEPTH,  # Chamfer is shallow
                is_roughing=False,
                is_chamfer=True
            ))

        # Add final finish pass at CB diameter
        passes.append(BoringPass(
            diameter=round(cb_inches, 4),
            depth=drill_depth,
            is_roughing=False,
            is_chamfer=False
        ))

        return passes

    @classmethod
    def calculate_diameters_only(cls, cb_inches: float) -> List[float]:
        """
        Calculate just the boring pass diameters (without depth info).

        This matches the original prototype's calculate_boring_passes method.

        Args:
            cb_inches: Target center bore diameter in inches

        Returns:
            List of X diameters for each pass
        """
        diameters = []
        current_x = cls.START_DIAMETER

        while current_x < cb_inches:
            diameters.append(round(current_x, 3))

            next_x = current_x + cls.MAX_INCREMENT

            if next_x >= cb_inches:
                # Add pre-finish pass
                prefinish_x = cb_inches - cls.PREFINISH_OFFSET
                if current_x < prefinish_x:
                    diameters.append(round(prefinish_x, 3))
                break

            current_x = next_x

        return diameters

    @classmethod
    def calculate_step_boring_passes(
        cls,
        holder_inches: float,
        counterbore_inches: float,
        drill_depth: float,
        step_depth: float
    ) -> Tuple[List[BoringPass], List[BoringPass]]:
        """
        Calculate boring passes for STEP spacers.

        STEP spacers have two zones:
        1. Inner bore (holder diameter) - goes to full drill_depth
        2. Counterbore shelf - only goes to step_depth

        Args:
            holder_inches: Inner (holder) diameter in inches
            counterbore_inches: Outer counterbore diameter in inches
            drill_depth: Full drill depth (negative)
            step_depth: Depth of the step/shelf (negative)

        Returns:
            Tuple of (inner_passes, shelf_passes)
        """
        # Zone 1: Inner bore to holder diameter (full depth)
        inner_passes = []
        current_x = cls.START_DIAMETER
        holder_prefinish = holder_inches - cls.PREFINISH_OFFSET

        while current_x < holder_prefinish:
            next_x = current_x + cls.MAX_INCREMENT
            if next_x >= holder_prefinish:
                break
            inner_passes.append(BoringPass(
                diameter=round(next_x, 4),
                depth=drill_depth,
                is_roughing=True,
                is_chamfer=False
            ))
            current_x = next_x

        # Add pre-finish pass for inner bore
        if current_x < holder_prefinish:
            inner_passes.append(BoringPass(
                diameter=round(holder_prefinish, 4),
                depth=drill_depth,
                is_roughing=True,
                is_chamfer=False
            ))

        # Zone 2: Counterbore shelf (step depth only)
        shelf_passes = []
        current_x = holder_inches + cls.MAX_INCREMENT
        counterbore_prefinish = counterbore_inches - cls.PREFINISH_OFFSET

        while current_x < counterbore_prefinish:
            shelf_passes.append(BoringPass(
                diameter=round(current_x, 4),
                depth=step_depth,  # Only to step depth!
                is_roughing=True,
                is_chamfer=False
            ))
            next_x = current_x + cls.MAX_INCREMENT
            if next_x >= counterbore_prefinish:
                break
            current_x = next_x

        # Add pre-finish pass for shelf
        if shelf_passes and shelf_passes[-1].diameter < counterbore_prefinish:
            shelf_passes.append(BoringPass(
                diameter=round(counterbore_prefinish, 4),
                depth=step_depth,
                is_roughing=True,
                is_chamfer=False
            ))

        return (inner_passes, shelf_passes)

    @classmethod
    def get_chamfer_position(cls, bore_diameter: float, chamfer_depth: float = 0.15) -> float:
        """
        Calculate the X start position for a 45-degree chamfer.

        For a 45-degree chamfer:
        X_start = bore_diameter + (chamfer_depth * 2)

        Args:
            bore_diameter: The bore diameter being chamfered
            chamfer_depth: Depth of chamfer in Z direction

        Returns:
            X start position for chamfer cut
        """
        return bore_diameter + (chamfer_depth * 2)

    @classmethod
    def estimate_cycle_time(
        cls,
        passes: List[BoringPass],
        feed_rough: float = 0.02,
        feed_finish: float = 0.009,
        rpm: int = 1800
    ) -> float:
        """
        Estimate the boring cycle time in seconds.

        This is a rough estimate for planning purposes.

        Args:
            passes: List of BoringPass objects
            feed_rough: Roughing feed rate (IPR)
            feed_finish: Finishing feed rate (IPR)
            rpm: Spindle RPM

        Returns:
            Estimated time in seconds
        """
        total_time = 0.0

        for pass_info in passes:
            # Time = distance / (feed * rpm)
            z_distance = abs(pass_info.depth)
            feed = feed_rough if pass_info.is_roughing else feed_finish

            # Cutting time
            cutting_time = z_distance / (feed * rpm) * 60  # Convert to seconds

            # Add rapid moves (estimated)
            rapid_time = 0.5  # Approximate rapid move time

            total_time += cutting_time + rapid_time

        return round(total_time, 1)

    @classmethod
    def validate_boring_parameters(
        cls,
        cb_inches: float,
        drill_depth: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate boring parameters before calculation.

        Args:
            cb_inches: Target center bore diameter
            drill_depth: Drill depth (negative)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if cb_inches <= cls.START_DIAMETER:
            return (
                False,
                f"CB diameter ({cb_inches}) must be larger than "
                f"starting diameter ({cls.START_DIAMETER})"
            )

        if drill_depth >= 0:
            return (False, "Drill depth must be negative")

        if cb_inches > 6.0:
            return (
                False,
                f"CB diameter ({cb_inches}) exceeds maximum boring range. "
                "Check your input values."
            )

        return (True, None)
