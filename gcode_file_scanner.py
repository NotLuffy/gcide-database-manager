"""
G-Code File Scanner Module
Scans G-code files for issues without importing to database

Extracted from test_phase1/file_scanner_test.py for integration into main application
"""

from typing import Dict
from improved_gcode_parser import ImprovedGCodeParser


class FileScanner:
    """
    File scanner for G-code files - scans for issues without importing to database
    """

    def __init__(self):
        self.parser = ImprovedGCodeParser()

    def scan_file_for_issues(self, file_path: str) -> Dict:
        """
        Scan a G-code file for issues without importing

        Args:
            file_path: Path to G-code file

        Returns:
            dict with keys:
                - success: bool
                - program_number: str
                - round_size: float
                - dimensions: dict
                - warnings: list of dict
                - errors: list of dict
                - raw_data: ParseResult object
        """
        results = {
            'success': False,
            'program_number': None,
            'round_size': None,
            'dimensions': {},
            'warnings': [],
            'errors': [],
            'raw_data': None,
            'spacer_type': None,
            'title': None,
            'material': None,
            'tools_used': [],
            'pcodes_found': []
        }

        try:
            # Parse file
            parse_result = self.parser.parse_file(file_path)
            results['raw_data'] = parse_result
            results['success'] = True

            # Extract program number
            results['program_number'] = parse_result.program_number

            # Extract round size (outer diameter)
            results['round_size'] = parse_result.outer_diameter

            # Extract spacer type
            results['spacer_type'] = parse_result.spacer_type

            # Extract title
            results['title'] = parse_result.title

            # Extract material
            results['material'] = parse_result.material

            # Extract tools
            results['tools_used'] = parse_result.tools_used

            # Extract P-codes
            results['pcodes_found'] = parse_result.pcodes_found

            # Extract dimensions
            results['dimensions'] = {
                'outer_diameter': parse_result.outer_diameter,
                'thickness': parse_result.thickness,
                'thickness_display': parse_result.thickness_display,
                'center_bore': parse_result.center_bore,
                'hub_diameter': parse_result.hub_diameter,
                'hub_height': parse_result.hub_height,
                'counter_bore_diameter': parse_result.counter_bore_diameter,
                'counter_bore_depth': parse_result.counter_bore_depth,
            }

            # Collect warnings from various sources

            # Tool home issues
            if parse_result.tool_home_issues:
                for issue in parse_result.tool_home_issues:
                    if issue.strip():
                        results['warnings'].append({
                            'type': 'tool_home',
                            'severity': 'warning',
                            'category': 'Tool Home Position',
                            'message': issue.strip(),
                            'line_number': None
                        })

            # Bore warnings
            if parse_result.bore_warnings:
                for warning in parse_result.bore_warnings:
                    if warning.strip():
                        results['warnings'].append({
                            'type': 'bore',
                            'severity': 'warning',
                            'category': 'Bore Dimensions',
                            'message': warning.strip(),
                            'line_number': None
                        })

            # Dimensional issues
            if parse_result.dimensional_issues:
                for issue in parse_result.dimensional_issues:
                    if issue.strip():
                        results['warnings'].append({
                            'type': 'dimensional',
                            'severity': 'warning',
                            'category': 'Dimensional',
                            'message': issue.strip(),
                            'line_number': None
                        })

            # Validation warnings
            if parse_result.validation_warnings:
                for warning in parse_result.validation_warnings:
                    if warning.strip():
                        results['warnings'].append({
                            'type': 'validation',
                            'severity': 'warning',
                            'category': 'Validation',
                            'message': warning.strip(),
                            'line_number': None
                        })

            # Validation issues (errors)
            if parse_result.validation_issues:
                for issue in parse_result.validation_issues:
                    if issue.strip():
                        results['errors'].append({
                            'type': 'validation',
                            'severity': 'error',
                            'category': 'Critical',
                            'message': issue.strip(),
                            'line_number': None
                        })

            # Check for missing critical dimensions
            if parse_result.outer_diameter is None:
                results['warnings'].append({
                    'type': 'dimensional',
                    'severity': 'info',
                    'category': 'Missing Data',
                    'message': 'Outer diameter not detected',
                    'line_number': None
                })

            if parse_result.thickness is None:
                results['warnings'].append({
                    'type': 'dimensional',
                    'severity': 'info',
                    'category': 'Missing Data',
                    'message': 'Thickness not detected',
                    'line_number': None
                })

            if parse_result.center_bore is None:
                results['warnings'].append({
                    'type': 'dimensional',
                    'severity': 'info',
                    'category': 'Missing Data',
                    'message': 'Center bore not detected',
                    'line_number': None
                })

        except Exception as e:
            results['errors'].append({
                'type': 'parse_error',
                'severity': 'error',
                'category': 'Parse Error',
                'message': f"Failed to parse file: {str(e)}",
                'line_number': None
            })

        return results
