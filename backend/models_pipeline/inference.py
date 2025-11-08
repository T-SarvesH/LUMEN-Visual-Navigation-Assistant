import os
import cv2
import numpy as np
from ultralytics import YOLO
from .router import RouterModel
from .config import YOLO_MODELS, YOLO_CONF, YOLO_IMGSZ, ROUTER_INTERVAL, TORCH_DEVICE
from .threat_detection import ThreatAnalyzer


class InferenceManager:
    """
    Central pipeline managing:
    - Router classification (EfficientNet)
    - YOLO object detection (class-specific)
    - Threat analysis (trajectory + motion)
    """

    def __init__(self):
        print("🧠 Initializing Router + YOLO Inference Pipeline...")
        self.router = RouterModel()
        self.threat_analyzer = ThreatAnalyzer()
        self.frame_count = 0
        self.active_classes = []
        self.yolo_models = {}
        print("✅ Inference Manager Ready.")

    # ------------------------------
    # 1️⃣ Lazy-load YOLO models
    # ------------------------------
    def load_yolo_model(self, category):
        """Load YOLO model only when required."""
        if category not in self.yolo_models:
            if category not in YOLO_MODELS:
                print(f"⚠️ No YOLO model mapped for class: {category}")
                return None
            model_path = YOLO_MODELS[category]
            if not os.path.exists(model_path):
                print(f"❌ YOLO model path not found: {model_path}")
                return None

            print(f"📦 Loading YOLO model for '{category}' from {model_path} ...")
            self.yolo_models[category] = YOLO(model_path).to(TORCH_DEVICE)

        return self.yolo_models[category]

    # ------------------------------
    # 2️⃣ Run router periodically
    # ------------------------------
    def run_router(self, frame):
        """Run EfficientNet router every N frames."""
        if self.frame_count % ROUTER_INTERVAL == 0:
            router_out = self.router.predict(frame)
            self.active_classes = router_out["active_classes"]
            self.router_probs = router_out["probabilities"]
            print(f"🎯 Active Classes: {self.active_classes}")
        self.frame_count += 1

    # ------------------------------
    # 3️⃣ YOLO inference
    # ------------------------------
    def run_yolo_inference(self, frame):
        """Run YOLO on active classes, gather detections."""
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
                    "class_id": class_id,
                    "class": cls_name,
                    "conf": conf,
                    "xyxy": xyxy
                })

        return annotated_frame, detections

    # ------------------------------
    # 4️⃣ Threat Analysis
    # ------------------------------
    def run_threat_analysis(self, annotated_frame, detections):
        """Pass YOLO detections to ThreatAnalyzer."""
        threat_frame, threat_data = self.threat_analyzer.analyze(annotated_frame, detections)
        return threat_frame, threat_data

    # ------------------------------
    # 5️⃣ Full frame pipeline
    # ------------------------------
    def process_frame(self, frame, return_info=False):
        """
        Runs the router → YOLO(s) → threat analysis in sequence.
        If return_info=True, also returns router probabilities, active classes,
        detections, and threat data.
        """
        # Step 1: Router
        self.run_router(frame)

        # Step 2: YOLO inference
        annotated, detections = self.run_yolo_inference(frame)

        # Step 3: Threat detection overlay
        threat_annotated, threat_data = self.run_threat_analysis(annotated, detections)

        # Step 4: Resize output for consistency
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
    from models_pipeline.router import RouterModel
    from models_pipeline.config import BASE_MODELS_DIR

    print("__ Running standalone VIDEO inference test...")
    print("__ Initializing Router + YOLO + Threat Analyzer Pipeline...")

    manager = InferenceManager()

    # ==============================
    # 📹 Load fixed test video
    # ==============================
    video_path = os.path.join(os.path.dirname(__file__), "Inference_Testing.mp4")
    if not os.path.exists(video_path):
        raise FileNotFoundError(
            f"❌ Test video not found at {video_path}\n"
            f"Please place your test video as 'Inference_Testing.mp4' inside this directory.\n"
        )

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"__ Loaded video: {video_path}")
    print(f"__ Resolution: {width}x{height}, FPS: {fps}\n")

    # ==============================
    # 🎞 Output Setup
    # ==============================
    output_path = f"{os.path.dirname(__file__)}/Inference_Testing_Annotated.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    print("__ Processing video (press Ctrl+C to stop early)...\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Full inference pipeline (with all info)
            annotated, router_probs, active_classes, detections, threat_data = manager.process_frame(
                frame, return_info=True
            )

            # ==============================
            # 🔍 Logs
            # ==============================
            print(f"\n🟢 Frame {frame_count + 1}")
            print("Router Probabilities:")
            for cls_name, prob in router_probs.items():
                print(f"  - {cls_name:<24}: {prob:.4f}")

            print(f"Active YOLO Models: {active_classes if active_classes else 'None'}")

            if detections:
                print("\nDetected Objects:")
                for det in detections:
                    cls = det["class"]
                    conf = det["conf"]
                    xyxy = list(map(int, det["xyxy"]))
                    print(f"  • {cls:<15} (conf: {conf:.2f}) at {xyxy}")
            else:
                print("No objects detected.")

            # Print Threat Scores
            if threat_data:
                print("\n⚠️ Threat Scores:")
                top_threats = sorted(threat_data.items(), key=lambda x: x[1]["threat_score"], reverse=True)[:3]
                for tid, data in top_threats:
                    print(f"  ID:{tid:<4} | {data['object']:<12} | Conf:{data['confidence']:.2f} | "
                          f"T:{data['threat_score']:.2f} | P:{data['proximity']:.2f} | "
                          f"A:{data['anomaly']:.2f} | L:{data['looming']:.2f}")
            else:
                print("No threats detected in this frame.")

            # ==============================
            # 💾 Write annotated frame
            # ==============================
            out.write(annotated)
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"__ Processed {frame_count} frames...")

        cap.release()
        out.release()
        print(f"\n✅ Annotated video saved at: {output_path}")

    except KeyboardInterrupt:
        cap.release()
        out.release()
        print("\n⏹ Interrupted by user. Video processing stopped.")