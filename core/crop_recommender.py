"""
core/crop_recommender.py
Production-grade crop recommendation engine.

Pipeline:
  - Stacked ensemble (RF + ExtraTrees + GradientBoosting → LogisticRegression)
  - Uncertainty detection via Shannon entropy
  - Seasonal scoring (Kharif / Rabi / Zaid)
  - Weather suitability scoring
  - Extended-model fallback when primary is uncertain
"""

import os
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR.mkdir(exist_ok=True)


#  Knowledge Base

CROP_CALENDAR = {
    "rice":        {"season": "kharif", "sowing": [6, 7],  "temp": (20, 35), "rain": (100, 400)},
    "maize":       {"season": "kharif", "sowing": [6, 7],  "temp": (18, 32), "rain": (50, 200)},
    "jute":        {"season": "kharif", "sowing": [4, 5],  "temp": (24, 37), "rain": (150, 350)},
    "cotton":      {"season": "kharif", "sowing": [5, 6],  "temp": (20, 35), "rain": (50, 200)},
    "chickpea":    {"season": "rabi",   "sowing": [10, 11],"temp": (10, 25), "rain": (20, 100)},
    "kidneybeans": {"season": "kharif", "sowing": [6, 7],  "temp": (15, 28), "rain": (80, 200)},
    "pigeonpeas":  {"season": "kharif", "sowing": [6, 7],  "temp": (20, 35), "rain": (60, 200)},
    "mothbeans":   {"season": "kharif", "sowing": [7, 8],  "temp": (24, 38), "rain": (30, 100)},
    "mungbean":    {"season": "kharif", "sowing": [6, 7],  "temp": (20, 35), "rain": (50, 150)},
    "blackgram":   {"season": "kharif", "sowing": [6, 7],  "temp": (20, 35), "rain": (50, 200)},
    "lentil":      {"season": "rabi",   "sowing": [10, 11],"temp": (10, 25), "rain": (20, 100)},
    "pomegranate": {"season": "kharif", "sowing": [6, 7],  "temp": (20, 38), "rain": (50, 150)},
    "banana":      {"season": "kharif", "sowing": [6, 7],  "temp": (20, 35), "rain": (100, 350)},
    "mango":       {"season": "zaid",   "sowing": [3, 4],  "temp": (24, 38), "rain": (50, 200)},
    "grapes":      {"season": "rabi",   "sowing": [1, 2],  "temp": (15, 30), "rain": (30, 100)},
    "watermelon":  {"season": "zaid",   "sowing": [3, 4],  "temp": (22, 35), "rain": (20, 80)},
    "muskmelon":   {"season": "zaid",   "sowing": [3, 4],  "temp": (22, 35), "rain": (20, 80)},
    "apple":       {"season": "rabi",   "sowing": [11, 12],"temp": (5, 22),  "rain": (50, 150)},
    "orange":      {"season": "rabi",   "sowing": [10, 11],"temp": (15, 30), "rain": (50, 200)},
    "papaya":      {"season": "zaid",   "sowing": [3, 4],  "temp": (22, 35), "rain": (50, 200)},
    "coconut":     {"season": "kharif", "sowing": [6, 7],  "temp": (20, 35), "rain": (100, 400)},
    "coffee":      {"season": "kharif", "sowing": [5, 6],  "temp": (15, 28), "rain": (150, 400)},
    "wheat":       {"season": "rabi",   "sowing": [10, 11],"temp": (10, 25), "rain": (30, 100)},
}

SEASON_MAP = {
    1: "rabi", 2: "rabi", 3: "rabi",
    4: "zaid", 5: "zaid", 6: "zaid",
    7: "kharif", 8: "kharif", 9: "kharif", 10: "kharif",
    11: "rabi", 12: "rabi",
}

FEATURE_COLS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]


# Scoring helpers

