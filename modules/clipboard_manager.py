"""
Clipboard management for G-code Database Manager
Provides easy copy/paste operations using pyperclip
"""

import pyperclip
from typing import Dict, List, Any, Optional


class ClipboardManager:
    """Manages clipboard operations for the application"""

    @staticmethod
    def copy_text(text: str) -> bool:
        """
        Copy plain text to clipboard

        Args:
            text: Text to copy

        Returns:
            True if successful, False otherwise
        """
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"Clipboard copy error: {e}")
            return False

    @staticmethod
    def paste_text() -> Optional[str]:
        """
        Get text from clipboard

        Returns:
            Clipboard text or None if error
        """
        try:
            return pyperclip.paste()
        except Exception as e:
            print(f"Clipboard paste error: {e}")
            return None

    @staticmethod
    def copy_program_number(program_number: str) -> bool:
        """
        Copy program number to clipboard

        Args:
            program_number: Program number (e.g., "o13002")

        Returns:
            True if successful
        """
        return ClipboardManager.copy_text(program_number)

    @staticmethod
    def copy_file_path(file_path: str) -> bool:
        """
        Copy file path to clipboard

        Args:
            file_path: Full file path

        Returns:
            True if successful
        """
        return ClipboardManager.copy_text(file_path)

    @staticmethod
    def copy_program_details(program_data: Dict[str, Any],
                           format: str = "text") -> bool:
        """
        Copy formatted program details to clipboard

        Args:
            program_data: Dictionary containing program data
            format: Output format ("text", "tsv", or "json")

        Returns:
            True if successful
        """
        try:
            if format == "text":
                text = ClipboardManager._format_as_text(program_data)
            elif format == "tsv":
                text = ClipboardManager._format_as_tsv(program_data)
            elif format == "json":
                import json
                text = json.dumps(program_data, indent=2)
            else:
                return False

            return ClipboardManager.copy_text(text)

        except Exception as e:
            print(f"Format error: {e}")
            return False

    @staticmethod
    def copy_validation_issues(issues: List[str]) -> bool:
        """
        Copy validation issues to clipboard

        Args:
            issues: List of validation issue strings

        Returns:
            True if successful
        """
        if not issues:
            return ClipboardManager.copy_text("No validation issues")

        text = "Validation Issues:\n"
        text += "\n".join(f"  • {issue}" for issue in issues)
        return ClipboardManager.copy_text(text)

    @staticmethod
    def copy_table_data(rows: List[Dict[str, Any]],
                       columns: List[str]) -> bool:
        """
        Copy table data as tab-separated values (Excel-compatible)

        Args:
            rows: List of row dictionaries
            columns: List of column names to include

        Returns:
            True if successful
        """
        try:
            # Header row
            text = "\t".join(columns) + "\n"

            # Data rows
            for row in rows:
                values = [str(row.get(col, "")) for col in columns]
                text += "\t".join(values) + "\n"

            return ClipboardManager.copy_text(text)

        except Exception as e:
            print(f"Table copy error: {e}")
            return False

    @staticmethod
    def _format_as_text(data: Dict[str, Any]) -> str:
        """Format program data as readable text"""
        lines = []
        for key, value in data.items():
            # Convert key from snake_case to Title Case
            label = key.replace('_', ' ').title()
            lines.append(f"{label}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _format_as_tsv(data: Dict[str, Any]) -> str:
        """Format program data as tab-separated values"""
        keys = "\t".join(data.keys())
        values = "\t".join(str(v) for v in data.values())
        return f"{keys}\n{values}"


def create_context_menu_handlers(clipboard_manager: ClipboardManager,
                                 get_selected_data_func):
    """
    Create context menu command handlers for clipboard operations

    Args:
        clipboard_manager: ClipboardManager instance
        get_selected_data_func: Function that returns selected row data

    Returns:
        Dictionary of menu command handlers
    """
    def copy_program_number():
        data = get_selected_data_func()
        if data and 'program_number' in data:
            clipboard_manager.copy_program_number(data['program_number'])
            return True
        return False

    def copy_file_path():
        data = get_selected_data_func()
        if data and 'file_path' in data:
            clipboard_manager.copy_file_path(data['file_path'])
            return True
        return False

    def copy_full_details():
        data = get_selected_data_func()
        if data:
            clipboard_manager.copy_program_details(data, format="text")
            return True
        return False

    def copy_validation_issues():
        data = get_selected_data_func()
        if data and 'validation_issues' in data:
            issues = data['validation_issues']
            if isinstance(issues, str):
                import json
                try:
                    issues = json.loads(issues)
                except:
                    issues = [issues]
            clipboard_manager.copy_validation_issues(issues)
            return True
        return False

    return {
        'copy_program_number': copy_program_number,
        'copy_file_path': copy_file_path,
        'copy_full_details': copy_full_details,
        'copy_validation_issues': copy_validation_issues
    }


if __name__ == "__main__":
    # Test the module
    cm = ClipboardManager()

    print("Test 1: Copy program number")
    cm.copy_program_number("o13002")
    print(f"  Copied: {cm.paste_text()}")

    print("\nTest 2: Copy program details")
    test_data = {
        'program_number': 'o13002',
        'title': '13.0 142/220MM 2.0 HC .5',
        'spacer_type': 'hub_centric',
        'outer_diameter': 13.0,
        'validation_status': 'PASS'
    }
    cm.copy_program_details(test_data, format="text")
    print("  Copied:")
    print(cm.paste_text())

    print("\nTest 3: Copy table data")
    rows = [
        {'program': 'o13002', 'status': 'PASS'},
        {'program': 'o61045', 'status': 'WARNING'}
    ]
    cm.copy_table_data(rows, ['program', 'status'])
    print("  Copied:")
    print(cm.paste_text())
