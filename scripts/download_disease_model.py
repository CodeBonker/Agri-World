"""
scripts/download_disease_model.py
Downloads the pre-trained MobileNetV2 plant disease model from HuggingFace.

Model: Daksh159/plant-disease-mobilenetv2
  - Architecture: MobileNetV2
  - Classes: 38 (PlantVillage)
  - Accuracy: ~95%
  - Size: ~9.3 MB

Usage:
    python scripts/download_disease_model.py
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)
DEST = MODEL_DIR / "disease_model.pth"


def download():
    if DEST.exists():
        print(f" Model already exists at {DEST} ({round(DEST.stat().st_size / 1e6, 1)} MB)")
        return

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("Installing huggingface_hub...")
        os.system(f"{sys.executable} -m pip install huggingface_hub -q")
        from huggingface_hub import hf_hub_download

    print("⬇️  Downloading MobileNetV2 plant disease model (~9.3 MB)...")
    path = hf_hub_download(
        repo_id="Daksh159/plant-disease-mobilenetv2",
        filename="mobilenetv2_plant.pth",
        local_dir="/tmp/hf_disease",
    )
    import shutil
    shutil.copy(path, DEST)
    print(f"Saved to {DEST} ({round(DEST.stat().st_size / 1e6, 1)} MB)")


if __name__ == "__main__":
    download()
