"""
core/disease_detector.py
Plant disease detection using a PyTorch CNN (ResNet-based).

Supports:
  - File path input
  - Base64 encoded image input
  - 38 disease classes across multiple crops

The model.pth file must be trained separately (see scripts/train_disease_model.py).
If the model is not available, returns a graceful error.
"""

import os
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models"


# Disease class labels (PlantVillage 38-class)


DISEASE_CLASSES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]

# Treatment recommendations per disease
TREATMENT_MAP = {
    "Apple_scab": [
        "Apply fungicides containing captan or myclobutanil.",
        "Remove and destroy infected leaves.",
        "Ensure good air circulation by pruning.",
    ],
    "Black_rot": [
        "Remove mummified fruits and infected wood.",
        "Apply copper-based fungicides.",
        "Avoid overhead irrigation.",
    ],
    "Cedar_apple_rust": [
        "Apply fungicides at bud break.",
        "Remove nearby cedar/juniper trees if possible.",
        "Use resistant apple varieties.",
    ],
    "Powdery_mildew": [
        "Apply sulfur-based or potassium bicarbonate fungicides.",
        "Improve air circulation.",
        "Avoid excess nitrogen fertilization.",
    ],
    "Cercospora_leaf_spot": [
        "Apply fungicides containing azoxystrobin.",
        "Rotate crops to break disease cycle.",
        "Remove crop debris after harvest.",
    ],
    "Common_rust": [
        "Apply fungicides at first sign of rust.",
        "Plant resistant hybrids.",
        "Monitor fields regularly.",
    ],
    "Northern_Leaf_Blight": [
        "Apply fungicides containing propiconazole.",
        "Use resistant corn hybrids.",
        "Rotate crops with non-host plants.",
    ],
    "Esca_(Black_Measles)": [
        "Prune infected wood during dry weather.",
        "Apply wound sealants after pruning.",
        "Avoid water stress.",
    ],
    "Leaf_blight": [
        "Apply copper-based fungicides.",
        "Remove infected plant material.",
        "Improve drainage.",
    ],
    "Haunglongbing": [
        "Remove and destroy infected trees immediately.",
        "Control Asian citrus psyllid vector.",
        "Use certified disease-free planting material.",
    ],
    "Bacterial_spot": [
        "Apply copper-based bactericides.",
        "Avoid overhead irrigation.",
        "Use disease-free seeds.",
    ],
    "Early_blight": [
        "Apply fungicides containing chlorothalonil or mancozeb.",
        "Remove lower infected leaves.",
        "Maintain proper plant spacing.",
    ],
    "Late_blight": [
        "Apply fungicides containing metalaxyl immediately.",
        "Remove and destroy infected plants.",
        "Avoid overhead watering.",
    ],
    "Leaf_Mold": [
        "Improve greenhouse ventilation.",
        "Apply fungicides containing chlorothalonil.",
        "Reduce humidity levels.",
    ],
    "Septoria_leaf_spot": [
        "Apply fungicides at first sign of disease.",
        "Remove infected lower leaves.",
        "Avoid working in wet fields.",
    ],
    "Spider_mites": [
        "Apply miticides or insecticidal soap.",
        "Increase humidity around plants.",
        "Introduce predatory mites.",
    ],
    "Target_Spot": [
        "Apply fungicides containing azoxystrobin.",
        "Improve air circulation.",
        "Remove infected plant debris.",
    ],
    "Yellow_Leaf_Curl_Virus": [
        "Control whitefly vectors with insecticides.",
        "Use reflective mulches to deter whiteflies.",
        "Remove and destroy infected plants.",
    ],
    "mosaic_virus": [
        "Remove and destroy infected plants.",
        "Control aphid vectors.",
        "Use virus-free seeds.",
    ],
    "Leaf_scorch": [
        "Apply fungicides containing captan.",
        "Remove infected leaves.",
        "Avoid overhead irrigation.",
    ],
    "healthy": [
        "Plant looks healthy! Continue regular monitoring.",
        "Maintain proper irrigation and fertilization.",
        "Scout for pests and diseases weekly.",
    ],
}

DEFAULT_TREATMENT = [
    "Consult your local agricultural extension officer.",
    "Apply appropriate fungicide/bactericide based on diagnosis.",
    "Remove and destroy severely infected plant material.",
]


def _get_treatment(disease_label: str) -> list:
    """Match disease label to treatment recommendations."""
    label_lower = disease_label.lower()
    for key, treatments in TREATMENT_MAP.items():
        if key.lower().replace("_", " ") in label_lower.replace("_", " "):
            return treatments
    return DEFAULT_TREATMENT


