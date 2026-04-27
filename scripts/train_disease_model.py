"""
scripts/train_disease_model.py
Train a ResNet18-based plant disease classifier on the PlantVillage dataset.

Dataset: PlantVillage (38 classes)
Download from: https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset

Usage:
    python scripts/train_disease_model.py --data_dir /path/to/PlantVillage --epochs 20

The trained model is saved to: models/disease_model.pth
"""

import argparse
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

from core.disease_detector import DISEASE_CLASSES


def train(data_dir: str, epochs: int = 20, batch_size: int = 32, lr: float = 1e-4):
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader
        from torchvision import datasets, models, transforms
    except ImportError:
        print(" PyTorch not installed. Run: pip install torch torchvision")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    #  Data transforms 
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Load dataset 
    print(f"  Loading dataset from: {data_dir}")
    full_dataset = datasets.ImageFolder(data_dir, transform=train_transform)
    n_classes = len(full_dataset.classes)
    print(f"  Classes found: {n_classes}")
    print(f"  Total images:  {len(full_dataset)}")

    # 80/20 split
    n_train = int(0.8 * len(full_dataset))
    n_val = len(full_dataset) - n_train
    train_ds, val_ds = torch.utils.data.random_split(full_dataset, [n_train, n_val])
    val_ds.dataset.transform = val_transform

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)

    # Model 
    model = models.resnet18(pretrained=True)
    model.fc = nn.Linear(model.fc.in_features, n_classes)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.1)

    best_val_acc = 0.0
    save_path = str(MODEL_DIR / "disease_model.pth")

    # Training loop 
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        t0 = time.time()

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total += labels.size(0)

        train_acc = correct / total
        train_loss = running_loss / total

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = outputs.max(1)
                val_correct += predicted.eq(labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / val_total
        elapsed = time.time() - t0

        print(f"  Epoch {epoch:2d}/{epochs} | Loss: {train_loss:.4f} | Train: {train_acc:.4f} | Val: {val_acc:.4f} | {elapsed:.1f}s")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), save_path)
            print(f"    Best model saved (val_acc={val_acc:.4f})")

        scheduler.step()

    print(f"\n  Training complete. Best val accuracy: {best_val_acc:.4f}")
    print(f"  Model saved to: {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train plant disease classifier")
    parser.add_argument("--data_dir", type=str, required=True, help="Path to PlantVillage dataset directory")
    parser.add_argument("--epochs",   type=int, default=20,   help="Number of training epochs")
    parser.add_argument("--batch",    type=int, default=32,   help="Batch size")
    parser.add_argument("--lr",       type=float, default=1e-4, help="Learning rate")
    args = parser.parse_args()

    print("\n Plant Disease Model Training")
    print("="*50)
    train(args.data_dir, args.epochs, args.batch, args.lr)