def _season_score(crop: str, month: int) -> float:
    cal = CROP_CALENDAR.get(crop.lower())
    if cal is None:
        return 0.5
    season = SEASON_MAP.get(month, "unknown")
    if cal["season"] == season:
        return 1.0
    dist = min(abs(month - m) % 12 for m in cal["sowing"])
    return max(0.0, 1.0 - dist / 3.0)


def _weather_score(crop: str, temperature: float, rainfall: float) -> float:
    cal = CROP_CALENDAR.get(crop.lower())
    if cal is None:
        return 0.5
    tmin, tmax = cal["temp"]
    rmin, rmax = cal["rain"]
    t_score = (
        1.0 if tmin <= temperature <= tmax
        else max(0.0, 1.0 - min(abs(temperature - tmin), abs(temperature - tmax)) / 10)
    )
    r_score = (
        1.0 if rmin <= rainfall <= rmax
        else max(0.0, 1.0 - min(abs(rainfall - rmin), abs(rainfall - rmax)) / 100)
    )
    return (t_score + r_score) / 2.0


def _composite_score(ml_prob: float, season_s: float, weather_s: float) -> float:
    return (0.55 * ml_prob) + (0.25 * season_s) + (0.20 * weather_s)


# Stacking ensemble

class _OOFStacker:
    """Out-of-fold stacking ensemble."""

    def __init__(self, n_splits: int = 5, random_state: int = 42):
        self.n_splits = n_splits
        self.random_state = random_state
        self.base_models_ = None
        self.meta_model_ = None
        self.classes_ = None

    @staticmethod
    def _build_base_models(random_state: int):
        return [
            ("rf", RandomForestClassifier(
                n_estimators=300, max_features="sqrt",
                random_state=random_state, n_jobs=-1)),
            ("et", ExtraTreesClassifier(
                n_estimators=300, max_features="sqrt",
                random_state=random_state, n_jobs=-1)),
            ("gb", GradientBoostingClassifier(
                n_estimators=200, learning_rate=0.05,
                max_depth=5, random_state=random_state)),
        ]

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_OOFStacker":
        skf = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=self.random_state)
        base_defs = self._build_base_models(self.random_state)
        n_classes = len(np.unique(y))
        oof_meta = np.zeros((X.shape[0], len(base_defs) * n_classes))

        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            print(f"  Fold {fold + 1}/{self.n_splits}...")
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr = y[train_idx]
            fold_probas = []
            for _, model in base_defs:
                m = model.__class__(**model.get_params())
                m.fit(X_tr, y_tr)
                fold_probas.append(m.predict_proba(X_val))
            oof_meta[val_idx] = np.hstack(fold_probas)

        self.meta_model_ = LogisticRegression(max_iter=1000, random_state=self.random_state)
        self.meta_model_.fit(oof_meta, y)

        self.base_models_ = []
        for name, model in base_defs:
            m = model.__class__(**model.get_params())
            m.fit(X, y)
            self.base_models_.append((name, m))

        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        meta_input = np.hstack([m.predict_proba(X) for _, m in self.base_models_])
        return self.meta_model_.predict_proba(meta_input)


# Main CropRecommender

