from ultralytics import YOLO
import os

# Make results folder
save_dir = "yolo11m_results"
os.makedirs(save_dir, exist_ok=True)

# Load YOLOv11 model
model = YOLO("yolo11m.pt")  # pretrained weights, or use .yaml for training from scratch

# Train on GPU (device='0' = first CUDA GPU, '0,1' = multi-GPU, 'cpu' = CPU only)
results = model.train(
    data="coco8.yaml",        # dataset config
    epochs=100,               # number of epochs
    imgsz=640,               # image size
    project=save_dir,        # results directory
    name="coco_exp",        # experiment name
    device="0",          # use CUDA GPU 0
    amp=True,
)