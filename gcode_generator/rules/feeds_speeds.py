"""
Feeds and Speeds Calculator

Calculates cutting parameters for 6061-T6 Aluminum on Haas lathes.
Provides both generalized (proven) values and calculated values based on
machining formulas.

Key concepts:
- RPM: Spindle revolutions per minute
- CSS: Constant Surface Speed (surface feet per minute)
- IPR: Inches Per Revolution (feed rate)
- SFM: Surface Feet per Minute
"""

import math
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class DrillParams:
    """Drilling operation parameters."""
    rpm: int
    feed: float  # IPR
    peck: float  # Peck depth in inches


@dataclass
class BoreParams:
    """Boring operation parameters."""
    max_rpm: int
    rpm: int
    css: int
    feed_rough: float
    feed_finish: float
    feed_chamfer: float


@dataclass
class TurnParams:
    """Turning operation parameters."""
    max_rpm: int
    rpm: int
    css: int
    feed_rough: float
    feed_finish: float
    feed_profile: float


@dataclass
class ChamferParams:
    """Chamfering operation parameters."""
    max_rpm: int
    rpm: int
    css: int
    feed: float


class FeedsSpeedsCalculator:
    """
    Calculates feeds and speeds for machining operations.

    Material: 6061-T6 Aluminum
    - Recommended SFM: 800-1200 (roughing), 1200-1600 (finishing)
    - High machinability, good chip formation
    """

    # Material properties for 6061-T6 Aluminum
    MATERIAL_SFM_ROUGH = 1000
    MATERIAL_SFM_FINISH = 1400
    MATERIAL_CHIP_LOAD = 0.006  # Base chip load per tooth

    # Machine limits
    DEFAULT_MAX_RPM = 2800
    DRILL_MAX_RPM = 2000
    BORE_MAX_RPM = 2300
    TURN_MAX_RPM = 2800

    # Standard drill diameter
    STANDARD_DRILL_DIA = 2.3  # inches

    @classmethod
    def calculate_rpm(cls, sfm: float, diameter: float) -> int:
        """
        Calculate RPM from surface feet per minute and diameter.

        Formula: RPM = (SFM * 12) / (PI * Diameter)

        Args:
            sfm: Surface feet per minute
            diameter: Cutting diameter in inches

        Returns:
            RPM (clamped to machine limits)
        """
        if diameter <= 0:
            return cls.DEFAULT_MAX_RPM

        rpm = (sfm * 12) / (math.pi * diameter)
        return int(min(cls.DEFAULT_MAX_RPM, max(400, rpm)))

    @classmethod
    def get_drill_params(
        cls,
        thickness_inches: float,
        round_size: float,
        use_calculated: bool = False
    ) -> DrillParams:
        """
        Get drilling parameters.

        Args:
            thickness_inches: Part thickness in inches
            round_size: Round stock diameter in inches
            use_calculated: Use formula-based calculation vs proven values

        Returns:
            DrillParams with rpm, feed, and peck depth
        """
        if use_calculated:
            # Calculate based on machining formulas
            sfm = 600  # Conservative for deep hole drilling
            rpm = cls.calculate_rpm(sfm, cls.STANDARD_DRILL_DIA)
            rpm = min(cls.DRILL_MAX_RPM, rpm)

            # Reduce feed for deeper holes
            base_ipr = 0.008
            depth_factor = max(0.5, 1.0 - (thickness_inches / 10.0))
            feed = round(base_ipr * depth_factor, 4)

            # Peck depth based on drill diameter
            peck = round(min(1.5, cls.STANDARD_DRILL_DIA * 0.4), 2)

            return DrillParams(rpm=rpm, feed=feed, peck=peck)

        # Proven/generalized values
        if thickness_inches <= 1.65:
            return DrillParams(rpm=1250, feed=0.008, peck=0.8)
        else:
            # Deeper holes: slower feed, larger peck
            feed = max(0.004, 0.008 - (thickness_inches - 1.65) * 0.001)
            peck = min(1.2, 0.8 + (thickness_inches - 1.65) * 0.15)
            return DrillParams(rpm=1250, feed=round(feed, 4), peck=round(peck, 2))

    @classmethod
    def get_bore_params(
        cls,
        round_size: float,
        thickness_inches: float,
        depth_of_cut: Optional[float] = None,
        use_calculated: bool = False
    ) -> BoreParams:
        """
        Get boring parameters.

        Args:
            round_size: Round stock diameter in inches
            thickness_inches: Part thickness in inches
            depth_of_cut: Radial depth of cut (for feed adjustment)
            use_calculated: Use formula-based calculation vs proven values

        Returns:
            BoreParams with speeds and feeds
        """
        if use_calculated and depth_of_cut is not None:
            # Adjust feed based on depth of cut
            if depth_of_cut > 0.25:
                feed_rough = 0.015
            elif depth_of_cut > 0.15:
                feed_rough = 0.018
            else:
                feed_rough = 0.02

            return BoreParams(
                max_rpm=cls.BORE_MAX_RPM,
                rpm=1800,
                css=int(cls.MATERIAL_SFM_FINISH),
                feed_rough=feed_rough,
                feed_finish=0.009,
                feed_chamfer=0.008
            )

        # Proven/generalized values
        base_feed_rough = 0.02
        base_feed_finish = 0.009

        if depth_of_cut:
            if depth_of_cut > 0.25:
                base_feed_rough = 0.015
            elif depth_of_cut > 0.20:
                base_feed_rough = 0.018

        return BoreParams(
            max_rpm=2300,
            rpm=1800,
            css=1450,
            feed_rough=base_feed_rough,
            feed_finish=base_feed_finish,
            feed_chamfer=0.008
        )

    @classmethod
    def get_turn_params(
        cls,
        round_size: float,
        thickness_inches: float,
        use_calculated: bool = False
    ) -> TurnParams:
        """
        Get turning parameters for OP1.

        Args:
            round_size: Round stock diameter in inches
            thickness_inches: Part thickness in inches
            use_calculated: Use formula-based calculation vs proven values

        Returns:
            TurnParams with speeds and feeds
        """
        if use_calculated:
            sfm_rough = 1000
            sfm_finish = 1300

            rpm = cls.calculate_rpm(sfm_rough, round_size)
            rpm = min(cls.TURN_MAX_RPM, max(600, rpm))

            return TurnParams(
                max_rpm=cls.TURN_MAX_RPM,
                rpm=rpm,
                css=int(sfm_finish),
                feed_rough=0.02,
                feed_finish=0.008,
                feed_profile=0.015
            )

        # Proven values based on round size
        if round_size >= 9.0:
            # Larger diameter: slower RPM to maintain surface speed
            return TurnParams(
                max_rpm=2800,
                rpm=900,
                css=1200,
                feed_rough=0.02,
                feed_finish=0.008,
                feed_profile=0.015
            )
        else:
            # Smaller diameter: higher RPM
            return TurnParams(
                max_rpm=2800,
                rpm=1950,
                css=1200,
                feed_rough=0.02,
                feed_finish=0.008,
                feed_profile=0.015
            )

    @classmethod
    def get_turn_op2_params(
        cls,
        round_size: float,
        thickness_inches: float,
        use_calculated: bool = False
    ) -> TurnParams:
        """
        Get turning parameters for OP2 (flip side).

        Args:
            round_size: Round stock diameter in inches
            thickness_inches: Part thickness in inches
            use_calculated: Use formula-based calculation vs proven values

        Returns:
            TurnParams with speeds and feeds
        """
        if use_calculated:
            sfm = 1200 if round_size >= 9.0 else 1000
            rpm = cls.calculate_rpm(sfm, round_size)
            rpm = min(2850, max(800, rpm))

            return TurnParams(
                max_rpm=2850,
                rpm=rpm,
                css=int(sfm * 1.3),
                feed_rough=0.013,
                feed_finish=0.009,
                feed_profile=0.013
            )

        # Proven values
        css = 1800 if round_size >= 9.0 else 1600

        return TurnParams(
            max_rpm=2850,
            rpm=2000,
            css=css,
            feed_rough=0.013,
            feed_finish=0.009,
            feed_profile=0.013
        )

    @classmethod
    def get_chamfer_params(
        cls,
        round_size: float,
        thickness_inches: float,
        use_calculated: bool = False
    ) -> ChamferParams:
        """
        Get chamfering parameters for OP2.

        Args:
            round_size: Round stock diameter in inches
            thickness_inches: Part thickness in inches
            use_calculated: Use formula-based calculation vs proven values

        Returns:
            ChamferParams with speeds and feeds
        """
        # Chamfering uses conservative, proven values
        return ChamferParams(
            max_rpm=2250,
            rpm=1750,
            css=950,
            feed=0.008
        )

    @classmethod
    def get_thin_lip_adjustments(cls) -> Dict[str, float]:
        """
        Get feed/speed adjustment factors for thin-lip spacers.

        Thin-lip spacers (CB/OB within ~5mm) need slower, more careful machining
        to avoid breaking the thin wall.

        Returns:
            Dict with adjustment multipliers
        """
        return {
            "feed_multiplier": 0.7,  # 30% slower feeds
            "rpm_multiplier": 0.9,  # 10% slower RPM
            "depth_increment": 0.1,  # Smaller Z increments (0.1" vs 0.2")
        }

    @classmethod
    def adjust_for_depth(cls, base_feed: float, depth_inches: float) -> float:
        """
        Adjust feed rate based on cutting depth.

        Deeper cuts generally need slower feeds for chip evacuation.

        Args:
            base_feed: Base feed rate (IPR)
            depth_inches: Total cutting depth

        Returns:
            Adjusted feed rate
        """
        if depth_inches <= 1.0:
            return base_feed
        elif depth_inches <= 2.0:
            return base_feed * 0.95
        elif depth_inches <= 3.0:
            return base_feed * 0.90
        else:
            return base_feed * 0.85
