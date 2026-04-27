"""
core/fertilizer_rec.py
Fertilizer recommendation engine.

Uses a RandomForest classifier trained on soil + crop features.
Applies rule-based NPK deficiency overrides when critical thresholds are breached.
"""

import os
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR.mkdir(exist_ok=True)

# Rule-based NPK deficiency overrides

NPK_RULES = [
    # (condition_fn, fertilizer_name, reason)
    (lambda n, p, k: n < 20,  "Urea",          "Critical nitrogen deficiency detected"),
    (lambda n, p, k: p < 10,  "DAP",            "Critical phosphorus deficiency detected"),
    (lambda n, p, k: k < 10,  "MOP",            "Critical potassium deficiency detected"),
    (lambda n, p, k: n < 40 and p < 20, "NPK (20-20-0)", "Low N and P levels"),
    (lambda n, p, k: n < 40 and k < 20, "NPK (17-17-17)", "Low N and K levels"),
]


class FertilizerRecommender:

    MODEL_PATH = str(MODEL_DIR / "fertilizer_model.pkl")
    ENCODERS_PATH = str(MODEL_DIR / "encoders.pkl")
    FEATURES_PATH = str(MODEL_DIR / "feature_names.pkl")

    # Canonical column names after normalization
    FEATURE_COLS = [
        "Temperature", "Humidity", "Moisture",
        "Soil Type", "Crop Type",
        "Nitrogen", "Potassium", "Phosphorous",
    ]

    # Map known typos / variants
    COL_ALIASES = {
        "temparature": "Temperature",
        "temperature": "Temperature",
        "humidity":    "Humidity",
        "moisture":    "Moisture",
        "soil type":   "Soil Type",
        "crop type":   "Crop Type",
        "nitrogen":    "Nitrogen",
        "potassium":   "Potassium",
        "phosphorous": "Phosphorous",
        "phosphorus":  "Phosphorous",
        "fertilizer name": "Fertilizer Name",
    }

    def __init__(self):
        self.model_ = None
        self.encoders_ = {}
        self.feature_names_ = None
        self.label_encoder_ = None
        self.scaler_ = None
        self.is_fitted_ = False

    @classmethod
    def _normalize_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace and apply alias mapping to column names."""
        df.columns = [c.strip() for c in df.columns]
        rename_map = {}
        for col in df.columns:
            canonical = cls.COL_ALIASES.get(col.lower().strip())
            if canonical and canonical != col:
                rename_map[col] = canonical
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    # Training 
    def fit(self, csv_path: str, save: bool = True) -> "FertilizerRecommender":
        df = pd.read_csv(csv_path)
        df = self._normalize_columns(df)

        # Encode categorical columns
        cat_cols = ["Soil Type", "Crop Type"]
        self.encoders_ = {}
        for col in cat_cols:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str).str.strip())
            self.encoders_[col] = le

        # Encode target
        self.label_encoder_ = LabelEncoder()
        y = self.label_encoder_.fit_transform(df["Fertilizer Name"].astype(str).str.strip())

        X = df[self.FEATURE_COLS].values.astype(float)
        self.feature_names_ = self.FEATURE_COLS

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model_ = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
        self.model_.fit(X_train, y_train)

        acc = accuracy_score(y_test, self.model_.predict(X_test))
        print(f"   Fertilizer model accuracy: {acc:.4f}")

        self.is_fitted_ = True

        if save:
            joblib.dump(self.model_, self.MODEL_PATH)
            joblib.dump(self.encoders_, self.ENCODERS_PATH)
            joblib.dump(self.feature_names_, self.FEATURES_PATH)
            # Save full object too
            joblib.dump(self, str(MODEL_DIR / "fertilizer_full.pkl"))
            print(f"   Fertilizer model saved → {self.MODEL_PATH}")

        return self

    #  Load 
    def load(self) -> "FertilizerRecommender":
        full_path = str(MODEL_DIR / "fertilizer_full.pkl")
        if os.path.exists(full_path):
            loaded = joblib.load(full_path)
            self.__dict__.update(loaded.__dict__)
            self.is_fitted_ = True
            return self

        if not os.path.exists(self.MODEL_PATH):
            raise FileNotFoundError(f"Fertilizer model not found: {self.MODEL_PATH}")

        self.model_ = joblib.load(self.MODEL_PATH)
        self.encoders_ = joblib.load(self.ENCODERS_PATH)
        self.feature_names_ = joblib.load(self.FEATURES_PATH)
        self.is_fitted_ = True
        return self

    #  Rule-based override 
    def _check_rules(self, nitrogen: float, phosphorous: float, potassium: float):
        for condition, fertilizer, reason in NPK_RULES:
            if condition(nitrogen, phosphorous, potassium):
                return fertilizer, reason
        return None, None

    # Recommend
    def recommend(
        self,
        temperature: float,
        humidity: float,
        moisture: float,
        nitrogen: float,
        phosphorous: float,
        potassium: float,
        soil_type: str,
        crop_type: str,
        top_n: int = 5,
    ) -> dict:
        try:
            if not self.is_fitted_:
                raise RuntimeError("Call fit() or load() first.")

            # Rule-based override
            rule_fertilizer, rule_reason = self._check_rules(nitrogen, phosphorous, potassium)

            # Encode categoricals
            soil_enc = self.encoders_["Soil Type"]
            crop_enc = self.encoders_["Crop Type"]

            try:
                soil_val = soil_enc.transform([soil_type.strip()])[0]
            except ValueError:
                soil_val = 0  # unknown → default

            try:
                crop_val = crop_enc.transform([crop_type.strip()])[0]
            except ValueError:
                crop_val = 0

            X = np.array([[temperature, humidity, moisture, soil_val, crop_val, nitrogen, potassium, phosphorous]])
            proba = self.model_.predict_proba(X)[0]
            classes = self.label_encoder_.classes_

            top_indices = np.argsort(proba)[::-1][:top_n]
            top_recommendations = [
                {"fertilizer": classes[i], "probability": round(float(proba[i]), 4)}
                for i in top_indices
            ]

            primary = rule_fertilizer if rule_fertilizer else classes[top_indices[0]]
            confidence = float(proba[top_indices[0]])

            return {
                "type": "fertilizer_recommendation",
                "success": True,
                "primary_fertilizer": primary,
                "confidence": round(confidence, 4),
                "rule_applied": rule_fertilizer is not None,
                "rule_reason": rule_reason,
                "top_recommendations": top_recommendations,
                "input_summary": {
                    "nitrogen": nitrogen,
                    "phosphorous": phosphorous,
                    "potassium": potassium,
                    "soil_type": soil_type,
                    "crop_type": crop_type,
                },
            }

        except Exception as e:
            return {"type": "fertilizer_recommendation", "success": False, "error": str(e)}
