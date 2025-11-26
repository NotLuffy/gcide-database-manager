"""
ML-Based G-Code Analyzer (Experimental)

This module runs alongside the main parser to provide ML-based insights
and predictions. It does NOT modify the database - only provides analysis.

Usage:
    python ml_analyzer.py --analyze          # Analyze patterns
    python ml_analyzer.py --detect-anomalies # Find unusual programs
    python ml_analyzer.py --predict-2pc      # Test 2PC classification
"""

import sqlite3
import sys

# Check if ML libraries are installed
try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    MISSING_LIBS = str(e)


class MLAnalyzer:
    """ML-based analyzer for G-code programs (experimental, read-only)"""

    def __init__(self, db_path='gcode_database.db'):
        if not ML_AVAILABLE:
            print("ERROR: ML libraries not installed!")
            print(f"Missing: {MISSING_LIBS}")
            print("\nInstall with:")
            print("  pip install pandas scikit-learn numpy scipy")
            sys.exit(1)

        self.db_path = db_path
        self.df = None

    def load_data(self):
        """Load all programs from database into pandas DataFrame"""
        print("Loading data from database...")
        conn = sqlite3.connect(self.db_path)

        # Load all programs
        self.df = pd.read_sql_query("""
            SELECT
                program_number, title, spacer_type, outer_diameter,
                thickness, center_bore, hub_diameter, hub_height,
                counter_bore_diameter, counter_bore_depth,
                material, validation_status, detection_confidence,
                cb_from_gcode, ob_from_gcode, drill_depth
            FROM programs
        """, conn)

        conn.close()
        print(f"Loaded {len(self.df)} programs")
        return self.df

    def analyze_patterns(self):
        """Analyze patterns in the data"""
        if self.df is None:
            self.load_data()

        print("\n" + "="*80)
        print("DATA ANALYSIS - PATTERN DISCOVERY")
        print("="*80)

        # Basic statistics
        print("\n1. SPACER TYPE DISTRIBUTION:")
        print(self.df['spacer_type'].value_counts())

        print("\n2. VALIDATION STATUS DISTRIBUTION:")
        print(self.df['validation_status'].value_counts())

        print("\n3. OUTER DIAMETER STATISTICS:")
        print(self.df['outer_diameter'].describe())

        print("\n4. THICKNESS BY SPACER TYPE:")
        print(self.df.groupby('spacer_type')['thickness'].describe())

        print("\n5. CENTER BORE BY SPACER TYPE:")
        print(self.df.groupby('spacer_type')['center_bore'].describe())

        # Correlations
        print("\n6. DIMENSION CORRELATIONS:")
        numeric_cols = ['outer_diameter', 'thickness', 'center_bore', 'hub_diameter']
        corr = self.df[numeric_cols].corr()
        print(corr)

        # 2PC Analysis
        print("\n7. 2PC PROGRAMS ANALYSIS:")
        twopc = self.df[self.df['spacer_type'].str.contains('2PC', na=False)]
        print(f"Total 2PC programs: {len(twopc)}")
        print("\n2PC Type breakdown:")
        print(twopc['spacer_type'].value_counts())

        print("\n2PC Thickness patterns:")
        print(twopc.groupby('spacer_type')['thickness'].describe())

        return self.df

    def detect_anomalies(self, contamination=0.05):
        """Use Isolation Forest to detect anomalous programs"""
        if self.df is None:
            self.load_data()

        print("\n" + "="*80)
        print("ANOMALY DETECTION - Isolation Forest")
        print("="*80)

        # Prepare features (only numeric, non-null)
        features = ['outer_diameter', 'thickness', 'center_bore', 'hub_diameter', 'hub_height']
        df_features = self.df[features].fillna(0)

        # Train on all data
        print(f"\nTraining Isolation Forest (contamination={contamination})...")
        detector = IsolationForest(contamination=contamination, random_state=42)
        predictions = detector.fit_predict(df_features)

        # Add predictions to dataframe
        self.df['is_anomaly'] = predictions == -1

        # Show anomalies
        anomalies = self.df[self.df['is_anomaly']]
        print(f"\nFound {len(anomalies)} anomalies ({len(anomalies)/len(self.df)*100:.1f}%)")

        print("\nTop 10 anomalies:")
        print(anomalies[['program_number', 'title', 'spacer_type', 'outer_diameter',
                        'thickness', 'center_bore', 'validation_status']].head(10))

        # Compare to current validation
        print("\nAnomaly vs Current Validation Status:")
        print(pd.crosstab(self.df['is_anomaly'], self.df['validation_status']))

        return anomalies

    def predict_2pc_classification(self):
        """Train classifier to predict 2PC LUG vs STUD"""
        if self.df is None:
            self.load_data()

        print("\n" + "="*80)
        print("2PC LUG/STUD CLASSIFICATION - Random Forest")
        print("="*80)

        # Filter to 2PC programs with labels
        twopc = self.df[self.df['spacer_type'].isin(['2PC LUG', '2PC STUD'])].copy()
        print(f"\nTraining data: {len(twopc)} labeled 2PC programs")
        print(f"  LUG: {len(twopc[twopc['spacer_type'] == '2PC LUG'])}")
        print(f"  STUD: {len(twopc[twopc['spacer_type'] == '2PC STUD'])}")

        if len(twopc) < 50:
            print("\nNot enough training data (need at least 50 labeled examples)")
            return None

        # Features that might distinguish LUG from STUD
        feature_cols = ['outer_diameter', 'thickness', 'center_bore', 'hub_diameter',
                       'hub_height', 'drill_depth', 'cb_from_gcode']

        # Prepare data
        X = twopc[feature_cols].fillna(0)
        y = twopc['spacer_type']

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )

        # Train Random Forest
        print("\nTraining Random Forest classifier...")
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)

        # Evaluate
        y_pred = clf.predict(X_test)
        accuracy = (y_pred == y_test).mean()

        print(f"\nTest Accuracy: {accuracy*100:.1f}%")

        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))

        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))

        print("\nFeature Importance:")
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': clf.feature_importances_
        }).sort_values('importance', ascending=False)
        print(feature_importance)

        # Test on UNSURE programs
        unsure = self.df[self.df['spacer_type'] == '2PC UNSURE'].copy()
        if len(unsure) > 0:
            print(f"\n\nTesting on {len(unsure)} '2PC UNSURE' programs:")
            X_unsure = unsure[feature_cols].fillna(0)
            predictions = clf.predict(X_unsure)
            probabilities = clf.predict_proba(X_unsure)

            unsure['ml_prediction'] = predictions
            unsure['ml_confidence'] = probabilities.max(axis=1)

            print("\nPredictions for UNSURE programs:")
            print(unsure[['program_number', 'title', 'thickness', 'hub_height',
                         'ml_prediction', 'ml_confidence']].head(10))

            print("\nPrediction distribution:")
            print(unsure['ml_prediction'].value_counts())

        return clf

    def compare_with_current(self):
        """Compare ML predictions with current rule-based system"""
        if self.df is None:
            self.load_data()

        print("\n" + "="*80)
        print("ML vs RULE-BASED COMPARISON")
        print("="*80)

        # Run both methods and compare
        print("\nThis feature coming soon...")
        print("Will compare:")
        print("  - ML anomaly detection vs current validation")
        print("  - ML 2PC classification vs current detection")
        print("  - Confidence scores vs detection confidence")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='ML-based G-Code Analysis (Experimental)')
    parser.add_argument('--analyze', action='store_true', help='Analyze patterns in data')
    parser.add_argument('--detect-anomalies', action='store_true', help='Detect anomalous programs')
    parser.add_argument('--predict-2pc', action='store_true', help='Predict 2PC LUG/STUD classification')
    parser.add_argument('--compare', action='store_true', help='Compare ML vs current system')
    parser.add_argument('--all', action='store_true', help='Run all analyses')

    args = parser.parse_args()

    # Run all if no specific option chosen
    if not any([args.analyze, args.detect_anomalies, args.predict_2pc, args.compare, args.all]):
        args.all = True

    analyzer = MLAnalyzer()

    if args.analyze or args.all:
        analyzer.analyze_patterns()

    if args.detect_anomalies or args.all:
        analyzer.detect_anomalies()

    if args.predict_2pc or args.all:
        analyzer.predict_2pc_classification()

    if args.compare or args.all:
        analyzer.compare_with_current()


if __name__ == '__main__':
    main()
