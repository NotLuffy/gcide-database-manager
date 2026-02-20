"""
Steel Ring Recess Diameter Validator

For steel ring spacers the Side-2 counterbore (recess) must be sized so
the ring is retained with a slight interference fit.

Standard ring ODs and acceptable recess ranges
───────────────────────────────────────────────
  Ring OD   │  Recess min  │  Recess max
  5.000"    │   4.990"     │   4.992"
  5.250"    │   5.240"     │   5.242"
  6.000"    │   5.990"     │   5.992"
  6.500"    │   6.490"     │   6.492"

Rule: recess = ring_OD − 0.008" to ring_OD − 0.010"

The detected value comes from result.counter_bore_diameter which the
parser stores in mm (X-value × 25.4).  This validator converts to
inches for comparison.

Only runs when spacer_type contains 'steel' (steel ring programs).
"""

from typing import List, Optional, Tuple


# ── Lookup table ─────────────────────────────────────────────────────────────
# ring OD (inches) → (recess_min_inches, recess_max_inches)
STEEL_RING_RECESS_TABLE = {
    5.000: (4.990, 4.992),
    5.250: (5.240, 5.242),
    6.000: (5.990, 5.992),
    6.500: (6.490, 6.492),
}

# How close the detected value must be to a ring's mid-point before we
# compare it against that ring's tolerance window.
_SEARCH_WINDOW = 0.030   # inches


class SteelRingRecessValidator:
    """
    Validates the Side-2 recess diameter on steel ring spacer programs.

    Errors  → recess too tight (ring will crack housing or not press in)
    Warnings→ recess too loose (ring will not be retained) or unrecognised size
    """

    def validate(
        self,
        spacer_type: Optional[str],
        counter_bore_diameter_mm: Optional[float],
    ) -> Tuple[List[str], List[str]]:
        """
        Args:
            spacer_type:              Detected spacer type from parser.
            counter_bore_diameter_mm: Side-2 recess diameter in mm
                                      (result.counter_bore_diameter).

        Returns:
            (errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Only applies to steel ring programs
        if not spacer_type or 'steel' not in spacer_type.lower():
            return errors, warnings

        if counter_bore_diameter_mm is None:
            warnings.append(
                "Steel ring spacer: Side-2 recess diameter not detected — "
                "unable to verify ring interference-fit tolerance."
            )
            return errors, warnings

        recess_in = counter_bore_diameter_mm / 25.4

        # Find the ring OD whose mid-recess is closest to what was detected
        def _mid(od: float) -> float:
            lo, hi = STEEL_RING_RECESS_TABLE[od]
            return (lo + hi) / 2.0

        closest_od = min(STEEL_RING_RECESS_TABLE, key=lambda od: abs(recess_in - _mid(od)))
        lo, hi = STEEL_RING_RECESS_TABLE[closest_od]
        distance = abs(recess_in - _mid(closest_od))

        if distance > _SEARCH_WINDOW:
            # Does not match any known ring size
            ring_list = ", ".join(
                f"{od:.3f}\""
                for od in sorted(STEEL_RING_RECESS_TABLE)
            )
            warnings.append(
                f"Steel ring recess {recess_in:.4f}\" "
                f"({counter_bore_diameter_mm:.2f} mm) does not match any "
                f"standard steel ring size. "
                f"Known ring ODs: {ring_list}. "
                f"Expected recess = ring OD \u2212 0.008\" to 0.010\"."
            )
            return errors, warnings

        # Value is targeting closest_od — check it is within tolerance
        if lo <= recess_in <= hi:
            pass  # Within spec — no issue

        elif recess_in < lo:
            over = lo - recess_in
            errors.append(
                f"Steel ring recess {recess_in:.4f}\" "
                f"({counter_bore_diameter_mm:.2f} mm) is too tight for "
                f"{closest_od:.3f}\" ring "
                f"(minimum recess: {lo:.4f}\", over by {over:.4f}\"). "
                f"Ring may crack housing or be impossible to press in."
            )

        else:  # recess_in > hi
            under = recess_in - hi
            warnings.append(
                f"Steel ring recess {recess_in:.4f}\" "
                f"({counter_bore_diameter_mm:.2f} mm) is too loose for "
                f"{closest_od:.3f}\" ring "
                f"(maximum recess: {hi:.4f}\", over by {under:.4f}\"). "
                f"Ring may not be retained securely."
            )

        return errors, warnings
