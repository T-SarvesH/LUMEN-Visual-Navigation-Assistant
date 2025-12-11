import os
import cv2
import json
import time
import numpy as np
from ultralytics import YOLO
from .router import RouterModel
from .config import YOLO_MODELS, YOLO_CONF, YOLO_IMGSZ, ROUTER_INTERVAL, TORCH_DEVICE
from .threat_detection import ThreatAnalyzer


class InferenceManager:
    """
    Router → YOLO → Threat Analyzer pipeline
    + Scene description (15-sec window)
    + Threat JSON writer
    """

    def __init__(self):
        print("Initializing Router + YOLO Inference Pipeline...")
        self.router = RouterModel()
        self.threat_analyzer = ThreatAnalyzer()

        self.frame_count = 0
        self.active_classes = []
        self.yolo_models = {}

        # -----------------------------
        # Scene Description Aggregation
        # -----------------------------
        self.scene_objects = {}         # class_name → track info
        self.window_frames = 0          # counter for 15s window
        self.fps_estimate = 30          # used to approximate 15s
        self.window_size = self.fps_estimate * 15

        print("Inference Manager Ready.")

    # --------------------------------------
    # Lazy-load YOLO model for a class
    # --------------------------------------
    def load_yolo_model(self, category):
        if category not in self.yolo_models:
            if category not in YOLO_MODELS:
                print(f"No YOLO model mapped for class: {category}")
                return None

            model_path = YOLO_MODELS[category]
            if not os.path.exists(model_path):
                print(f"YOLO model path not found: {model_path}")
                return None

            print(f"Loading YOLO model for '{category}' from {model_path} ...")
            self.yolo_models[category] = YOLO(model_path).to(TORCH_DEVICE)

        return self.yolo_models[category]

    # --------------------------------------
    # Run router every N frames
    # --------------------------------------
    def run_router(self, frame):
        if self.frame_count % ROUTER_INTERVAL == 0:
            router_out = self.router.predict(frame)
            self.active_classes = router_out["active_classes"]
            self.router_probs = router_out["probabilities"]
            print(f"Active Classes: {self.active_classes}")

        self.frame_count += 1

    # --------------------------------------
    # YOLO inference
    # --------------------------------------
    def run_yolo_inference(self, frame):
        annotated_frame = frame.copy()
        detections = []

        for category in self.active_classes:
            model = self.load_yolo_model(category)
            if model is None:
                continue

            results = model(frame, conf=YOLO_CONF, imgsz=YOLO_IMGSZ, verbose=False)
            annotated_frame = results[0].plot(line_width=2)

            for box in results[0].boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                class_id = int(box.cls[0])
                cls_name = model.names[class_id]

                detections.append({
                    "class": cls_name,
                    "class_id": class_id,
                    "conf": conf,
                    "xyxy": xyxy
                })

        return annotated_frame, detections

    # --------------------------------------
    # Threat Analysis
    # --------------------------------------
    def run_threat_analysis(self, annotated_frame, detections):
        threat_frame, threat_data = self.threat_analyzer.analyze(annotated_frame, detections)

        # Write threat JSON immediately
        self.write_threat_json(threat_data)

        return threat_frame, threat_data

    # ============================================================
    # Scene description aggregation (15-second rolling window)
    # ============================================================
    def update_scene_description(self, detections, threat_data):
        """
        Scene description uses ONLY tracker IDs and tracker bboxes.
        YOLO bbox matching is NOT used.
        """
        ts = time.time()

        # Add/update tracker-derived objects
        for tid, tdata in threat_data.items():
            cls = tdata["object"]
            bbox = tdata["bbox-coords"]
            conf = tdata["confidence"]

            if cls not in self.scene_objects:
                self.scene_objects[cls] = {"track_ids": {}}

            self.scene_objects[cls]["track_ids"][str(tid)] = {
                "bbox": bbox,
                "conf": conf,
                "last_seen": ts
            }

        # Remove stale items older than 15 seconds
        expire_ts = ts - 15

        for cls in list(self.scene_objects.keys()):
            for tid in list(self.scene_objects[cls]["track_ids"].keys()):
                if self.scene_objects[cls]["track_ids"][tid]["last_seen"] < expire_ts:
                    del self.scene_objects[cls]["track_ids"][tid]

            if len(self.scene_objects[cls]["track_ids"]) == 0:
                del self.scene_objects[cls]

        # Write JSON every window
        self.window_frames += 1
        if self.window_frames >= self.window_size:
            self.write_scene_json()
            self.window_frames = 0


    # --------------------------------------
    # JSON Writers
    # --------------------------------------
    def write_scene_json(self):
        path = os.path.join(os.path.dirname(__file__), "scene_description.json")
        with open(path, "w") as f:
            json.dump(self.scene_objects, f, indent=4)

    def write_threat_json(self, threat_data):
        path = os.path.join(os.path.dirname(__file__), "threats.json")
        with open(path, "w") as f:
            json.dump(threat_data, f, indent=4)

    # --------------------------------------
    # Full frame pipeline
    # --------------------------------------
    def process_frame(self, frame, return_info=False):
        self.run_router(frame)

        annotated, detections = self.run_yolo_inference(frame)

        threat_annotated, threat_data = self.run_threat_analysis(annotated, detections)

        # Scene JSON update (15s window)
        self.update_scene_description(detections, threat_data)

        h, w = frame.shape[:2]
        final_frame = cv2.resize(threat_annotated, (w, h))

        if return_info:
            router_probs = getattr(self, "router_probs", {})
            return final_frame, router_probs, self.active_classes, detections, threat_data
        else:
            return final_frame

# =====================================================
# 🎬 Standalone VIDEO inference test (Router + YOLO + Threat Analysis)
# =====================================================
if __name__ == "__main__":
    print("__ Running standalone VIDEO inference test...")
    manager = InferenceManager()

    # Load video
    video_path = os.path.join(os.path.dirname(__file__), "TestingVid(Trimmed).mp4")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"❌ Video not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_path = f"{os.path.dirname(__file__)}/TestingVid_Annotated.mp4"
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    frame_count = 0
    print("__ Processing video ...\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            annotated, router_probs, active_classes, detections, threat_data = manager.process_frame(
                frame, return_info=True
            )

            print(f"\n🟢 Frame {frame_count+1}")

            print("Router Probabilities:")
            for cls, prob in router_probs.items():
                print(f"  - {cls:<24}: {prob:.4f}")

            print(f"Active YOLO Models: {active_classes}")

            if detections:
                print("\nDetected Objects:")
                for det in detections:
                    print(f"  • {det['class']:<15} (conf {det['conf']:.2f}) at {list(map(int, det['xyxy']))}")
            else:
                print("No objects detected.")

            if threat_data:
                print("\n⚠️ Threat Scores:")
                sorted_threats = sorted(threat_data.items(), key=lambda x: x[1]["threat_score"], reverse=True)
                for tid, t in sorted_threats[:]:
                    print(f"  ID:{tid:<3} | {t['object']:<10} | Conf:{t['confidence']:.2f} | "
                          f"T:{t['threat_score']:.2f} | P:{t['proximity']:.2f} | "
                          f"A:{t['anomaly']:.2f} | L:{t['looming']:.2f} | b-coords: {t['bbox-coords']}")
            else:
                print("No threats detected.")

            out.write(annotated)
            frame_count += 1

    except KeyboardInterrupt:
        pass

    cap.release()
    out.release()
    print(f"\n✅ Saved annotated video at: {output_path}")