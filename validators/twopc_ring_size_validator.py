"""
2PC Mating Hub Ring Size and Recess Fit Validator

For 2-piece (2PC) spacers the ring OD used to retain the STUD insert inside
the LUG should correspond to the spacer's centre bore (CB) size.

Lookup table  — Centre Bore range → Expected Hub/Ring OD(s)
─────────────────────────────────────────────────────────────
  CB range (mm)  │  Hub OD (inches)    │  Common fitment
  53 – 61 mm     │  2.690"             │  60mm CB class
  63 – 69 mm     │  3.134"             │  63.4 / 64.1mm CB class
  73 – 83 mm     │  3.505"             │  74 / 77.8 / 78.1mm CB class
  85 – 92 mm     │  3.700" or 3.900"   │  87.1mm CB class
  99 – 116 mm    │  4.600"             │  100 – 110mm CB class

  Gaps (61–63 mm, 69–73 mm, 83–85 mm, 92–99 mm) are intentionally unvalidated
  because ring selection depends on the OD (part size) at those boundaries.

2PC LUG — Recess Fit Validation:
  The LUG step bore (counter_bore_diameter) seats the retaining ring.
  Correct clearance fit: recess bore = hub_OD + 0.003" to hub_OD + 0.005".
  Minimum recess depth: 0.300".
  hub_diameter on LUG parts typically captures an inner bore, not the ring OD,
  so it is never used for LUG recess validation.

2PC STUD — Ring Size Validation:
  counter_bore_diameter first (HC STUD inner hub bore),
  hub_diameter as fallback (hub OD ≈ ring OD for simple STUDs).
  Tolerance: ±0.25" — wide enough to allow OD-specific variants while still
  catching full ring-class errors.

2PC UNSURE — Skipped (type ambiguity makes ring ID unreliable).

A dimension is rejected as implausible (likely outer-hub or inner-bore) when:
  - it is less than CB + 0.22" (cannot be a ring surrounding that bore), OR
  - it exceeds the max expected ring + 0.30" (outer-hub OD on HC STUD).
"""

from typing import List, Optional, Tuple


# ── Lookup table ──────────────────────────────────────────────────────────────
# (cb_min_mm, cb_max_mm, hub_ods_inches, description)
# hub_ods_inches = standard hub/ring ODs for that CB class
# Ranges are half-open: cb_min <= cb < cb_max
TWOPC_RING_TABLE = [
    (53.0,  61.0, [2.690],        "60mm CB class"),
    (63.0,  69.0, [3.134],        "63.4–64.1mm CB class"),
    (73.0,  83.0, [3.505],        "74–78.1mm CB class"),
    (85.0,  92.0, [3.700, 3.900], "87.1mm CB class"),
    (99.0, 116.0, [4.600],        "100–110mm CB class"),
]

# 2PC LUG recess fit specification (diametral clearance over hub OD)
_RECESS_MIN_CLEARANCE_IN = 0.003   # recess bore must be at least this much over hub OD
_RECESS_MAX_CLEARANCE_IN = 0.005   # recess bore must not exceed hub OD by more than this

# Minimum counter-bore depth for 2PC LUG recess
_MIN_RECESS_DEPTH_IN = 0.300

# ± tolerance for STUD ring size check
# Wide enough to allow OD-specific variants; tight enough to catch cross-class errors.
_STUD_TOLERANCE_IN = 0.25

# Minimum excess over CB: ring must be > CB + this margin (plausibility filter).
_MIN_RING_EXCESS_IN = 0.22

# Maximum excess over max expected ring: above this → outer-hub OD, not ring.
_OUTER_HUB_MARGIN_IN = 0.30


