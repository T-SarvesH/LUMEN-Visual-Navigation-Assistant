
from ultralytics import YOLO
import cv2
import os

results = YOLO('/home/sarvesh/LUMEN-Visual-Navigation-Assistant/collab-model-training/yolo11m_results/coco_exp/weights/best.pt', task='detect')
result = results.predict('TestImage.jpeg', conf=0.3, imgsz=640)

#result[0].show()

path = 'outputs/'
os.makedirs(path, exist_ok=True)
cv2.imwrite(path + 'ModelOutput.png', result[0].plot())