class CropRecommender:

    UNCERTAINTY_THRESHOLD = 1.8
    MODEL_PATH = str(MODEL_DIR / "crop_model.pkl")

    def __init__(self):
        self.stacker_ = None
        self.scaler_ = None
        self.encoder_ = None
        self.is_fitted_ = False
        self.ext_model_ = None
        self.ext_encoder_ = None
        self.ext_scaler_ = None

    # Extended model 
    def fit_extended(self, csv_path: str) -> None:
        df = pd.read_csv(csv_path)
        col_map = {c: (c.strip() if c.strip() in ("N", "P", "K") else c.strip().lower()) for c in df.columns}
        df.rename(columns=col_map, inplace=True)
        X_raw = df[FEATURE_COLS].values
        y_raw = df["label"].str.lower().str.strip().values
        self.ext_encoder_ = LabelEncoder()
        y = self.ext_encoder_.fit_transform(y_raw)
        self.ext_scaler_ = StandardScaler()
        X = self.ext_scaler_.fit_transform(X_raw)
        self.ext_model_ = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
        self.ext_model_.fit(X, y)
        print(f" Extended model trained from {csv_path}")

    # ── Validation ────────────────────────────
    def _validate_inputs(self, N, P, K, temperature, humidity, ph, rainfall):
        if any(v is None for v in [N, P, K, temperature, humidity, ph, rainfall]):
            raise ValueError("All input fields are required.")
        if any(v < 0 for v in [N, P, K, rainfall]):
            raise ValueError("N, P, K, and rainfall must be non-negative.")
        if not (-10 <= temperature <= 60):
            raise ValueError("Temperature must be between -10 and 60°C.")
        if not (0 <= humidity <= 100):
            raise ValueError("Humidity must be between 0 and 100%.")
        if not (0 <= ph <= 14):
            raise ValueError("pH must be between 0 and 14.")

    # Primary training 
    def fit(self, csv_path: str, save_path: str = None) -> "CropRecommender":
        df = pd.read_csv(csv_path)
        col_map = {c: (c.strip() if c.strip() in ("N", "P", "K") else c.strip().lower()) for c in df.columns}
        df.rename(columns=col_map, inplace=True)
        X_raw = df[FEATURE_COLS].values
        y_raw = df["label"].str.lower().str.strip().values
        self.encoder_ = LabelEncoder()
        y = self.encoder_.fit_transform(y_raw)
        self.scaler_ = StandardScaler()
        X = self.scaler_.fit_transform(X_raw)
        self.stacker_ = _OOFStacker()
        self.stacker_.fit(X, y)
        self.stacker_.classes_ = self.encoder_.classes_
        self.is_fitted_ = True
        target = save_path or self.MODEL_PATH
        joblib.dump(self, target)
        print(f" Crop model saved → {target}")
        return self

    # Load 
    def load(self, path: str = None) -> "CropRecommender":
        path = path or self.MODEL_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found: {path}")
        loaded = joblib.load(path)
        if not isinstance(loaded, CropRecommender):
            raise TypeError("Invalid model file.")
        self.__dict__.update(loaded.__dict__)
        self.is_fitted_ = True
        return self

    def _scale(self, **kwargs) -> np.ndarray:
        row = np.array([[kwargs[f] for f in FEATURE_COLS]])
        return self.scaler_.transform(row)

    def _proba_vector(self, X_scaled: np.ndarray) -> np.ndarray:
        return self.stacker_.predict_proba(X_scaled)[0]

    def _uncertainty(self, proba: np.ndarray) -> dict:
        H = float(scipy_entropy(proba))
        max_H = float(np.log(len(proba)))
        return {
            "entropy": round(H, 4),
            "normalized_entropy": round(H / max_H if max_H > 0 else 0, 4),
            "is_uncertain": H > self.UNCERTAINTY_THRESHOLD,
            "confidence_label": (
                "high" if H < 0.8 else
                "medium" if H < self.UNCERTAINTY_THRESHOLD else
                "low"
            ),
        }

    def _rank_crops(self, proba, month, temperature, rainfall, top_n=5):
        results = []
        for idx, ml_prob in enumerate(proba):
            crop = self.encoder_.classes_[idx]
            s_score = _season_score(crop, month)
            w_score = _weather_score(crop, temperature, rainfall)
            composite = _composite_score(ml_prob, s_score, w_score)
            results.append({
                "crop": crop,
                "composite_score": round(float(composite), 4),
                "ml_probability": round(float(ml_prob), 4),
                "seasonal_score": round(float(s_score), 4),
                "weather_score": round(float(w_score), 4),
            })
        return sorted(results, key=lambda x: x["composite_score"], reverse=True)[:top_n]

    # Recommend 
    def recommend(self, N, P, K, temperature, humidity, ph, rainfall, month=None, top_n=5) -> dict:
        try:
            self._validate_inputs(N, P, K, temperature, humidity, ph, rainfall)
            if not self.is_fitted_:
                raise RuntimeError("Call fit() or load() first.")
            if month is None:
                from datetime import datetime
                month = datetime.now().month
            season_name = SEASON_MAP.get(month, "unknown")
            X = self._scale(N=N, P=P, K=K, temperature=temperature, humidity=humidity, ph=ph, rainfall=rainfall)
            proba = self._proba_vector(X)
            uncertainty = self._uncertainty(proba)

            # Extended model fallback
            if uncertainty["is_uncertain"] and self.ext_model_ is not None:
                X_ext = self.ext_scaler_.transform(np.array([[N, P, K, temperature, humidity, ph, rainfall]]))
                ext_proba = self.ext_model_.predict_proba(X_ext)[0]
                ext_rankings = []
                for idx, prob in enumerate(ext_proba):
                    crop = self.ext_encoder_.classes_[idx]
                    s_score = _season_score(crop, month)
                    w_score = _weather_score(crop, temperature, rainfall)
                    composite = _composite_score(prob, s_score, w_score)
                    ext_rankings.append({
                        "crop": crop,
                        "composite_score": round(float(composite), 4),
                        "ml_probability": round(float(prob), 4),
                        "seasonal_score": round(float(s_score), 4),
                        "weather_score": round(float(w_score), 4),
                    })
                ext_rankings = sorted(ext_rankings, key=lambda x: x["composite_score"], reverse=True)[:top_n]
                top = ext_rankings[0]
                return {
                    "type": "crop_recommendation", "success": True, "source": "extended_model",
                    "primary_crop": top["crop"], "confidence": uncertainty["confidence_label"],
                    "uncertainty_score": uncertainty["entropy"], "season": season_name,
                    "seasonal_score": top["seasonal_score"], "weather_score": top["weather_score"],
                    "top_recommendations": ext_rankings,
                }

            rankings = self._rank_crops(proba, month, temperature, rainfall, top_n)
            top = rankings[0]
            return {
                "type": "crop_recommendation", "success": True, "source": "primary_model",
                "primary_crop": top["crop"], "confidence": uncertainty["confidence_label"],
                "uncertainty_score": uncertainty["entropy"], "season": season_name,
                "seasonal_score": top["seasonal_score"], "weather_score": top["weather_score"],
                "top_recommendations": rankings,
            }
        except Exception as e:
            return {"type": "crop_recommendation", "success": False, "error": str(e)}

    #  Evaluate
    def evaluate(self, csv_path: str) -> dict:
        if not self.is_fitted_:
            raise RuntimeError("Call fit() or load() first.")
        df = pd.read_csv(csv_path)
        col_map = {c: (c.strip() if c.strip() in ("N", "P", "K") else c.strip().lower()) for c in df.columns}
        df.rename(columns=col_map, inplace=True)
        X_raw = df[FEATURE_COLS].values
        y_raw = df["label"].str.lower().str.strip().values
        X = self.scaler_.transform(X_raw)
        y_true = self.encoder_.transform(y_raw)
        proba = self.stacker_.predict_proba(X)
        y_pred = np.argmax(proba, axis=1)
        top1_acc = accuracy_score(y_true, y_pred)
        top3_acc = float(np.mean([y_true[i] in np.argsort(proba[i])[-3:] for i in range(len(y_true))]))
        macro_f1 = f1_score(y_true, y_pred, average="macro")
        entropies = [scipy_entropy(p) for p in proba]
        uncertain_rate = float(np.mean([e > self.UNCERTAINTY_THRESHOLD for e in entropies]))
        return {
            "top1_accuracy": round(top1_acc, 4),
            "top3_accuracy": round(top3_acc, 4),
            "macro_f1": round(macro_f1, 4),
            "mean_entropy": round(float(np.mean(entropies)), 4),
            "uncertain_prediction_rate": round(uncertain_rate, 4),
        }