class TwoPCRingSizeValidator:
    """
    Validates ring/hub OD and recess fit on 2-piece spacer programs.

    2PC LUG:
      - Checks counter-bore diameter (recess bore) is hub_OD + 0.003" to 0.005"
        (using the nearest expected hub OD for the spacer's CB class).
      - Checks counter-bore depth >= 0.300".
    2PC STUD:
      - Checks hub diameter is within ±0.25" of expected ring OD for CB class.
    2PC UNSURE:
      - Skipped entirely.

    All findings are issued as warnings (not errors).
    """

    def validate(
        self,
        spacer_type: Optional[str],
        center_bore_mm: Optional[float],
        counter_bore_diameter_mm: Optional[float],
        hub_diameter_mm: Optional[float],
        counter_bore_depth_in: Optional[float] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        Args:
            spacer_type:              Detected spacer type ('2PC LUG', '2PC STUD', …).
            center_bore_mm:           Spacer centre bore in mm (from title).
            counter_bore_diameter_mm: Step/shelf bore in mm (result.counter_bore_diameter).
            hub_diameter_mm:          Hub OD in mm (result.hub_diameter).
            counter_bore_depth_in:    Recess depth in inches (result.counter_bore_depth).

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

        # Need CB to look up the expected hub OD
        if not center_bore_mm:
            return errors, warnings

        cb_mm = float(center_bore_mm)
        cb_in = cb_mm / 25.4

        # Find the lookup entry for this CB
        entry = None
        for cb_min, cb_max, hub_ods, desc in TWOPC_RING_TABLE:
            if cb_min <= cb_mm < cb_max:
                entry = (hub_ods, desc)
                break

        if entry is None:
            # CB not covered by the lookup — skip (handles gap zones too)
            return errors, warnings

        hub_ods_in, desc = entry
        max_hub_in = max(hub_ods_in)

        # ── Plausibility filter ────────────────────────────────────────────────
        def _is_plausible(val_in: float) -> bool:
            """True when val_in could represent a ring/hub OD for this CB class."""
            # Ring must meaningfully exceed the centre bore
            if val_in < cb_in + _MIN_RING_EXCESS_IN:
                return False
            # Must not be so large it is clearly an outer-hub dimension
            if val_in > max_hub_in + _OUTER_HUB_MARGIN_IN:
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

        # ── 2PC LUG: recess bore clearance + depth ────────────────────────────
        if is_lug:
            # Depth check — independent of whether we found a ring dimension
            if counter_bore_depth_in is not None:
                depth = float(counter_bore_depth_in)
                if depth < _MIN_RECESS_DEPTH_IN:
                    warnings.append(
                        f"2PC LUG recess too shallow: counter-bore depth "
                        f"{depth:.4f}\" is less than the {_MIN_RECESS_DEPTH_IN:.3f}\" minimum. "
                        f"Verify recess depth."
                    )

            if ring_val_mm is None:
                return errors, warnings

            ring_in = ring_val_mm / 25.4

            # Nearest expected hub OD for this CB class
            nearest_hub_in = min(hub_ods_in, key=lambda r: abs(ring_in - r))
            clearance_in = ring_in - nearest_hub_in

            if clearance_in < _RECESS_MIN_CLEARANCE_IN:
                if clearance_in < 0.0:
                    warnings.append(
                        f"2PC LUG recess interference: {ring_field} "
                        f"{ring_in:.4f}\" ({ring_val_mm:.1f} mm) is smaller than "
                        f"hub OD {nearest_hub_in:.3f}\" for a {desc} spacer "
                        f"(CB={cb_mm:.1f} mm). "
                        f"Clearance = {clearance_in:+.4f}\". "
                        f"Expected +{_RECESS_MIN_CLEARANCE_IN:.3f}\" to "
                        f"+{_RECESS_MAX_CLEARANCE_IN:.3f}\". Verify recess bore."
                    )
                else:
                    warnings.append(
                        f"2PC LUG recess too tight: {ring_field} "
                        f"{ring_in:.4f}\" ({ring_val_mm:.1f} mm) gives "
                        f"{clearance_in:+.4f}\" clearance over hub OD "
                        f"{nearest_hub_in:.3f}\" for a {desc} spacer "
                        f"(CB={cb_mm:.1f} mm). "
                        f"Expected +{_RECESS_MIN_CLEARANCE_IN:.3f}\" to "
                        f"+{_RECESS_MAX_CLEARANCE_IN:.3f}\". Verify recess bore."
                    )
            elif clearance_in > _RECESS_MAX_CLEARANCE_IN:
                warnings.append(
                    f"2PC LUG recess too loose: {ring_field} "
                    f"{ring_in:.4f}\" ({ring_val_mm:.1f} mm) gives "
                    f"{clearance_in:+.4f}\" clearance over hub OD "
                    f"{nearest_hub_in:.3f}\" for a {desc} spacer "
                    f"(CB={cb_mm:.1f} mm). "
                    f"Expected +{_RECESS_MIN_CLEARANCE_IN:.3f}\" to "
                    f"+{_RECESS_MAX_CLEARANCE_IN:.3f}\". Verify ring selection."
                )
            # else: clearance within spec — no warning

            return errors, warnings

        # ── 2PC STUD: ring size validation (±0.25" tolerance) ─────────────────
        if ring_val_mm is None:
            return errors, warnings

        ring_in = ring_val_mm / 25.4
        closest_ring = min(hub_ods_in, key=lambda r: abs(ring_in - r))
        min_diff = abs(ring_in - closest_ring)

        if min_diff <= _STUD_TOLERANCE_IN:
            return errors, warnings  # Within spec

        # Build human-readable expected string
        ring_ods_str = " or ".join(f'{r:.3f}"' for r in hub_ods_in)

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
