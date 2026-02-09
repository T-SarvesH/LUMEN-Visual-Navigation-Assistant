import os
import cv2
import json
import time
import numpy as np
import threading
from typing import Tuple, List, Dict, Any, Optional
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
    """
    Core AI engine for LUMEN. Handles real-time YOLO routing, spatial threat 
    analysis, and asynchronous scene narration.
    """
    def __init__(self):
        print("Initializing LUMEN Inference Core...")
        self.router = RouterModel()
        self.threat_analyzer = ThreatAnalyzer()
        self.narrator = NarratorBot()
        
        # Scenery Manager handles spatial aggregation over time
        self.scenery_mgr = SceneryManager(interval=30, frame_w=1280, frame_h=720)
        
        # Internal State
        self.frame_count = 0
        self.active_classes = []
        self.yolo_models = {}
        
        # --- FIXED: Time-Based Cooldown ---
        self.last_narration_time = time.time()
        self.narration_interval = 30  # Seconds
        self.start_time = time.time()

        # Alert Cooldown State
        self.last_alert_time = 0
        self.alert_cooldown = 4.0

        print("LUMEN Inference Manager Ready.")

    #Update or default to 15s
    def update_narration_interval(self, interval=15):
        self.narration_interval = interval
        
    def load_yolo_model(self, category: str) -> Optional[YOLO]:
        """Lazy-loads YOLO models to optimize VRAM usage."""
        if category not in self.yolo_models:
            if category not in YOLO_MODELS: return None
            model_path = YOLO_MODELS[category]
            if not os.path.exists(model_path): return None
            self.yolo_models[category] = YOLO(model_path).to(TORCH_DEVICE)
        return self.yolo_models[category]

    def _run_router(self, frame: np.ndarray):
        """Updates the active YOLO models based on scene classification."""
        if self.frame_count % ROUTER_INTERVAL == 0:
            router_out = self.router.predict(frame)
            self.active_classes = router_out["active_classes"]
            self.router_probs = router_out["probabilities"]
        self.frame_count += 1

    def _run_yolo_inference(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """Executes detections for all active model categories."""
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

    def update_scene_description(self, threat_data: Dict) -> Optional[str]:
        """
        Evaluates scenery every 30 seconds. Returns skeletal narration immediately
        and triggers LLM refinement in a background thread.
        """
        current_time = time.time()
        
        # Check if 30 seconds have passed since the last narration
        if current_time - self.last_narration_time < self.narration_interval:
            return None

        # Format detections for the SceneryManager temporal buffer
        pseudo_tracks = []
        for tid, t in threat_data.items():
            x1, y1, x2, y2 = t["bbox-coords"]
            clean_name = str(t["object"]).lower().strip()
            pseudo_tracks.append([x1, y1, x2, y2, tid, t["confidence"], clean_name])

        # SceneryManager creates a JSON summary of the last 30s
        scene_json = self.scenery_mgr.generate_refined_json(pseudo_tracks, {}, priority_override=False)

        if scene_json:
            self.last_narration_time = current_time
            elapsed = current_time - self.start_time
            ts_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
            
            # Offload heavy Groq/LLM call to background thread to prevent lag
            threading.Thread(
                target=self._run_async_narration, 
                args=(scene_json, ts_str), 
                daemon=True
            ).start()
            
            # Return Rule-Based NL immediately so the user gets instant feedback
            return self.narrator.generate_rule_based_nl(scene_json)
            
        return None

    def _run_async_narration(self, scene_data: Dict, timestamp_str: str):
        """Internal: Communicates with Groq API for natural language refinement."""
        try:
            narration = self.narrator.generate_narration(scene_data)
            if narration:
                print(f"\n🗣️ LUMEN [{timestamp_str}]: {narration}\n")
                # Log narration locally for hackathon analytics/debugging
                log_path = os.path.join(os.path.dirname(__file__), "narrations_log.txt")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp_str}] {narration}\n")
        except Exception as e:
            print(f"Async Narrator Failed: {e}")

    def check_immediate_threats(self, threat_data) -> Optional[str]:
        """
        Checks for critical threats in real-time.
        Returns a short, urgent warning string if a threat is detected.
        """
        current_time = time.time()
        
        # Don't spam warnings
        if current_time - self.last_alert_time < self.alert_cooldown:
            return None

        critical_threat = self.threat_analyzer.get_critical_threat(threat_data)
        
        if critical_threat:
            self.last_alert_time = current_time
            obj_name = critical_threat["object"]
            # Short, urgent text
            return f"Stop! {obj_name} approaching."
            
        return None
    
    def process_frame(self, frame: np.ndarray, return_info: bool = False) -> Any:
        """
        Primary entry point for the FastAPI/WebSocket server. 
        Processes video frames and generates metadata/narrations.
        """
        self._run_router(frame)
        annotated, detections = self._run_yolo_inference(frame)
        threat_annotated, threat_data = self.threat_analyzer.analyze(annotated, detections)
        
        # Check for periodic narration (30s interval)
        narration = self.update_scene_description(threat_data)

        # Check for CRITICAL Threats (Every Frame)
        # If we have a critical alert, it overrides standard narration in this return
        critical_alert = self.check_immediate_threats(threat_data)
        
        if return_info:
            return {
                "annotated_frame": threat_annotated,
                "router_probs": getattr(self, "router_probs", {}),
                "active_classes": self.active_classes,
                "detections": detections,
                "threat_data": threat_data,
                "narration": narration,
                "critical_alert": critical_alert
            }
        return threat_annotated