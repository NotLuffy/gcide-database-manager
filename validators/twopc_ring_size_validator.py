"""
2PC Mating Hub Ring Size Validator

For 2-piece (2PC) spacers the ring OD used to retain the STUD insert inside
the LUG should correspond to the spacer's centre bore (CB) size.

Lookup table  — Centre Bore range → Expected Ring OD(s)
─────────────────────────────────────────────────────────
  CB range (mm)  │  Ring OD (inches)   │  Common fitment
  53 – 61 mm     │  2.690"             │  60mm CB class
  63 – 69 mm     │  3.134"             │  63.4 / 64.1mm CB class
  73 – 83 mm     │  3.505"             │  74 / 77.8 / 78.1mm CB class
  85 – 92 mm     │  3.700" or 3.900"   │  87.1mm CB class
  99 – 116 mm    │  4.600"             │  100 – 110mm CB class

  Gaps (61–63 mm, 69–73 mm, 83–85 mm, 92–99 mm) are intentionally unvalidated
  because ring selection depends on the OD (part size) at those boundaries.

Tolerance: ±0.25" from the nearest expected ring OD, which is wide enough to
allow OD-specific variants (e.g. 8" parts with 77.8mm CB may use 3.7" ring
instead of 3.505") while still catching full ring-class errors.

Field selection strategy:
  • 2PC LUG:  counter_bore_diameter only (the step bore = ring seat).
              hub_diameter on LUG parts typically captures an inner bore,
              not the ring OD, so it is never used for LUG validation.
  • 2PC STUD: counter_bore_diameter first (HC STUD inner hub bore),
              hub_diameter as fallback (hub OD ≈ ring OD for simple STUDs).
  • 2PC UNSURE: skipped — type ambiguity makes ring ID unreliable.

A dimension is rejected as implausible (likely outer-hub or inner-bore) when:
  - it is less than CB + 0.22" (cannot be a ring surrounding that bore), OR
  - it exceeds the max expected ring + 0.30" (outer-hub OD on HC STUD).
"""

from typing import List, Optional, Tuple


# ── Lookup table ──────────────────────────────────────────────────────────────
# (cb_min_mm, cb_max_mm, ring_ods_inches, description)
# Ranges are half-open: cb_min <= cb < cb_max
TWOPC_RING_TABLE = [
    (53.0,  61.0, [2.690],        "60mm CB class"),
    (63.0,  69.0, [3.134],        "63.4–64.1mm CB class"),
    (73.0,  83.0, [3.505],        "74–78.1mm CB class"),
    (85.0,  92.0, [3.700, 3.900], "87.1mm CB class"),
    (99.0, 116.0, [4.600],        "100–110mm CB class"),
]

# ± tolerance for comparing detected ring OD to expected OD.
# Wide enough to allow OD-size variants; tight enough to catch cross-class errors.
_TOLERANCE_IN = 0.25

# Minimum excess over CB: ring must be > CB + this margin.
_MIN_RING_EXCESS_IN = 0.22

# Maximum excess over max expected ring: above this → outer-hub OD, not ring.
_OUTER_HUB_MARGIN_IN = 0.30


class TwoPCRingSizeValidator:
    """
    Validates the ring/hub OD on 2-piece spacer programs.

    Warnings → detected ring dimension does not match the expected OD for
               the spacer's centre bore class.
    No errors are issued (ring mismatch is a production check, not a crash risk).
    """

    def validate(
        self,
        spacer_type: Optional[str],
        center_bore_mm: Optional[float],
        counter_bore_diameter_mm: Optional[float],
        hub_diameter_mm: Optional[float],
    ) -> Tuple[List[str], List[str]]:
        """
        Args:
            spacer_type:              Detected spacer type ('2PC LUG', '2PC STUD', …).
            center_bore_mm:           Spacer centre bore in mm (from title).
            counter_bore_diameter_mm: Step/shelf bore in mm (result.counter_bore_diameter).
            hub_diameter_mm:          Hub OD in mm (result.hub_diameter).

        Returns:
            (errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not spacer_type:
            return errors, warnings

        stype_upper = spacer_type.upper()

        # Only applies to 2PC programs
        if '2PC' not in stype_upper:
            return errors, warnings

        # UNSURE classification is too ambiguous to validate reliably
        if 'UNSURE' in stype_upper:
            return errors, warnings

        is_lug = 'LUG' in stype_upper

        # Need CB to look up the expected ring
        if not center_bore_mm:
            return errors, warnings

        cb_mm = float(center_bore_mm)
        cb_in = cb_mm / 25.4

        # Find the lookup entry for this CB
        entry = None
        for cb_min, cb_max, ring_ods, desc in TWOPC_RING_TABLE:
            if cb_min <= cb_mm < cb_max:
                entry = (ring_ods, desc)
                break

        if entry is None:
            # CB not covered by the lookup — skip (handles gap zones too)
            return errors, warnings

        ring_ods_in, desc = entry
        max_ring_in = max(ring_ods_in)

        # ── Plausibility filter ────────────────────────────────────────────────
        def _is_plausible(val_in: float) -> bool:
            """True when val_in could represent a ring OD for this CB class."""
            # Ring must meaningfully exceed the centre bore
            if val_in < cb_in + _MIN_RING_EXCESS_IN:
                return False
            # Must not be so large it is clearly an outer-hub dimension
            if val_in > max_ring_in + _OUTER_HUB_MARGIN_IN:
                return False
            return True

        # ── Choose the best available ring dimension ───────────────────────────
        ring_val_mm: Optional[float] = None
        ring_field: str = ""

        if counter_bore_diameter_mm is not None:
            cbd_in = float(counter_bore_diameter_mm) / 25.4
            if _is_plausible(cbd_in):
                ring_val_mm = float(counter_bore_diameter_mm)
                ring_field = "counter-bore diameter"

        # For LUG parts, only counter_bore_diameter is reliable.
        # hub_diameter on LUG programs often captures an inner bore, not the ring.
        if ring_val_mm is None and not is_lug and hub_diameter_mm is not None:
            hub_in = float(hub_diameter_mm) / 25.4
            if _is_plausible(hub_in):
                ring_val_mm = float(hub_diameter_mm)
                ring_field = "hub diameter"

        if ring_val_mm is None:
            # No plausible ring dimension found — cannot validate
            return errors, warnings

        ring_in = ring_val_mm / 25.4

        # ── Compare against expected ring ODs ─────────────────────────────────
        closest_ring = min(ring_ods_in, key=lambda r: abs(ring_in - r))
        min_diff = abs(ring_in - closest_ring)

        if min_diff <= _TOLERANCE_IN:
            return errors, warnings  # Within spec

        # Build human-readable expected string
        ring_ods_str = " or ".join(f'{r:.3f}"' for r in ring_ods_in)

        warnings.append(
            f"2PC ring size mismatch: {ring_field} "
            f"{ring_in:.4f}\" ({ring_val_mm:.1f} mm) "
            f"does not match the expected ring OD for a {desc} spacer "
            f"(CB={cb_mm:.1f}mm). "
            f"Expected: {ring_ods_str}. "
            f"Nearest expected: {closest_ring:.3f}\" "
            f"(off by {min_diff:.4f}\"). "
            f"Verify ring selection."
        )

        return errors, warnings
