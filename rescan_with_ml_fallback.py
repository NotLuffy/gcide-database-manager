"""
Rescan Database with ML Fallback Integration

This script rescans all programs using the improved parser, then uses ML predictions
as intelligent fallbacks for any dimensions that are still missing after parsing.

Usage:
    python rescan_with_ml_fallback.py
"""

import sqlite3
import os
import sys
from pathlib import Path
from typing import Dict, Optional

# Import the improved parser
from improved_gcode_parser import ImprovedGCodeParser, GCodeParseResult

# Import ML extractor if available
try:
    from ml_dimension_extractor import MLDimensionExtractor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("WARNING: ML dimension extractor not available")
    print("Install with: pip install pandas scikit-learn numpy")


class DatabaseRescanner:
    """Rescan database with ML fallback for missing dimensions"""

    def __init__(self, db_path='gcode_database.db', gcode_base_path=None):
        self.db_path = db_path
        self.gcode_base_path = gcode_base_path or r"I:\My Drive\NC Master\REVISED PROGRAMS"
        self.parser = ImprovedGCodeParser()
        self.ml_extractor = None

        # Statistics
        self.stats = {
            'total': 0,
            'parsed_od': 0,
            'parsed_thickness': 0,
            'parsed_cb': 0,
            'ml_od': 0,
            'ml_thickness': 0,
            'ml_cb': 0,
            'still_missing_od': 0,
            'still_missing_thickness': 0,
            'still_missing_cb': 0,
        }

    def initialize_ml(self):
        """Initialize ML extractor and load/train models"""
        if not ML_AVAILABLE:
            print("\nML not available - will skip ML fallback")
            return False

        print("\n" + "="*80)
        print("INITIALIZING ML FALLBACK SYSTEM")
        print("="*80)

        self.ml_extractor = MLDimensionExtractor(self.db_path)

        # Try to load existing models
        if self.ml_extractor.load_models():
            print("[OK] Loaded existing ML models")
            return True

        # Train new models if not found
        print("\nNo saved models found - training new models...")
        self.ml_extractor.load_data()
        self.ml_extractor.train_all_models()
        self.ml_extractor.save_models()
        print("[OK] ML models trained and saved")
        return True

    def get_ml_prediction(self, program_number: str, dimension: str,
                         title: str, result: GCodeParseResult) -> Optional[float]:
        """Get ML prediction for a specific dimension"""
        if not self.ml_extractor or not self.ml_extractor.models.get(dimension):
            return None

        # Extract features
        features = self.ml_extractor.extract_title_features(title)

        # Add G-code features
        features['cb_from_gcode'] = result.cb_from_gcode if result.cb_from_gcode else 0
        features['ob_from_gcode'] = result.ob_from_gcode if result.ob_from_gcode else 0

        # Add known dimensions (use existing parsed values)
        features['known_od'] = result.outer_diameter if (dimension != 'outer_diameter' and result.outer_diameter) else 0
        features['known_cb'] = result.center_bore if (dimension != 'center_bore' and result.center_bore) else 0
        features['known_thickness'] = result.thickness if (dimension != 'thickness' and result.thickness) else 0

        # Create feature vector
        import numpy as np
        feature_vector = [features.get(fn, 0) for fn in self.ml_extractor.feature_names]
        feature_vector = np.array(feature_vector).reshape(1, -1)

        # Predict
        try:
            model = self.ml_extractor.models[dimension]
            prediction = model.predict(feature_vector)[0]
            return prediction
        except Exception as e:
            print(f"  ML prediction failed for {program_number} {dimension}: {e}")
            return None

    def apply_ml_fallbacks(self, result: GCodeParseResult, program_number: str, title: str):
        """Apply ML predictions as fallbacks for missing dimensions"""
        if not self.ml_extractor:
            return

        # Outer Diameter
        if not result.outer_diameter:
            ml_od = self.get_ml_prediction(program_number, 'outer_diameter', title, result)
            if ml_od:
                result.outer_diameter = ml_od
                result.detection_confidence = 'ML_FALLBACK'
                result.detection_notes.append(f'OD from ML: {ml_od:.2f}"')
                self.stats['ml_od'] += 1

        # Thickness
        if not result.thickness:
            ml_thickness = self.get_ml_prediction(program_number, 'thickness', title, result)
            if ml_thickness:
                result.thickness = ml_thickness
                if result.detection_confidence != 'ML_FALLBACK':
                    result.detection_confidence = 'ML_FALLBACK'
                result.detection_notes.append(f'Thickness from ML: {ml_thickness:.3f}"')
                self.stats['ml_thickness'] += 1

        # Center Bore
        if not result.center_bore:
            ml_cb = self.get_ml_prediction(program_number, 'center_bore', title, result)
            if ml_cb:
                result.center_bore = ml_cb
                if result.detection_confidence != 'ML_FALLBACK':
                    result.detection_confidence = 'ML_FALLBACK'
                result.detection_notes.append(f'CB from ML: {ml_cb:.1f}mm')
                self.stats['ml_cb'] += 1

    def rescan_database(self):
        """Rescan all programs with ML fallback"""
        print("\n" + "="*80)
        print("RESCANNING DATABASE WITH ML FALLBACK")
        print("="*80)

        # Initialize ML if available
        ml_initialized = self.initialize_ml()

        # Get all programs
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT program_number, title, file_path FROM programs ORDER BY program_number")
        programs = cursor.fetchall()

        self.stats['total'] = len(programs)
        print(f"\nFound {len(programs)} programs to rescan")

        # Process each program
        print("\nProcessing programs...")
        update_count = 0

        for i, (program_number, title, file_path) in enumerate(programs, 1):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(programs)} ({i/len(programs)*100:.1f}%)")

            # File path is already full path in database
            if file_path and os.path.exists(file_path):
                # Parse the file
                result = self.parser.parse_file(file_path)

                # Track what was parsed
                if result.outer_diameter:
                    self.stats['parsed_od'] += 1
                if result.thickness:
                    self.stats['parsed_thickness'] += 1
                if result.center_bore:
                    self.stats['parsed_cb'] += 1

                # Apply ML fallbacks for missing dimensions
                if ml_initialized:
                    self.apply_ml_fallbacks(result, program_number, title or "")

                # Track remaining missing
                if not result.outer_diameter:
                    self.stats['still_missing_od'] += 1
                if not result.thickness:
                    self.stats['still_missing_thickness'] += 1
                if not result.center_bore:
                    self.stats['still_missing_cb'] += 1

                # Update database
                self.update_program(cursor, program_number, result)
                update_count += 1

        # Commit changes
        conn.commit()
        conn.close()

        print(f"\n[OK] Updated {update_count} programs")

        # Print statistics
        self.print_statistics()

    def determine_validation_status(self, result: GCodeParseResult) -> str:
        """Determine validation status from issues/warnings"""
        if result.validation_issues:
            return 'CRITICAL'
        elif result.bore_warnings:
            return 'BORE_WARNING'
        elif result.dimensional_issues:
            return 'DIMENSIONAL'
        elif result.validation_warnings:
            return 'WARNING'
        else:
            return 'PASS'

    def update_program(self, cursor, program_number: str, result: GCodeParseResult):
        """Update program in database with parsed/ML results"""
        # Note: detection_notes is not in database schema, use notes field instead
        notes = '|'.join(result.detection_notes) if result.detection_notes else None

        # Determine validation status from issues
        validation_status = self.determine_validation_status(result)

        cursor.execute("""
            UPDATE programs SET
                spacer_type = ?,
                outer_diameter = ?,
                thickness = ?,
                center_bore = ?,
                hub_diameter = ?,
                hub_height = ?,
                counter_bore_diameter = ?,
                counter_bore_depth = ?,
                material = ?,
                cb_from_gcode = ?,
                ob_from_gcode = ?,
                validation_status = ?,
                detection_confidence = ?,
                validation_issues = ?,
                validation_warnings = ?,
                notes = ?,
                bore_warnings = ?,
                dimensional_issues = ?
            WHERE program_number = ?
        """, (
            result.spacer_type,
            result.outer_diameter,
            result.thickness,
            result.center_bore,
            result.hub_diameter,
            result.hub_height,
            result.counter_bore_diameter,
            result.counter_bore_depth,
            result.material,
            result.cb_from_gcode,
            result.ob_from_gcode,
            validation_status,
            result.detection_confidence,
            '|'.join(result.validation_issues) if result.validation_issues else None,
            '|'.join(result.validation_warnings) if result.validation_warnings else None,
            notes,
            '|'.join(result.bore_warnings) if result.bore_warnings else None,
            '|'.join(result.dimensional_issues) if result.dimensional_issues else None,
            program_number
        ))

    def print_statistics(self):
        """Print comprehensive statistics"""
        print("\n" + "="*80)
        print("RESCAN STATISTICS")
        print("="*80)

        total = self.stats['total']

        print(f"\nTotal programs: {total}")

        print("\n" + "-"*80)
        print("OUTER DIAMETER (OD)")
        print("-"*80)
        print(f"  Parsed from title/G-code:  {self.stats['parsed_od']:5d} ({self.stats['parsed_od']/total*100:.1f}%)")
        if self.stats['ml_od'] > 0:
            print(f"  ML Fallback predictions:    {self.stats['ml_od']:5d} ({self.stats['ml_od']/total*100:.1f}%)")
            total_od = self.stats['parsed_od'] + self.stats['ml_od']
            print(f"  TOTAL with OD:              {total_od:5d} ({total_od/total*100:.1f}%)")
        print(f"  Still missing:              {self.stats['still_missing_od']:5d} ({self.stats['still_missing_od']/total*100:.1f}%)")

        print("\n" + "-"*80)
        print("THICKNESS")
        print("-"*80)
        print(f"  Parsed from title/G-code:  {self.stats['parsed_thickness']:5d} ({self.stats['parsed_thickness']/total*100:.1f}%)")
        if self.stats['ml_thickness'] > 0:
            print(f"  ML Fallback predictions:    {self.stats['ml_thickness']:5d} ({self.stats['ml_thickness']/total*100:.1f}%)")
            total_thick = self.stats['parsed_thickness'] + self.stats['ml_thickness']
            print(f"  TOTAL with thickness:       {total_thick:5d} ({total_thick/total*100:.1f}%)")
        print(f"  Still missing:              {self.stats['still_missing_thickness']:5d} ({self.stats['still_missing_thickness']/total*100:.1f}%)")

        print("\n" + "-"*80)
        print("CENTER BORE (CB)")
        print("-"*80)
        print(f"  Parsed from title/G-code:  {self.stats['parsed_cb']:5d} ({self.stats['parsed_cb']/total*100:.1f}%)")
        if self.stats['ml_cb'] > 0:
            print(f"  ML Fallback predictions:    {self.stats['ml_cb']:5d} ({self.stats['ml_cb']/total*100:.1f}%)")
            total_cb = self.stats['parsed_cb'] + self.stats['ml_cb']
            print(f"  TOTAL with CB:              {total_cb:5d} ({total_cb/total*100:.1f}%)")
        print(f"  Still missing:              {self.stats['still_missing_cb']:5d} ({self.stats['still_missing_cb']/total*100:.1f}%)")

        # Overall improvement
        if self.stats['ml_od'] > 0 or self.stats['ml_thickness'] > 0 or self.stats['ml_cb'] > 0:
            print("\n" + "="*80)
            print("ML FALLBACK IMPACT")
            print("="*80)
            total_ml = self.stats['ml_od'] + self.stats['ml_thickness'] + self.stats['ml_cb']
            print(f"\nTotal ML predictions added: {total_ml}")
            print(f"  OD:        {self.stats['ml_od']:5d} programs")
            print(f"  Thickness: {self.stats['ml_thickness']:5d} programs")
            print(f"  CB:        {self.stats['ml_cb']:5d} programs")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Rescan database with ML fallback')
    parser.add_argument('--auto', action='store_true', help='Run without confirmation prompts')
    args = parser.parse_args()

    print("="*80)
    print("DATABASE RESCAN WITH ML FALLBACK")
    print("="*80)
    print("\nThis will:")
    print("  1. Rescan all programs using improved parser")
    print("  2. Apply ML predictions for missing dimensions")
    print("  3. Update database with results")

    # Check if ML is available
    if not ML_AVAILABLE:
        print("\n⚠️  WARNING: ML libraries not installed!")
        print("    Will rescan with improved parser only.")
        print("    To enable ML fallback, install:")
        print("    pip install pandas scikit-learn numpy")
        if not args.auto:
            try:
                response = input("\nContinue without ML? (y/n): ")
                if response.lower() != 'y':
                    print("Cancelled.")
                    return
            except EOFError:
                print("\nAuto-proceeding (non-interactive mode)...")

    if not args.auto:
        try:
            response = input("\nProceed with rescan? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
        except EOFError:
            print("\nAuto-proceeding (non-interactive mode)...")

    # Create rescanner and run
    rescanner = DatabaseRescanner()
    rescanner.rescan_database()

    print("\n" + "="*80)
    print("RESCAN COMPLETE!")
    print("="*80)
    print("\nYou can now:")
    print("  1. Open gcode_database_manager.py to view results")
    print("  2. Check programs marked 'ML_FALLBACK' in detection confidence")
    print("  3. Review Warning Details column for any issues")


if __name__ == '__main__':
    main()
