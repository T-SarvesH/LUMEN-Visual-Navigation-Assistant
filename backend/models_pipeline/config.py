# models_pipeline/config.py
import os

# BASE directory where collab-model-training is located (Updated to match project structure)
BASE_MODELS_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 
    "../../collab-model-training"
))

# EfficientNet router model (update filename if you saved differently)
ROUTER_MODEL_PATH = os.path.join(
    BASE_MODELS_DIR,
    "EfficientNet-Router-Model/trained_models/efficientnetv2b3_finetuned_model(v1).h5"
)

# Router settings
ROUTER_INTERVAL = 5            # run router every N frames (default 5)
ROUTER_THRESHOLD = 0.25         # probability threshold for marking class active

# Per-frame YOLO configs (confidence & image size)
YOLO_CONF = 0.25
YOLO_IMGSZ = 640
IMG_SIZE = 300

# YOLO specialized models mapping — update paths if your weights are elsewhere
YOLO_MODELS = {
    "Animal": os.path.join(BASE_MODELS_DIR, "Animal_Detection_Lumen/Version1-Results/train/weights/best.pt"),
    "Vehicle": os.path.join(BASE_MODELS_DIR, "Vehicle_Detection_Lumen/Version-2/best.pt"),
    "Pedestrian": os.path.join(BASE_MODELS_DIR, "Pedestrian_Detection_Lumen/yolo11_custom2/weights/best.pt"),
    "Environmental_Hazard": os.path.join(BASE_MODELS_DIR, "Environmental_Hazard_Lumen/Version-2/best.pt"),
}

#A simple check to see whether the model files exist
for name, path in YOLO_MODELS.items():
    if not os.path.exists(path):
        print(f"⚠️ Warning: YOLO model for '{name}' not found at {path}")
if not os.path.exists(ROUTER_MODEL_PATH):
    print(f"⚠️ Router model missing at {ROUTER_MODEL_PATH}")

# Motion detection sensitivity (tune per environment)
MOTION_THRESHOLD = 12.0

# Device config
TORCH_DEVICE = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES", "") != "" or (os.name != "nt" and os.path.exists("/dev/nvidia0")) else "cpu"