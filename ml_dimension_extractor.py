"""
ML-Based Dimension Extractor - Intelligent Fallback System

Uses machine learning to extract dimensions when title parsing fails.
Learns patterns from successfully parsed programs to predict missing dimensions.

Usage:
    python ml_dimension_extractor.py --train      # Train models
    python ml_dimension_extractor.py --predict    # Predict missing dimensions
    python ml_dimension_extractor.py --evaluate   # Evaluate accuracy
"""

import sqlite3
import re
from typing import Optional, Dict, List

try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_absolute_error, r2_score
    import pickle
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("ERROR: ML libraries required!")
    print("Install with: pip install pandas scikit-learn numpy")
    exit(1)


class MLDimensionExtractor:
    """ML-based dimension extraction for fallback when title parsing fails"""

    def __init__(self, db_path='gcode_database.db'):
        self.db_path = db_path
        self.df = None
        self.models = {}
        self.feature_names = []

    def load_data(self):
        """Load all programs with their dimensions"""
        print("Loading data from database...")
        conn = sqlite3.connect(self.db_path)

        self.df = pd.read_sql_query("""
            SELECT
                program_number, title, spacer_type,
                outer_diameter, thickness, center_bore,
                hub_diameter, hub_height,
                counter_bore_diameter, counter_bore_depth,
                cb_from_gcode, ob_from_gcode,
                material, lathe
            FROM programs
        """, conn)

        conn.close()
        print(f"Loaded {len(self.df)} programs")
        return self.df

    def extract_title_features(self, title: str) -> Dict[str, float]:
        """
        Extract numerical features from title even when parsing fails.
        Looks for ANY numbers that might be dimensions.
        """
        if not title or pd.isna(title):
            title = ""

        features = {}

        # Basic features
        features['title_length'] = len(title)
        features['has_IN'] = 1 if 'IN' in title.upper() else 0
        features['has_MM'] = 1 if 'MM' in title.upper() else 0
        features['has_HC'] = 1 if 'HC' in title.upper() else 0
        features['has_DIA'] = 1 if 'DIA' in title.upper() else 0
        features['has_slash'] = 1 if '/' in title else 0
        features['has_2PC'] = 1 if '2PC' in title.upper() else 0
        features['has_STEP'] = 1 if 'STEP' in title.upper() or 'B/C' in title.upper() else 0

        # Extract ALL numbers from title
        numbers = re.findall(r'\d+\.?\d*', title)
        numbers = [float(n) for n in numbers if float(n) > 0]

        # Statistical features from numbers
        if numbers:
            features['num_count'] = len(numbers)
            features['num_min'] = min(numbers)
            features['num_max'] = max(numbers)
            features['num_mean'] = np.mean(numbers)
            features['num_median'] = np.median(numbers)

            # Likely candidates for specific dimensions
            # OD usually 5-13 inches
            od_candidates = [n for n in numbers if 3 <= n <= 14]
            features['od_candidate'] = od_candidates[0] if od_candidates else 0

            # CB usually 40-220mm
            cb_candidates = [n for n in numbers if 30 <= n <= 250]
            features['cb_candidate'] = cb_candidates[0] if cb_candidates else 0

            # Thickness usually 0.5-4 inches
            thick_candidates = [n for n in numbers if 0.3 <= n <= 5]
            features['thick_candidate'] = thick_candidates[-1] if thick_candidates else 0

        else:
            features['num_count'] = 0
            features['num_min'] = 0
            features['num_max'] = 0
            features['num_mean'] = 0
            features['num_median'] = 0
            features['od_candidate'] = 0
            features['cb_candidate'] = 0
            features['thick_candidate'] = 0

        return features

    def prepare_training_data(self, target_dimension: str):
        """
        Prepare training data for a specific dimension.
        Uses programs where we successfully extracted the dimension.
        """
        if self.df is None:
            self.load_data()

        print(f"\nPreparing training data for {target_dimension}...")

        # Only use programs where we have the target dimension
        df_train = self.df[self.df[target_dimension].notna()].copy()
        print(f"  Programs with {target_dimension}: {len(df_train)}")

        # Extract features from titles
        print("  Extracting title features...")
        title_features = df_train['title'].apply(self.extract_title_features)
        title_features_df = pd.DataFrame(title_features.tolist())

        # Add G-code features (ALWAYS add to ensure consistent feature set)
        if 'cb_from_gcode' in df_train.columns:
            title_features_df['cb_from_gcode'] = df_train['cb_from_gcode'].fillna(0)
        if 'ob_from_gcode' in df_train.columns:
            title_features_df['ob_from_gcode'] = df_train['ob_from_gcode'].fillna(0)

        # Add other known dimensions as features (ALWAYS add all 3, set target to 0)
        # This ensures consistent feature count across all models
        if target_dimension != 'outer_diameter' and 'outer_diameter' in df_train.columns:
            title_features_df['known_od'] = df_train['outer_diameter'].fillna(0)
        else:
            title_features_df['known_od'] = 0  # Add as zero column for consistency

        if target_dimension != 'center_bore' and 'center_bore' in df_train.columns:
            title_features_df['known_cb'] = df_train['center_bore'].fillna(0)
        else:
            title_features_df['known_cb'] = 0  # Add as zero column for consistency

        if target_dimension != 'thickness' and 'thickness' in df_train.columns:
            title_features_df['known_thickness'] = df_train['thickness'].fillna(0)
        else:
            title_features_df['known_thickness'] = 0  # Add as zero column for consistency

        # Target values
        y = df_train[target_dimension].values

        # Store feature names
        self.feature_names = title_features_df.columns.tolist()

        return title_features_df.values, y

    def train_model(self, dimension: str):
        """Train a model to predict a specific dimension"""
        print(f"\n{'='*80}")
        print(f"TRAINING MODEL FOR: {dimension}")
        print('='*80)

        # Prepare data
        X, y = self.prepare_training_data(dimension)

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train Random Forest
        print("\nTraining Random Forest model...")
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)

        # Evaluate
        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)

        train_mae = mean_absolute_error(y_train, train_pred)
        test_mae = mean_absolute_error(y_test, test_pred)
        train_r2 = r2_score(y_train, train_pred)
        test_r2 = r2_score(y_test, test_pred)

        print(f"\nModel Performance:")
        print(f"  Training MAE:   {train_mae:.3f}")
        print(f"  Testing MAE:    {test_mae:.3f}")
        print(f"  Training R²:    {train_r2:.3f}")
        print(f"  Testing R²:     {test_r2:.3f}")

        # Feature importance
        print(f"\nTop 10 Feature Importances:")
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        print(feature_importance.head(10))

        # Save model
        self.models[dimension] = model

        return model, test_mae, test_r2

    def train_all_models(self):
        """Train models for all important dimensions"""
        dimensions = ['outer_diameter', 'thickness', 'center_bore', 'hub_diameter', 'hub_height']
        results = {}

        for dim in dimensions:
            try:
                model, mae, r2 = self.train_model(dim)
                results[dim] = {'model': model, 'mae': mae, 'r2': r2}
            except Exception as e:
                print(f"\nERROR training {dim}: {e}")
                results[dim] = None

        return results

    def predict_missing_dimensions(self):
        """Find programs with missing dimensions and predict them"""
        print("\n" + "="*80)
        print("PREDICTING MISSING DIMENSIONS")
        print("="*80)

        if self.df is None:
            self.load_data()

        predictions = []

        # Find programs with missing dimensions
        for dimension in ['outer_diameter', 'thickness', 'center_bore']:
            missing = self.df[self.df[dimension].isna()].copy()

            if len(missing) == 0:
                print(f"\n{dimension}: No missing values")
                continue

            print(f"\n{dimension}: {len(missing)} missing values")

            if dimension not in self.models:
                print(f"  No model trained for {dimension} - skipping")
                continue

            model = self.models[dimension]

            # Extract features for missing programs
            for idx, row in missing.iterrows():
                title = row['title'] if pd.notna(row['title']) else ""
                features = self.extract_title_features(title)

                # Add G-code features (ALWAYS add to match training)
                features['cb_from_gcode'] = row['cb_from_gcode'] if pd.notna(row['cb_from_gcode']) else 0
                features['ob_from_gcode'] = row['ob_from_gcode'] if pd.notna(row['ob_from_gcode']) else 0

                # Add known dimensions (ALWAYS add to match training, use 0 for the target dimension)
                features['known_od'] = row['outer_diameter'] if (dimension != 'outer_diameter' and pd.notna(row['outer_diameter'])) else 0
                features['known_cb'] = row['center_bore'] if (dimension != 'center_bore' and pd.notna(row['center_bore'])) else 0
                features['known_thickness'] = row['thickness'] if (dimension != 'thickness' and pd.notna(row['thickness'])) else 0

                # Create feature vector matching training
                feature_vector = [features.get(fn, 0) for fn in self.feature_names]
                feature_vector = np.array(feature_vector).reshape(1, -1)

                # Predict
                predicted = model.predict(feature_vector)[0]

                predictions.append({
                    'program_number': row['program_number'],
                    'title': title,
                    'dimension': dimension,
                    'predicted_value': predicted,
                    'confidence': 'ML_PREDICTION'
                })

        # Display predictions
        if predictions:
            print(f"\n\nGENERATED {len(predictions)} PREDICTIONS:")
            print("-"*80)

            for pred in predictions[:20]:  # Show first 20
                print(f"{pred['program_number']}: {pred['dimension']}={pred['predicted_value']:.2f}")
                print(f"  Title: {pred['title'][:70]}")

            print(f"\n... and {len(predictions)-20} more") if len(predictions) > 20 else None

        return predictions

    def save_models(self, filepath='ml_dimension_models.pkl'):
        """Save trained models to disk"""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'feature_names': self.feature_names
            }, f)
        print(f"\nModels saved to {filepath}")

    def load_models(self, filepath='ml_dimension_models.pkl'):
        """Load trained models from disk"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.models = data['models']
                self.feature_names = data['feature_names']
            print(f"Models loaded from {filepath}")
            return True
        except FileNotFoundError:
            print(f"No saved models found at {filepath}")
            return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='ML-Based Dimension Extraction')
    parser.add_argument('--train', action='store_true', help='Train models')
    parser.add_argument('--predict', action='store_true', help='Predict missing dimensions')
    parser.add_argument('--evaluate', action='store_true', help='Evaluate model accuracy')
    parser.add_argument('--save', action='store_true', help='Save trained models')

    args = parser.parse_args()

    extractor = MLDimensionExtractor()

    if args.train or not any([args.predict, args.evaluate]):
        # Train models
        extractor.load_data()
        results = extractor.train_all_models()

        if args.save:
            extractor.save_models()

    if args.predict:
        # Load or train models
        if not extractor.load_models():
            print("Training models first...")
            extractor.load_data()
            extractor.train_all_models()
            extractor.save_models()

        # Predict missing dimensions
        predictions = extractor.predict_missing_dimensions()

        # Option to save predictions to CSV
        if predictions:
            import csv
            with open('ml_dimension_predictions.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['program_number', 'title', 'dimension', 'predicted_value', 'confidence'])
                writer.writeheader()
                writer.writerows(predictions)
            print(f"\nPredictions saved to ml_dimension_predictions.csv")

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
