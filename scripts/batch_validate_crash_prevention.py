"""
Batch Validate Crash Prevention
Re-validates all programs in the database with the crash prevention system.

This script:
1. Loads all programs from database
2. Re-parses each G-code file with crash detection
3. Updates database with crash validation results
4. Shows progress and statistics
"""

import sqlite3
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
from improved_gcode_parser import ImprovedGCodeParser


class BatchCrashValidator:
    """Batch validate all programs with crash prevention"""

    def __init__(self, db_path: str, repository_path: str):
        """
        Initialize batch validator.

        Args:
            db_path: Path to database
            repository_path: Path to repository folder
        """
        self.db_path = db_path
        self.repository_path = Path(repository_path)
        self.parser = ImprovedGCodeParser()

        # Statistics
        self.total_programs = 0
        self.validated_count = 0
        self.crash_risk_count = 0
        self.crash_warning_count = 0
        self.pass_count = 0
        self.error_count = 0

    def get_all_programs(self) -> List[Tuple]:
        """
        Get all programs from database.

        Returns:
            List of (program_number, file_path) tuples
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT program_number, file_path
            FROM programs
            WHERE file_path IS NOT NULL
              AND program_number IS NOT NULL
            ORDER BY program_number
        """)

        programs = cursor.fetchall()
        conn.close()

        return programs

    def validate_program(self, program_number: str, file_path: str) -> Dict:
        """
        Validate single program with crash detection.

        Args:
            program_number: Program number (e.g., 'O70500')
            file_path: Path to G-code file

        Returns:
            Dictionary with crash validation results
        """
        # Check if file exists
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File not found',
                'crash_issues': [],
                'crash_warnings': []
            }

        try:
            # Parse file with crash detection
            result = self.parser.parse_file(file_path)

            # Compute validation status based on issues
            # Priority: CRASH_RISK > CRITICAL > BORE_WARNING > WARNING > PASS
            validation_status = 'PASS'

            if result.crash_issues:
                validation_status = 'CRASH_RISK'
            elif result.validation_issues:
                validation_status = 'CRITICAL'
            elif result.bore_warnings:
                validation_status = 'BORE_WARNING'
            elif result.validation_warnings or result.crash_warnings:
                validation_status = 'WARNING'

            return {
                'success': True,
                'crash_issues': result.crash_issues or [],
                'crash_warnings': result.crash_warnings or [],
                'validation_status': validation_status,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'crash_issues': [],
                'crash_warnings': []
            }

    def update_database(self, program_number: str, validation_result: Dict):
        """
        Update database with crash validation results.

        Args:
            program_number: Program number
            validation_result: Validation results dictionary
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            # Serialize lists to JSON
            crash_issues_json = json.dumps(validation_result['crash_issues']) if validation_result['crash_issues'] else None
            crash_warnings_json = json.dumps(validation_result['crash_warnings']) if validation_result['crash_warnings'] else None

            # Update crash fields
            cursor.execute("""
                UPDATE programs
                SET crash_issues = ?,
                    crash_warnings = ?,
                    validation_status = ?
                WHERE program_number = ?
            """, (
                crash_issues_json,
                crash_warnings_json,
                validation_result.get('validation_status', 'UNKNOWN'),
                program_number
            ))

            conn.commit()

        except Exception as e:
            print(f"  ERROR updating database for {program_number}: {e}")
            conn.rollback()

        finally:
            conn.close()

    def run_batch_validation(self, limit: int = None):
        """
        Run batch validation on all programs.

        Args:
            limit: Optional limit on number of programs to validate (for testing)
        """
        print("="*70)
        print("  BATCH CRASH PREVENTION VALIDATION")
        print("="*70)

        # Get all programs
        programs = self.get_all_programs()
        self.total_programs = len(programs)

        if limit:
            programs = programs[:limit]
            print(f"\nValidating first {len(programs)} programs (limit applied)...")
        else:
            print(f"\nValidating all {len(programs)} programs...")

        print("\nProgress:")
        print("-"*70)

        # Validate each program
        for i, (program_number, file_path) in enumerate(programs, 1):
            # Progress indicator
            if i % 100 == 0:
                print(f"  {i}/{len(programs)} programs validated...")

            # Validate
            result = self.validate_program(program_number, file_path)

            if result['success']:
                # Update database
                self.update_database(program_number, result)
                self.validated_count += 1

                # Track statistics
                if result['crash_issues']:
                    self.crash_risk_count += 1
                elif result['crash_warnings']:
                    self.crash_warning_count += 1
                else:
                    self.pass_count += 1

            else:
                self.error_count += 1
                # Print first 5 errors to help diagnose issues
                if self.error_count <= 5:
                    print(f"  ERROR: {program_number} - {result['error']}")

        # Final progress
        print(f"  {len(programs)}/{len(programs)} programs validated...")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*70)
        print("  VALIDATION SUMMARY")
        print("="*70)
        print(f"\nTotal Programs:      {self.total_programs:,}")
        print(f"Successfully Validated: {self.validated_count:,}")
        print(f"Errors:              {self.error_count:,}")
        print()
        print("Crash Prevention Results:")
        print(f"  CRASH RISK:        {self.crash_risk_count:,} programs (have critical crash issues)")
        print(f"  WARNINGS:          {self.crash_warning_count:,} programs (have crash warnings)")
        print(f"  PASS:              {self.pass_count:,} programs (no crash issues)")
        print()

        # Calculate percentages
        if self.validated_count > 0:
            crash_pct = (self.crash_risk_count / self.validated_count) * 100
            warn_pct = (self.crash_warning_count / self.validated_count) * 100
            pass_pct = (self.pass_count / self.validated_count) * 100

            print("Percentages:")
            print(f"  CRASH RISK:        {crash_pct:.1f}%")
            print(f"  WARNINGS:          {warn_pct:.1f}%")
            print(f"  PASS:              {pass_pct:.1f}%")

        print("\n" + "="*70)
        print("Validation complete. Refresh the database manager to see results.")
        print("="*70 + "\n")


def main():
    """Main entry point"""
    import sys

    # Paths
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    repository_path = r"l:\My Drive\Home\File organizer\repository"

    # Create validator
    validator = BatchCrashValidator(db_path, repository_path)

    # Check for limit argument (for testing)
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"Limiting validation to first {limit} programs")
        except ValueError:
            print("Invalid limit argument, validating all programs")

    # Run validation
    validator.run_batch_validation(limit=limit)


if __name__ == "__main__":
    main()
