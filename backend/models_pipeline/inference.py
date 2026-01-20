import os
import cv2
import json
import time
import numpy as np
import asyncio
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
        # Initializing Router + YOLO Inference Pipeline
        print("Initializing Router + YOLO Inference Pipeline...")
        self.router = RouterModel()
        self.threat_analyzer = ThreatAnalyzer()
        self.narrator = NarratorBot()
        
        # Isolated Scenery Manager for periodic descriptions
        self.scenery_mgr = SceneryManager(interval=30, frame_w=1280, frame_h=720)
        
        # Results directory for internal logging
        self.results_dir = os.path.join(".", "models_pipeline", "testing-results")
        os.makedirs(self.results_dir, exist_ok=True)

        self.frame_count = 0
        self.active_classes = []
        self.yolo_models = {}
        self.fps_estimate = 30 

        print("Inference Manager Ready.")

    def load_yolo_model(self, category):
        if category not in self.yolo_models:
            if category not in YOLO_MODELS: return None
            model_path = YOLO_MODELS[category]
            if not os.path.exists(model_path): return None
            self.yolo_models[category] = YOLO(model_path).to(TORCH_DEVICE)
        return self.yolo_models[category]

    def run_router(self, frame):
        # Runs classification router at set intervals
        if self.frame_count % ROUTER_INTERVAL == 0:
            router_out = self.router.predict(frame)
            self.active_classes = router_out["active_classes"]
            self.router_probs = router_out["probabilities"]
        self.frame_count += 1

    def run_yolo_inference(self, frame):
        # Runs YOLO detection on active categories
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
        # Analyzes objects for immediate spatial threats
        threat_frame, threat_data = self.threat_analyzer.analyze(annotated_frame, detections)
        return threat_frame, threat_data

    def get_scene_description(self, threat_data):
        # Logic for periodic scene narration
        # Interval is managed by the websocket server or frame count
        pseudo_tracks = []
        for tid, t in threat_data.items():
            x1, y1, x2, y2 = t["bbox-coords"]
            clean_name = str(t["object"]).lower().strip()
            pseudo_tracks.append([x1, y1, x2, y2, tid, t["confidence"], clean_name])

        # Generate refined scene data
        scene_json = self.scenery_mgr.generate_refined_json(pseudo_tracks, {}, priority_override=False)
        
        if scene_json:
            # Generate the natural language narration
            return self.narrator.generate_narration(scene_json)
        return None

    def process_frame(self, frame, return_info=False):
        # Unified processing entry point for WebSocket server
        self.run_router(frame)
        annotated, detections = self.run_yolo_inference(frame)
        threat_annotated, threat_data = self.run_threat_analysis(annotated, detections)
        
        if return_info:
            # Returning full metadata for WebSocket DataChannel usage
            return threat_annotated, getattr(self, "router_probs", {}), self.active_classes, detections, threat_data
        return threat_annotated