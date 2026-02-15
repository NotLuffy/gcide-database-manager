"""
G-Code Diff Engine
Provides advanced comparison and highlighting for G-code files.

Part of Phase 3: Version History & Archive Improvements
"""

import difflib
import tkinter as tk
from typing import List, Tuple, Dict, Optional


class GCodeDiffEngine:
    """Engine for comparing G-code files and highlighting differences"""

    @staticmethod
    def diff_lines(content1: str, content2: str) -> List[Tuple]:
        """
        Perform line-by-line diff using Python's difflib.

        Args:
            content1: First file content as string
            content2: Second file content as string

        Returns:
            List of opcodes from SequenceMatcher:
            Each tuple is (tag, i1, i2, j1, j2) where:
            - tag: 'replace', 'delete', 'insert', or 'equal'
            - i1, i2: Range in first sequence
            - j1, j2: Range in second sequence
        """
        lines1 = content1.splitlines(keepends=True)
        lines2 = content2.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        return matcher.get_opcodes()

    @staticmethod
    def highlight_changes(text_widget1: tk.Text, text_widget2: tk.Text,
                         content1: str, content2: str) -> Dict[str, int]:
        """
        Apply color highlighting to differences in two text widgets.

        Args:
            text_widget1: First text widget (left/old version)
            text_widget2: Second text widget (right/new version)
            content1: Content for first widget
            content2: Content for second widget

        Returns:
            Dictionary with statistics:
            - additions: Number of added lines
            - deletions: Number of deleted lines
            - changes: Number of changed lines
            - equal: Number of unchanged lines
        """
        # Configure tags for highlighting
        text_widget1.tag_configure("added", background="#1b5e20", foreground="#a5d6a7")
        text_widget1.tag_configure("deleted", background="#7f0000", foreground="#ef9a9a")
        text_widget1.tag_configure("changed", background="#5a3a00", foreground="#ffcc80")
        text_widget1.tag_configure("equal", background="#2b2b2b", foreground="#ffffff")

        text_widget2.tag_configure("added", background="#1b5e20", foreground="#a5d6a7")
        text_widget2.tag_configure("deleted", background="#7f0000", foreground="#ef9a9a")
        text_widget2.tag_configure("changed", background="#5a3a00", foreground="#ffcc80")
        text_widget2.tag_configure("equal", background="#2b2b2b", foreground="#ffffff")

        # Clear widgets
        text_widget1.delete('1.0', tk.END)
        text_widget2.delete('1.0', tk.END)

        # Get opcodes
        opcodes = GCodeDiffEngine.diff_lines(content1, content2)
        lines1 = content1.splitlines(keepends=True)
        lines2 = content2.splitlines(keepends=True)

        # Statistics
        stats = {
            'additions': 0,
            'deletions': 0,
            'changes': 0,
            'equal': 0
        }

        # Process each opcode
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                # Lines are the same
                for line in lines1[i1:i2]:
                    text_widget1.insert(tk.END, line, "equal")
                for line in lines2[j1:j2]:
                    text_widget2.insert(tk.END, line, "equal")
                stats['equal'] += (i2 - i1)

            elif tag == 'replace':
                # Lines were changed
                for line in lines1[i1:i2]:
                    text_widget1.insert(tk.END, line, "changed")
                for line in lines2[j1:j2]:
                    text_widget2.insert(tk.END, line, "changed")
                stats['changes'] += max(i2 - i1, j2 - j1)

            elif tag == 'delete':
                # Lines were deleted
                for line in lines1[i1:i2]:
                    text_widget1.insert(tk.END, line, "deleted")
                # Add blank lines to widget2 for alignment
                for _ in range(i2 - i1):
                    text_widget2.insert(tk.END, "\n", "equal")
                stats['deletions'] += (i2 - i1)

            elif tag == 'insert':
                # Lines were added
                # Add blank lines to widget1 for alignment
                for _ in range(j2 - j1):
                    text_widget1.insert(tk.END, "\n", "equal")
                for line in lines2[j1:j2]:
                    text_widget2.insert(tk.END, line, "added")
                stats['additions'] += (j2 - j1)

        return stats

    @staticmethod
    def get_diff_stats(content1: str, content2: str) -> Dict[str, int]:
        """
        Get statistics about differences without rendering.

        Args:
            content1: First file content
            content2: Second file content

        Returns:
            Dictionary with additions, deletions, changes, equal counts
        """
        opcodes = GCodeDiffEngine.diff_lines(content1, content2)

        stats = {
            'additions': 0,
            'deletions': 0,
            'changes': 0,
            'equal': 0
        }

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                stats['equal'] += (i2 - i1)
            elif tag == 'replace':
                stats['changes'] += max(i2 - i1, j2 - j1)
            elif tag == 'delete':
                stats['deletions'] += (i2 - i1)
            elif tag == 'insert':
                stats['additions'] += (j2 - j1)

        return stats


