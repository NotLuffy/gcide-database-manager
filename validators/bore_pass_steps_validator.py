"""
Bore Pass Steps Validator
=========================
Detects T121 BORE operations where:

1. Consecutive pass X steps exceed 0.300" (diameter).
   An over-large step removes too much material in a single pass
   and risks deflection, tool breakage, or poor bore finish.

   Standard rule: max 0.300" diameter step between consecutive bore passes.
   Most common violation: 0.600" step (every other intermediate pass skipped).

2. First bore approach X is >= 2.400".
   After drilling, the bore tool must enter the pre-drilled hole safely.
   The first bore pass should start at X2.300 or less to avoid crashing
   into undrilled material at the bore entry.

Applies to:
- T121 BORE sections only (NOT T121 CHAMFER BORE / CHAMPHER)
- Passes to Z depth > 0.200" below surface
- Two-piece and single-op programs

Example step violation (o81267-style):
    X2.300  Z-1.400  (pass 1)
    X2.900  Z-1.400  (pass 2 — step 0.600" -> exceeds 0.300" max)
    X3.500  Z-1.400  (pass 3 — step 0.600" -> exceeds 0.300" max)
    Fix: add X2.600 between each pair

Example first-X violation:
    G00 X2.500 Z1.    (approach at X2.500 -- already past X2.300 limit)
    G01 Z-1.400       (first bore pass at X2.500 -- FLAGGED)
    Fix: start at X2.300 or less and work outward
"""

import re
from typing import List, Tuple, Optional


