"""
G-Code Generator V2.0
Generates G-code for wheel spacers on Haas lathes.

Supports:
- Standard Wheel Spacers
- Hub-Centric Wheel Spacers
- Thin-Lip Hub-Centric Spacers
- STEP Spacers
- Steel Ring Spacers
- 2-Piece Interlocking Spacers

Uses hybrid approach: templates when available, rules as fallback.
"""

__version__ = "2.0.0"
__author__ = "Bronson Generators"

from .generator import GCodeGenerator

__all__ = ['GCodeGenerator']
