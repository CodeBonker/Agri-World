"""
scripts/train_models.py
Train and save all ML models (crop + fertilizer).

Usage:
    python scripts/train_models.py

Requirements:
    - data/Crop_recommendation.csv
    - data/Fertilizer Prediction.csv
    - (optional) data/synthetic_102_crop_dataset.csv  ← extended crop model

Downloads data automatically if not present.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

CROP_CSV = DATA_DIR / "Crop_recommendation.csv"
FERT_CSV = DATA_DIR / "Fertilizer Prediction.csv"
EXT_CSV  = DATA_DIR / "synthetic_102_crop_dataset.csv"

#  Download datasets if missing 

CROP_URL = "https://raw.githubusercontent.com/Manideep2k4/cropseek-llm/main/data/Crop_recommendation.csv"
FERT_URL = "https://raw.githubusercontent.com/Manideep2k4/cropseek-llm/main/data/Fertilizer%20Prediction.csv"
EXT_URL  = "https://raw.githubusercontent.com/Manideep2k4/cropseek-llm/main/data/synthetic_102_crop_dataset.csv"


def download_if_missing(url: str, dest: Path):
    if dest.exists():
        print(f" Found: {dest.name}")
        return
    print(f" Downloading {dest.name}...")
    import urllib.request
    try:
        urllib.request.urlretrieve(url, dest)
        print(f" Downloaded: {dest.name}")
    except Exception as e:
        print(f" Failed to download {dest.name}: {e}")
        print(f" Please manually place the file at: {dest}")


# Train crop model

def train_crop_model():
    print("\n" + "="*50)
    print("  Training Crop Recommendation Model")
    print("="*50)

    from core.crop_recommender import CropRecommender

    if not CROP_CSV.exists():
        print(f"  Missing: {CROP_CSV}")
        print(" Run this script again after placing the CSV.")
        return False

    rec = CropRecommender()
    t0 = time.time()
    rec.fit(str(CROP_CSV))
    elapsed = time.time() - t0
    print(f" Crop model trained in {elapsed:.1f}s")

    # Evaluate
    try:
        metrics = rec.evaluate(str(CROP_CSV))
        print(f"  Top-1 Accuracy: {metrics['top1_accuracy']:.4f}")
        print(f"  Top-3 Accuracy: {metrics['top3_accuracy']:.4f}")
        print(f"  Macro F1:       {metrics['macro_f1']:.4f}")
    except Exception as e:
        print(f"  Evaluation skipped: {e}")

    # Extended model
    if EXT_CSV.exists():
        print("\n  Training extended crop model...")
        rec.fit_extended(str(EXT_CSV))
        import joblib
        joblib.dump(rec, str(MODEL_DIR / "crop_model.pkl"))
        print(" Extended model integrated and saved")

    return True


# Train fertilizer model 

def train_fertilizer_model():
    print("\n" + "="*50)
    print("  Training Fertilizer Recommendation Model")
    print("="*50)

    from core.fertilizer_rec import FertilizerRecommender

    if not FERT_CSV.exists():
        print(f" Missing: {FERT_CSV}")
        return False

    rec = FertilizerRecommender()
    t0 = time.time()
    rec.fit(str(FERT_CSV))
    elapsed = time.time() - t0
    print(f" Fertilizer model trained in {elapsed:.1f}s")
    return True


# Main 
if __name__ == "__main__":
    print("\n CropSeek LLM — Model Training")
    print("="*50)

    # Download datasets
    print("\n Checking datasets...")
    download_if_missing(CROP_URL, CROP_CSV)
    download_if_missing(FERT_URL, FERT_CSV)
    download_if_missing(EXT_URL, EXT_CSV)

    # Train
    crop_ok = train_crop_model()
    fert_ok = train_fertilizer_model()

    print("\n" + "="*50)
    print("  Training Summary")
    print("="*50)
    print(f"  Crop model:       {'Done' if crop_ok else ' Failed'}")
    print(f"  Fertilizer model: {' Done' if fert_ok else ' Failed'}")
    print(f"  Disease model:  Train separately (see scripts/train_disease_model.py)")
    print("\n  Run the server: python main.py")
    print("="*50)