class BorePassStepsValidator:
    """Validates T121 bore pass X step increments and bore entry position."""

    MAX_STEP        = 0.300   # Maximum diameter step between bore passes
    MIN_DEPTH       = 0.200   # Minimum Z depth (below surface) to count as a bore pass
    STEP_TOL        = 0.005   # Tolerance: 0.305" is acceptable (CB rounding, etc.)
    MAX_FIRST_X     = 2.300   # First bore pass must start at or below this X diameter

    # Compiled patterns (module-level for performance)
    _T_COMMENT = re.compile(r'^T\d+\s*\(([^)]*)\)', re.IGNORECASE)
    _G_CODE    = re.compile(r'\bG0*([0-3])\b', re.IGNORECASE)   # G00-G03
    _Z_VAL     = re.compile(r'Z(-?\d+\.?\d*)', re.IGNORECASE)
    _X_VAL     = re.compile(r'X(\d+\.?\d*)', re.IGNORECASE)
    _P_VAL     = re.compile(r'G154\s*P(\d+)', re.IGNORECASE)

    def validate_file(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        """
        Scan all lines for bore pass step violations and bad first-pass X.

        Returns:
            (warnings, notes) — lists of human-readable strings.
            warnings: bore violations (step too large, or first X too large)
            notes:    informational (currently unused)
        """
        warnings: List[str] = []
        notes:    List[str] = []

        in_bore    = False  # True while inside a T121 BORE (non-chamfer) block
        active_g   = None   # Current modal G code (0=rapid, 1=feed, 2/3=arc)
        current_x  = None   # Most recent bore X diameter position
        x_from_g01 = False  # True when current_x was set by a G01 X move (angled cut)
        bore_passes: List[Tuple[int, float]] = []
        side       = 1      # 1 or 2 (determined from P-code parity)

        def _flush(passes: List[Tuple[int, float]]) -> None:
            """Check accumulated passes for first-X and outward step violations."""
            if not passes:
                return

            # ── Rule 1: first bore pass must start at X2.300 or less ──────────
            first_ln, first_x = passes[0]
            if first_x > self.MAX_FIRST_X + self.STEP_TOL:
                warnings.append(
                    f"Side {side} Line {first_ln}: First bore pass at X{first_x:.3f} "
                    f"-- bore approach should start at X{self.MAX_FIRST_X:.3f} or less "
                    f"(too aggressive entry, risk of crashing into undrilled material)"
                )

            # ── Rule 2: consecutive outward steps must not exceed MAX_STEP ────
            for i in range(1, len(passes)):
                _, prev_x = passes[i - 1]
                curr_ln, curr_x = passes[i]
                # Only flag outward steps (boring to larger diameter).
                # Inward steps are cleanup/return passes -- never aggressive.
                if curr_x <= prev_x:
                    continue
                step = curr_x - prev_x
                if step > self.MAX_STEP + self.STEP_TOL:
                    mid_x = round((prev_x + curr_x) / 2, 4)
                    warnings.append(
                        f"Side {side} Line {curr_ln}: Bore pass step {step:.3f}\" "
                        f"(X{prev_x:.3f}->X{curr_x:.3f}) exceeds {self.MAX_STEP:.3f}\" max "
                        f"-- add intermediate pass at X{mid_x:.3f}"
                    )

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()

            if not stripped or stripped.startswith('%') or stripped.startswith('('):
                continue

            code_part  = stripped.split('(')[0].strip()
            code_upper = code_part.upper()

            # ── tool-comment line starts a new block ──────────────────────────
            tm = self._T_COMMENT.match(stripped)
            if tm:
                if in_bore:
                    _flush(bore_passes)
                bore_passes = []
                current_x   = None
                active_g    = None
                x_from_g01  = False

                comment = tm.group(1).upper()
                # T121 BORE = bore tool, and comment does NOT say CHAMFER/CHAMPHER
                is_t121 = 'T121' in code_upper or stripped.upper().startswith('T121')
                in_bore = (
                    is_t121
                    and 'BORE' in comment
                    and 'CHAMFER' not in comment
                    and 'CHAMPHER' not in comment
                )
                continue

            # ── G53 (tool home) ends the current block ────────────────────────
            if 'G53' in code_upper:
                if in_bore:
                    _flush(bore_passes)
                bore_passes = []
                current_x   = None
                active_g    = None
                x_from_g01  = False
                in_bore     = False
                continue

            # ── track side from G154 P-code parity (odd=side1, even=side2) ───
            pm = self._P_VAL.search(code_part)
            if pm:
                p = int(pm.group(1))
                side = 1 if p % 2 == 1 else 2

            # ── update modal G code ───────────────────────────────────────────
            gm = self._G_CODE.search(code_part)
            if gm:
                active_g = int(gm.group(1))

            if not in_bore:
                continue

            # ── within a T121 BORE block ──────────────────────────────────────
            x_m = self._X_VAL.search(code_part)
            z_m = self._Z_VAL.search(code_part)

            x_present = bool(x_m)
            z_present = bool(z_m)

            z_val = float(z_m.group(1)) if z_m else None
            x_val = float(x_m.group(1)) if x_m else None

            # ── update current bore X position ────────────────────────────────
            # G00 rapids and standalone X lines set a new bore position (x_from_g01=False).
            # G01 X lines are angled/chamfer cuts -- they move the tool to a new X but
            # the following Z-only G01 passes are chamfer cleanup, not bore depth passes
            # (x_from_g01=True suppresses recording).
            is_explicit_g00 = 'G00' in code_upper
            is_standalone_x = x_present and not gm   # no G code word on this line

            if x_present:
                if is_explicit_g00:
                    if not z_present or (z_val is not None and z_val >= 0):
                        current_x  = x_val
                        x_from_g01 = False
                elif is_standalone_x:
                    current_x  = x_val
                    x_from_g01 = False
                elif 'G01' in code_upper or active_g == 1:
                    # Chamfer/angled G01 -- track position but mark as chamfer-derived
                    current_x  = x_val
                    x_from_g01 = True

            # ── detect bore pass: G01 (explicit or modal) with only Z, deep pass ─
            if z_present and not x_present:
                is_g01_explicit = 'G01' in code_upper
                is_g01_modal    = (active_g == 1) and not gm
                is_feed_pass    = is_g01_explicit or is_g01_modal

                if (is_feed_pass and z_val is not None
                        and z_val < -self.MIN_DEPTH
                        and current_x is not None
                        and not x_from_g01):
                    bore_passes.append((line_num, current_x))

        # Final flush in case file ends without G53
        if in_bore:
            _flush(bore_passes)

        return warnings, notes