def _severity_from_confidence(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    elif confidence >= 0.60:
        return "moderate"
    return "low"


class DiseaseDetector:
    """
    Plant disease detector using a pre-trained MobileNetV2 model.
    Model source: https://huggingface.co/Daksh159/plant-disease-mobilenetv2
    Architecture: MobileNetV2 with custom classifier head (38 classes)
    Accuracy: ~95% on PlantVillage augmented dataset
    """

    MODEL_PATH = str(MODEL_DIR / "disease_model.pth")
    IMG_SIZE = 224

    def __init__(self):
        self.model = None
        self.is_loaded = False
        self.num_classes = len(DISEASE_CLASSES)
        self.device = None

    def load(self) -> "DiseaseDetector":
        """Load the MobileNetV2 plant disease model."""
        try:
            import torch
            import torch.nn as nn
            import torchvision.models as models

            if not os.path.exists(self.MODEL_PATH):
                raise FileNotFoundError(
                    f"Disease model not found at {self.MODEL_PATH}. "
                    "Run: python scripts/download_disease_model.py"
                )

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            # Build MobileNetV2 with the exact same head used during training:
            #   model.classifier[1] = nn.Sequential(
            #       nn.Dropout(0.2),
            #       nn.Linear(1280, 38)
            #   )
            model = models.mobilenet_v2(weights=None)
            model.classifier[1] = nn.Sequential(
                nn.Dropout(0.2),
                nn.Linear(model.classifier[1].in_features, self.num_classes),
            )

            state = torch.load(self.MODEL_PATH, map_location=device)

            # Handle wrapped checkpoints gracefully
            if isinstance(state, dict) and "model_state_dict" in state:
                state = state["model_state_dict"]
            elif isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]

            model.load_state_dict(state)
            model.to(device)
            model.eval()

            self.model = model
            self.device = device
            self.is_loaded = True
            logger.info(f" Disease model (MobileNetV2) loaded from {self.MODEL_PATH}")
            return self

        except Exception as e:
            logger.warning(f"Disease model load failed: {e}")
            raise

    def _preprocess(self, image):
        """Preprocess a PIL image for inference."""
        import torchvision.transforms as transforms
        transform = transforms.Compose([
            transforms.Resize((self.IMG_SIZE, self.IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        return transform(image).unsqueeze(0)

    def _load_image(self, image_path: Optional[str] = None, image_base64: Optional[str] = None):
        """Load image from path or base64 string."""
        from PIL import Image
        if image_path:
            return Image.open(image_path).convert("RGB")
        elif image_base64:
            # Strip data URI prefix if present
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            img_bytes = base64.b64decode(image_base64)
            return Image.open(BytesIO(img_bytes)).convert("RGB")
        raise ValueError("Either image_path or image_base64 must be provided.")

    def predict(self, image_path: Optional[str] = None, image_base64: Optional[str] = None) -> dict:
        """Run inference and return structured result."""
        try:
            import torch
            import torch.nn.functional as F

            if not self.is_loaded:
                raise RuntimeError("Model not loaded. Call load() first.")

            image = self._load_image(image_path, image_base64)
            tensor = self._preprocess(image).to(self.device)

            with torch.no_grad():
                logits = self.model(tensor)
                probs = F.softmax(logits, dim=1)[0]

            top_indices = torch.argsort(probs, descending=True)[:3].tolist()
            top3 = [
                {
                    "class": DISEASE_CLASSES[i],
                    "disease": DISEASE_CLASSES[i].replace("___", " - ").replace("_", " "),
                    "confidence": round(float(probs[i]), 4),
                }
                for i in top_indices
            ]

            primary_label = DISEASE_CLASSES[top_indices[0]]
            confidence = float(probs[top_indices[0]])

            # Parse crop and disease from label
            parts = primary_label.split("___")
            crop = parts[0].replace("_", " ") if len(parts) > 0 else "Unknown"
            disease_name = parts[1].replace("_", " ") if len(parts) > 1 else primary_label

            is_healthy = "healthy" in primary_label.lower()
            severity = "none" if is_healthy else _severity_from_confidence(confidence)
            treatments = _get_treatment(primary_label)

            return {
                "type": "disease_detection",
                "success": True,
                "primary_disease": primary_label,
                "crop": crop,
                "disease_name": disease_name,
                "confidence": round(confidence, 4),
                "is_healthy": is_healthy,
                "severity": severity,
                "treatment_recommendations": treatments,
                "top_3": top3,
            }

        except Exception as e:
            logger.exception("Disease prediction failed")
            return {"type": "disease_detection", "success": False, "error": str(e)}
