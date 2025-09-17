from ultralytics import YOLO

model = YOLO('yolo11n.pt')
model.train(data='coco128.yaml', epochs=50, imgsz=512, device=0, half=True, batch=8)