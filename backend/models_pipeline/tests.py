import os
import cv2
import json
import time
import numpy as np
import threading
from dotenv import load_dotenv
from ultralytics import YOLO
from .router import RouterModel
from .config import YOLO_MODELS, YOLO_CONF, YOLO_IMGSZ, ROUTER_INTERVAL, TORCH_DEVICE
from .threat_detection import ThreatAnalyzer
from Scene_Description_Module.narrator import NarratorBot
from Scene_Description_Module.scenary_manager import SceneryManager
from warnings import filterwarnings

filterwarnings('ignore')
load_dotenv()

class InferenceManager:
    def __init__(self):
        print("Initializing Router + YOLO Inference Pipeline...")
        self.router = RouterModel()
        self.threat_analyzer = ThreatAnalyzer()
        self.narrator = NarratorBot()
        
        # Isolated Scenery Manager (Optimization 2)
        self.scenery_mgr = SceneryManager(interval=30, frame_w=1280, frame_h=720)
        
        # Output directory for video only
        self.results_dir = os.path.join(".", "models_pipeline", "testing-results")
        os.makedirs(self.results_dir, exist_ok=True)

        self.frame_count = 0
        self.active_classes = []
        self.yolo_models = {}
        self.fps_estimate = 30 
        self.window_frames = 0
        self.window_size = self.fps_estimate * 30

        print("Inference Manager Ready.")

    def load_yolo_model(self, category):
        if category not in self.yolo_models:
            if category not in YOLO_MODELS: return None
            model_path = YOLO_MODELS[category]
            if not os.path.exists(model_path): return None
            self.yolo_models[category] = YOLO(model_path).to(TORCH_DEVICE)
        return self.yolo_models[category]

    def run_router(self, frame):
        if self.frame_count % ROUTER_INTERVAL == 0:
            router_out = self.router.predict(frame)
            self.active_classes = router_out["active_classes"]
            self.router_probs = router_out["probabilities"]
        self.frame_count += 1

    def run_yolo_inference(self, frame):
        annotated_frame = frame.copy()
        detections = []
        for category in self.active_classes:
            model = self.load_yolo_model(category)
            if model is None: continue
            results = model(frame, conf=YOLO_CONF, imgsz=YOLO_IMGSZ, verbose=False)
            annotated_frame = results[0].plot(line_width=2)
            for box in results[0].boxes:
                detections.append({
                    "class": model.names[int(box.cls[0])],
                    "class_id": int(box.cls[0]),
                    "conf": float(box.conf[0]),
                    "xyxy": box.xyxy[0].tolist()
                })
        return annotated_frame, detections

    def run_threat_analysis(self, annotated_frame, detections):
        threat_frame, threat_data = self.threat_analyzer.analyze(annotated_frame, detections)
        self.write_threat_json(threat_data)
        return threat_frame, threat_data

    def update_scene_description(self, threat_data):
        """
        Hard Latch: Only activates on the 900-frame window (every 30 seconds).
        Priority overrides have been removed.
        """
        # --- FIXED: Strict 30-Second Window Latch ---
        # 900 frames / 30 fps = 30 seconds
        if self.frame_count % 900 != 0:
            return

        # Prepare pseudo-tracks for SceneryManager
        pseudo_tracks = []
        for tid, t in threat_data.items():
            x1, y1, x2, y2 = t["bbox-coords"]
            # Clean name for consistency (Lowercase + Stripped)
            clean_name = str(t["object"]).lower().strip()
            pseudo_tracks.append([x1, y1, x2, y2, tid, t["confidence"], clean_name])

        # Generate JSON - Priority override is now permanently False
        scene_json = self.scenery_mgr.generate_refined_json(pseudo_tracks, {}, priority_override=False)

        if scene_json:
            self.write_scene_json(scene_json)
            ts_str = f"{int((self.frame_count/self.fps_estimate)//60):02d}:{int((self.frame_count/self.fps_estimate)%60):02d}"
            
            # Pass the scene_json dictionary directly to the thread
            thread = threading.Thread(target=self.run_async_narration, args=(scene_json, ts_str), daemon=True)
            thread.start()
        

    def run_async_narration(self, scene_data, timestamp_str):
        try:
            # The NarratorBot now performs Rule-Based NL + LLM Refinement internally
            narration = self.narrator.generate_narration(scene_data)
            if narration:
                log_entry = f"[{timestamp_str}] {narration}"
                log_path = os.path.join(os.path.dirname(__file__), "narrations_log(Refined).txt")
                
                # Feedback to console for monitoring
                print(f"\n🗣️ LUMEN [{timestamp_str}]: {narration}\n")
                
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
        except Exception as e:
            print(f"Async Narrator Failed: {e}")

    def write_scene_json(self, scene_objects):
        path = os.path.join(os.path.dirname(__file__), "scene_description.json")
        with open(path, "w") as f:
            json.dump(scene_objects, f, indent=4)

    def write_threat_json(self, threat_data):
        path = os.path.join(os.path.dirname(__file__), "threats.json")
        with open(path, "w") as f:
            json.dump(threat_data, f, indent=4)

    def process_frame(self, frame, return_info=False):
        self.run_router(frame)
        annotated, detections = self.run_yolo_inference(frame)
        threat_annotated, threat_data = self.run_threat_analysis(annotated, detections)
        self.update_scene_description(threat_data)
        if return_info:
            return threat_annotated, getattr(self, "router_probs", {}), self.active_classes, detections, threat_data
        return threat_annotated

if __name__ == "__main__":
    manager = InferenceManager()
    video_path = os.path.join(os.path.dirname(__file__), "TestingVid(Trimmed).mp4")
    cap = cv2.VideoCapture(video_path)
    
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # OUTPUT VIDEO DIRECTED TO testing-results
    output_path = os.path.join(manager.results_dir, "TestingVid_Annotated_and_Refined.mp4")
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    MAX_FRAMES = 8100
    frame_count = 0

    try:
        while frame_count < MAX_FRAMES:
            ret, frame = cap.read()
            if not ret: break
            annotated, router_probs, active_classes, detections, threat_data = manager.process_frame(frame, return_info=True)
            out.write(annotated)
            frame_count += 1
            print(f"Processed Frame {frame_count}/{MAX_FRAMES}", end="\r")
    finally:
        cap.release()
        out.release()
        print(f"\n✅ Video saved at: {output_path}")