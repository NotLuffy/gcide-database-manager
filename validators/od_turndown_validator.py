"""
OD Turn-Down Validator
======================
Validates that T303 OD turn-down X values match common-practice standards.

The OD turn-down X is the modal X at the moment the tool executes a
"G01 Z-<depth>" cut that turns down the side of the part.

That modal X can be established in several ways (no single standard flow):

  Pattern A - G01 face pass immediately before Z-down (simple / standard):
    G00 G154 P27 x5.7 Z1.      <- G00 sets modal X=5.7
    G01 x5.7 Z0. F0.015        <- face pass: modal X still 5.7
    G01 Z-1.3 F0.015           <- Z-down at X5.7  (o57504 lines 47-48)

  Pattern B - Chamfer lead-in to OD X, then Z-down (HC / standard):
    X9.42
    G01 x9.478 Z-0.05 F0.008  <- chamfer sets modal X=9.478
    G01 Z-1.9 F0.012           <- Z-down at X9.478  (o09906 line 60-61)

  Pattern C - G00 positioning sets X, no G01 X before Z-down:
    G00 G154 P11 x9.45 Z1.    <- G00 sets modal X=9.45
    G00 Z0.1
    G01 Z-1.1 F0.012           <- Z-down at X9.45  (o09501 lines 57-61)

Hub-face guard (OP2 HC parts):
  In OP2 of HC programs, the tool plunges incrementally to face the hub
  (G01 Z-0.2, Z-0.4, Z-0.9, ...) at OD modal X, but each plunge is
  followed by a large inward X move (to OB territory, > 1.5" inward).
  We scan backward for such an inward X to suppress false OD-turn flags.
"""

import re
from typing import Dict, List, Optional, Tuple


