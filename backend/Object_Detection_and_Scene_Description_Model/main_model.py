from .models import Yolo_Model_Output
from ultralytics import YOLO

def object_detection_and_results(imageFrame, model: YOLO):
    results = model.predict(imageFrame, imgsz=640, conf=0.25, verbose=False)
    detections = []

    for r in results:
        for box in r.boxes:
            xyxy = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            classname = model.names[cls]

            detections.append(
                Yolo_Model_Output(
                    xyxy=xyxy,
                    conf=conf,
                    objClass=classname,
                    classIndex=cls
                )
            )
    return detections
