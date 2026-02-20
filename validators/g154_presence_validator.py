"""
G154 / Work Offset Presence Validator

Every tool operation must declare a work coordinate system
(G154 P#, G54, G55, or G54.1 P#) within the first 5 code lines
following the tool call.

Without an explicit work offset, the tool runs in whatever
coordinate space was last active.  If a previous operation used a
different P-code the part will be cut in the wrong location.

Real-world example: o73876.nc — T121 (BORE) lacked G154 P11.
The bore ran using the inherited P11 from the preceding drill and
happened to produce a correct part, but the omission is a latent
error that would cause a wrong cut if fixture offsets ever differ.
"""

import re
from typing import List, Tuple


class G154PresenceValidator:
    """
    Validates that every tool operation declares a work coordinate
    system (G154 P#, G54, G54.1 P#, or G55) within its first N
    code lines after the tool change.
    """

    # Number of code lines to inspect after each tool call.
    WINDOW = 5

    # Matches any work-offset command:
    #   G154 P##   G54   G54.1 P##   G55
    #
    # Fixes vs. the naive pattern:
    #   54(?:\.1)?  — makes the whole ".1" suffix optional, so plain G54 matches
    #   (?!\d)      — negative lookahead instead of trailing \b so G54X4.3 and
    #                 G154P11 are detected even without a space separator, while
    #                 G541, G5412 etc. are still correctly rejected
    WCS_PATTERN = re.compile(
        r'\bG(?:154|54(?:\.1)?|55)(?!\d)',
        re.IGNORECASE
    )

    # Matches a tool call word, e.g. T101, T303
    TOOL_PATTERN = re.compile(r'\bT\d+\b', re.IGNORECASE)

    # G53 = machine-coordinate tool home (resets active WCS context)
    G53_PATTERN = re.compile(r'\bG53\b', re.IGNORECASE)

    # Program-end codes — stop scanning after these
    END_PATTERN = re.compile(r'\bM3[03]\b', re.IGNORECASE)

    def validate_file(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        """
        Scan every tool change and verify a WCS declaration follows.

        Args:
            lines: Raw G-code file lines (1 element per line).

        Returns:
            (errors, warnings)
            - errors  : list of str — operations missing a work offset.
            - warnings: list of str — currently always empty; reserved
                        for future softer checks.
        """
        errors = []

        # Build a flat list of "code lines" — skip blanks, %-markers,
        # and pure-comment lines (e.g. "(FLIP PART)") so the WINDOW
        # count is not inflated by whitespace.
        code_lines = []
        for line_no, raw in enumerate(lines, 1):
            stripped = raw.strip()
            if not stripped or stripped.startswith('%'):
                continue
            code_part = stripped.split('(')[0].strip()
            if not code_part:          # line was only a comment
                continue
            if self.END_PATTERN.search(code_part):
                code_lines.append((line_no, code_part, raw))
                break                  # nothing useful after M30/M33
            code_lines.append((line_no, code_part, raw))

        for ci, (line_num, code, raw) in enumerate(code_lines):
            if not self.TOOL_PATTERN.search(code):
                continue

            # Build a human-readable tool label from the inline comment
            comment_match = re.search(r'\(([^)]+)\)', raw)
            tool_token = self.TOOL_PATTERN.search(code).group().upper()
            if comment_match:
                tool_label = f"{tool_token} ({comment_match.group(1).strip()})"
            else:
                tool_label = tool_token

            # Scan the next WINDOW code lines for a WCS declaration
            found_wcs = False
            for wl_num, wl_code, _ in code_lines[ci + 1: ci + 1 + self.WINDOW]:

                # A new tool call begins before we found a WCS — the
                # current operation had no offset declaration.
                if self.TOOL_PATTERN.search(wl_code):
                    break

                # G53 tool home encountered — operation ended without WCS
                if self.G53_PATTERN.search(wl_code):
                    break

                if self.WCS_PATTERN.search(wl_code):
                    found_wcs = True
                    break

            if not found_wcs:
                errors.append(
                    f"Line {line_num}: {tool_label} — no work offset "
                    f"(G154 P#, G54, or G55) found within first "
                    f"{self.WINDOW} code lines of operation. "
                    f"Tool will cut in undefined/inherited coordinate "
                    f"space — verify correct fixture offset is active."
                )

        return errors, []