class ODTurnDownValidator:
    """Validates OD turn-down X values against common-practice standards."""

    STANDARD_OD_TURNDOWN: Dict[float, float] = {
        5.75:  5.700,
        6.00:  5.950,
        6.25:  6.200,
        6.50:  6.450,
        7.00:  6.945,
        7.50:  7.445,
        8.00:  7.945,
        8.50:  8.440,
        9.50:  9.450,
        10.25: 10.170,
        10.50: 10.450,
        13.00: 12.904,
    }

    _INWARD_THRESHOLD = 1.5   # X must move this far inward to signal "hub face"
    _LOOKBACK         = 20    # lines scanned backward for hub-face guard
    _MIN_Z_AB         = 0.10  # min Z depth for Patterns A/B
    _MIN_Z_C          = 0.30  # min Z depth for Pattern C (avoids shallow hub-face plunges)

    def __init__(self):
        self.tolerance = 0.01   # ±0.01" tolerance when comparing to standard

    # ── public API ────────────────────────────────────────────────────────────

    def validate_file(self, lines: List[str], round_size: Optional[float]) -> Tuple[List[str], List[str]]:
        """
        Validate OD turn-down X values in T303 blocks.

        Returns:
            (warnings, notes)
        """
        if not round_size or round_size not in self.STANDARD_OD_TURNDOWN:
            return [], []

        standard_od = self.STANDARD_OD_TURNDOWN[round_size]
        warnings: List[str] = []
        notes:    List[str] = []
        state = {'in_t3': False, 'side': 1, 'modal_x': None, 'x_by_g01': False}

        for i, line in enumerate(lines):
            line_upper = line.upper()
            # Side detection runs on every line (FLIP PART is often comment-only)
            state['side'] = self._update_side(state['side'], line_upper, i)
            code_part = line.split('(')[0].upper().strip()
            if not code_part or code_part.startswith('%'):
                continue
            if self._update_tool_state(state, code_part):
                continue
            xm = re.search(r'X\s*([\d.]+)', code_part)
            if xm:
                state['modal_x']  = float(xm.group(1))
                state['x_by_g01'] = 'G01' in code_part
            if state['in_t3']:
                self._process_g01(lines, i, code_part, bool(xm), state,
                                  round_size, standard_od, warnings, notes)

        return warnings, notes

    def get_standard_od(self, round_size: float) -> Optional[float]:
        """Return the standard OD turn-down X for a given round size."""
        return self.STANDARD_OD_TURNDOWN.get(round_size)

    # ── per-line processing ───────────────────────────────────────────────────

    def _process_g01(self, lines, i, code_part, has_x, state,
                     round_size, standard_od, warnings, notes):
        """Entry point for G01 lines inside a T303 block."""
        if 'G01' not in code_part:
            return
        if has_x:
            # Pattern A/B: G01 with X on this line; look ahead for G01 Z-<depth>
            self._check_pattern_ab(lines, i, state['modal_x'],
                                   standard_od, round_size, state['side'], warnings, notes)
        else:
            # Pattern C: G01 with only Z-<depth> on this line; X set earlier via G00
            zm = re.search(r'Z\s*(-\d+\.?\d*)', code_part)
            if zm:
                self._check_pattern_c(lines, i, state['modal_x'], state['x_by_g01'],
                                      abs(float(zm.group(1))),
                                      standard_od, round_size, state['side'], warnings, notes)

    # ── pattern detectors ─────────────────────────────────────────────────────

    def _check_pattern_ab(self, lines, i, modal_x,
                          standard_od, round_size, side, warnings, notes):
        """Pattern A/B: current G01 has X; next real line is G01 Z-<depth>."""
        if modal_x is None or modal_x < standard_od - 1.0:
            return
        nxt = self._next_real_line(lines, i + 1)
        if nxt is None or 'G01' not in nxt:
            return
        nzm = re.search(r'Z\s*(-\d+\.?\d*)', nxt)
        if nzm and abs(float(nzm.group(1))) >= self._MIN_Z_AB:
            self._emit_result(modal_x, i, side, round_size, standard_od, warnings, notes)

    def _check_pattern_c(self, lines, i, modal_x, x_by_g01, z_depth,
                         standard_od, round_size, side, warnings, notes):
        """Pattern C: current G01 has only Z; modal X was set earlier via G00."""
        if modal_x is None or x_by_g01:
            return
        if z_depth < self._MIN_Z_C or modal_x < standard_od - 1.0:
            return
        if not self._has_recent_inward_x(lines, i, modal_x):
            self._emit_result(modal_x, i, side, round_size, standard_od, warnings, notes)

    # ── state helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _update_tool_state(state: dict, code_part: str) -> bool:
        """Update in_t3 / modal_x on tool-change and G53 lines. Returns True to skip line."""
        if re.match(r'T\d+', code_part):
            state['in_t3']    = code_part.startswith('T3')
            state['modal_x']  = None
            state['x_by_g01'] = False
            return True
        if 'G53' in code_part:
            state['in_t3']    = False
            state['modal_x']  = None
            state['x_by_g01'] = False
            return True
        return False

    @staticmethod
    def _update_side(side: int, line_upper: str, i: int) -> int:
        if 'FLIP PART' in line_upper or 'SIDE 2' in line_upper:
            return 2
        if i < 100 and 'SIDE 1' in line_upper:
            return 1
        return side

    # ── output helpers ────────────────────────────────────────────────────────

    def _emit_result(self, x_value, i, side, round_size, standard_od, warnings, notes):
        """Append note (match) or warning (deviation) for the detected OD turn X."""
        side_str = f"Side {side}"
        if abs(x_value - standard_od) <= self.tolerance:
            notes.append(
                f"{side_str}: OD turn-down X{x_value:.3f}\" matches standard (X{standard_od:.3f}\")"
            )
            return
        other = next(
            (sz for sz, od in self.STANDARD_OD_TURNDOWN.items()
             if sz != round_size and abs(x_value - od) <= self.tolerance),
            None
        )
        if other:
            warnings.append(
                f"OUT OF COMMON PRACTICE - {side_str}: OD turn-down X{x_value:.3f}\" "
                f"does not match standard X{standard_od:.3f}\" for {round_size:.2f}\" rounds "
                f"- matches {other:.2f}\" round standard instead (Line {i + 1})"
            )
        else:
            warnings.append(
                f"OUT OF COMMON PRACTICE - {side_str}: OD turn-down X{x_value:.3f}\" "
                f"does not match standard X{standard_od:.3f}\" for {round_size:.2f}\" rounds "
                f"(Line {i + 1})"
            )

    # ── scan helpers ──────────────────────────────────────────────────────────

    def _has_recent_inward_x(self, lines: List[str], i: int, modal_x: float) -> bool:
        """Return True if a recent X line moved > _INWARD_THRESHOLD inward from modal_x."""
        for j in range(i - 1, max(0, i - self._LOOKBACK) - 1, -1):
            prev = lines[j].split('(')[0].upper().strip()
            if not prev or prev.startswith('%'):
                continue
            if re.match(r'T\d+', prev):
                break
            xm = re.search(r'X\s*([\d.]+)', prev)
            if xm and (modal_x - float(xm.group(1))) > self._INWARD_THRESHOLD:
                return True
        return False

    @staticmethod
    def _next_real_line(lines: List[str], start: int) -> Optional[str]:
        """Return code part of the first non-empty line at or after start."""
        for j in range(start, min(start + 3, len(lines))):
            code = lines[j].split('(')[0].upper().strip()
            if code and not code.startswith('%'):
                return code
        return None
