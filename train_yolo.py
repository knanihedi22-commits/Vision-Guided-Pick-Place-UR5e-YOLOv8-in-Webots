from ultralytics import YOLO
from pathlib import Path
import torch

# Check if CUDA is available
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")

# Load a pretrained YOLOv8 model
# Options: yolov8n.pt (nano), yolov8s.pt (small), yolov8m.pt (medium), yolov8l.pt (large), yolov8x.pt (xlarge)
model = YOLO('yolov8n.pt')  # Start with nano model for faster training

# Path to dataset configuration
data_yaml = '/home/wassim/Projects/controllers/data/yolo_dataset/data.yaml'

# Training parameters
train_params = {
    'data': data_yaml,
    'epochs': 100,              # Number of training epochs
    'imgsz': 640,               # Image size
    'batch': 16,                # Batch size (adjust based on GPU memory)
    'device': device,
    'workers': 4,               # Number of workers for data loading
    'patience': 20,             # Early stopping patience
    'save': True,               # Save checkpoints
    'project': 'runs/train',    # Project directory
    'name': 'object_detection', # Experiment name
    'exist_ok': True,           # Overwrite existing experiment
    'pretrained': True,         # Use pretrained weights
    'optimizer': 'Adam',        # Optimizer (SGD, Adam, AdamW)
    'lr0': 0.01,               # Initial learning rate
    'lrf': 0.01,               # Final learning rate (lr0 * lrf)
    'momentum': 0.937,         # Momentum
    'weight_decay': 0.0005,    # Weight decay
    'warmup_epochs': 3,        # Warmup epochs
    'warmup_momentum': 0.8,    # Warmup momentum
    'box': 7.5,                # Box loss gain
    'cls': 0.5,                # Class loss gain
    'dfl': 1.5,                # DFL loss gain
    'plots': True,             # Generate plots
    'val': True,               # Validate during training
}

print("\nStarting training...")
print(f"Configuration: {train_params}\n")

# Train the model
results = model.train(**train_params)

print("\nTraining complete!")
print(f"Results saved to: {results.save_dir}")

# Evaluate the model on validation set
print("\nEvaluating model...")
metrics = model.val()

print(f"\nValidation Metrics:")
print(f"mAP50: {metrics.box.map50:.4f}")
print(f"mAP50-95: {metrics.box.map:.4f}")

# Export the trained model
print("\nExporting model...")
model.export(format='onnx')  # Export to ONNX format
print("Model exported successfully!")