class DimensionExtractor:
    """Utility for comparing dimensions between versions"""

    @staticmethod
    def compare_dimensions(dims1: Dict[str, Optional[float]],
                          dims2: Dict[str, Optional[float]]) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
        """
        Compare dimensions between two versions.

        Args:
            dims1: First version dimensions (keys: outer_diameter, thickness, center_bore)
            dims2: Second version dimensions

        Returns:
            Dictionary of changed dimensions with (old_value, new_value) tuples
        """
        changes = {}

        # Get all unique keys
        all_keys = set(dims1.keys()) | set(dims2.keys())

        for key in all_keys:
            val1 = dims1.get(key)
            val2 = dims2.get(key)

            # Compare values (handle None values and floating point precision)
            if val1 is None and val2 is None:
                continue  # Both None, no change

            if val1 is None or val2 is None:
                # One is None, the other isn't - that's a change
                changes[key] = (val1, val2)
            elif abs(val1 - val2) > 0.0001:  # Use epsilon for float comparison
                # Values differ beyond floating point precision
                changes[key] = (val1, val2)

        return changes

    @staticmethod
    def format_dimension_change(key: str, old_value: Optional[float],
                               new_value: Optional[float]) -> str:
        """
        Format a dimension change for display.

        Args:
            key: Dimension key (e.g., 'outer_diameter')
            old_value: Old dimension value
            new_value: New dimension value

        Returns:
            Formatted string describing the change
        """
        # Format key as readable name
        key_names = {
            'outer_diameter': 'Outer Diameter',
            'thickness': 'Thickness',
            'center_bore': 'Center Bore',
            'hub_height': 'Hub Height',
            'hub_diameter': 'Hub Diameter',
            'counter_bore_diameter': 'Counter Bore Diameter',
            'counter_bore_depth': 'Counter Bore Depth'
        }
        display_key = key_names.get(key, key.replace('_', ' ').title())

        # Format values
        def format_val(v):
            if v is None:
                return "None"
            return f"{v:.4f}".rstrip('0').rstrip('.')

        old_str = format_val(old_value)
        new_str = format_val(new_value)

        # Determine change direction
        if old_value is None:
            change_type = "Added"
            return f"{display_key}: {change_type} → {new_str}\""
        elif new_value is None:
            change_type = "Removed"
            return f"{display_key}: {old_str}\" → {change_type}"
        elif new_value > old_value:
            change_type = "Increased"
            delta = new_value - old_value
            return f"{display_key}: {old_str}\" → {new_str}\" ({change_type} by {format_val(delta)}\")"
        elif new_value < old_value:
            change_type = "Decreased"
            delta = old_value - new_value
            return f"{display_key}: {old_str}\" → {new_str}\" ({change_type} by {format_val(delta)}\")"
        else:
            return f"{display_key}: {old_str}\" (No change)"

    @staticmethod
    def has_dimensional_changes(dims1: Dict[str, Optional[float]],
                               dims2: Dict[str, Optional[float]]) -> bool:
        """
        Check if there are any dimensional changes.

        Args:
            dims1: First version dimensions
            dims2: Second version dimensions

        Returns:
            True if dimensions changed, False otherwise
        """
        changes = DimensionExtractor.compare_dimensions(dims1, dims2)
        return len(changes) > 0
