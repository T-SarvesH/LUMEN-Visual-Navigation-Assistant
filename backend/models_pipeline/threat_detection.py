import cv2
import numpy as np
from ultralytics import YOLO
from boxmot import DeepOcSort
from pathlib import Path
import torch
import torch.nn as nn
import joblib
from collections import deque
import os
import math

class ThreatAnalyzer:
    def __init__(self):
        print("🧠 Initializing Threat Analyzer...")

        models_path = os.path.join(os.path.dirname(__file__), "threat_detection_models")

        # --- Device ---
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

        # --- Parameters ---
        self.HISTORY_LEN = 16
        self.FUTURE_LEN = 12
        self.INPUT_SIZE = 2
        self.HIDDEN_SIZE = 128
        self.NUM_LAYERS = 2

        # --- Clustering Parameters ---
        self.CLUSTER_DISTANCE_THRESHOLD = 120 

        # --- Threat Weights (Physics Base) ---
        self.PROXIMITY_WEIGHT = 0.5
        self.ANOMALY_WEIGHT = 0.3
        self.LOOMING_WEIGHT = 0.2

        # --- Class Priority Multipliers ---
        self.CLASS_PRIORITY_MULTIPLIERS = {
            "car": 1.5, "truck": 1.8, "bus": 1.8, "train": 2.0,
            "motorcycle": 1.5, "bicycle": 1.2, "scooter": 1.2,
            "fire": 2.5, "smoke": 2.0, "pothole": 1.5, "debris": 1.4,
            "water": 1.3, "mud": 1.3, "rock": 1.4,
            "person": 1.0, "dog": 0.8, "cat": 0.8, "cow": 1.0
        }
        self.DEFAULT_MULTIPLIER = 1.0

        # --- Thresholds ---
        self.ANOMALY_THRESHOLD = 15.0
        self.LOOMING_THRESHOLD = 1.15
        self.THREAT_VIEW_ANGLE = 210
        self.DANGER_ZONE_RADIUS_PERCENT = 0.25

        # --- Tracker ---
        self.tracker = DeepOcSort(
            reid_weights=Path(f"{models_path}/osnet_x0_25_msmt17.pt"),
            device=self.device,
            half=True
        )

        # --- LSTM Model Definition ---
        class Seq2SeqLSTM(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, output_seq_len):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.linear = nn.Linear(hidden_size, output_seq_len * 2)
                self.output_seq_len = output_seq_len

            def forward(self, x):
                _, (hidden, _) = self.lstm(x)
                out = self.linear(hidden[-1])
                return out.view(-1, self.output_seq_len, 2)

        self.prediction_model = Seq2SeqLSTM(
            self.INPUT_SIZE, self.HIDDEN_SIZE, self.NUM_LAYERS, self.FUTURE_LEN
        ).to(self.device)

        traj_model_path = f"{models_path}/trajectory_model.pth"
        if os.path.exists(traj_model_path):
            self.prediction_model.load_state_dict(
                torch.load(traj_model_path, map_location=self.device)
            )
        else:
            print(f"⚠️ Warning: Trajectory model not found at {traj_model_path}")
            
        self.prediction_model.eval()

        scaler_path = f"{models_path}/scaler.gz"
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
        else:
            print(f"⚠️ Warning: Scaler not found at {scaler_path}")
            self.scaler = None

        self.track_histories = {}
        self.track_predictions = {}
        self.track_anomalies = {}
        self.track_area_histories = {}

        self.initialized = False
        print("✅ Threat Analyzer Ready (With Clustering).")

    def _init_geometry(self, frame):
        if not self.initialized:
            h, w = frame.shape[:2]
            self.DANGER_ZONE_CENTER = (w // 2, h)
            self.DANGER_ZONE_RADIUS = int(w * self.DANGER_ZONE_RADIUS_PERCENT)
            self.initialized = True

    def _get_centroid(self, bbox):
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

    def _cluster_threats(self, raw_items):
        """
        Groups individual detected items by Class and Proximity.
        """
        if not raw_items:
            return []

        # 1. Bucket by class
        by_class = {}
        for item in raw_items:
            cls = item['object']
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(item)

        clustered_results = []

        # 2. Cluster within each class bucket
        for cls, items in by_class.items():
            processed = [False] * len(items)

            for i in range(len(items)):
                if processed[i]:
                    continue
                
                # Start a new cluster
                current_cluster = [items[i]]
                processed[i] = True
                
                seed_centroid = self._get_centroid(items[i]['bbox-coords'])
                
                for j in range(i + 1, len(items)):
                    if processed[j]:
                        continue
                        
                    compare_centroid = self._get_centroid(items[j]['bbox-coords'])
                    dist = math.hypot(seed_centroid[0] - compare_centroid[0], 
                                      seed_centroid[1] - compare_centroid[1])
                    
                    if dist < self.CLUSTER_DISTANCE_THRESHOLD:
                        current_cluster.append(items[j])
                        processed[j] = True

                # 3. Aggregate the Cluster
                min_x = min(x['bbox-coords'][0] for x in current_cluster)
                min_y = min(x['bbox-coords'][1] for x in current_cluster)
                max_x = max(x['bbox-coords'][2] for x in current_cluster)
                max_y = max(x['bbox-coords'][3] for x in current_cluster)

                max_threat = max(x['threat_score'] for x in current_cluster)
                max_conf = max(x['confidence'] for x in current_cluster)
                
                count = len(current_cluster)
                display_name = f"{count} {cls}s" if count > 1 else cls
                
                clustered_results.append({
                    "id": f"{cls}_{i}", 
                    "object": display_name,
                    "raw_class": cls,
                    "count": count,
                    "confidence": max_conf,
                    "threat_score": max_threat,
                    "bbox-coords": [min_x, min_y, max_x, max_y],
                    "constituents": current_cluster 
                })

        return clustered_results

    def analyze(self, annotated_frame, detections):
        self._init_geometry(annotated_frame)
        frame = annotated_frame.copy()

        # [x1, y1, x2, y2, conf, class_id]
        detections_np = np.array([
            [*det["xyxy"], det["conf"], det["class_id"]]
            for det in detections
        ]) if detections else np.empty((0, 6))

        if detections_np.shape[0] == 0:
            return frame, {}

        try:
            tracks = self.tracker.update(detections_np, frame)
        except Exception:
            return frame, {}

        raw_processed_items = []
        class_lookup = {det["class_id"]: det["class"] for det in detections}

        # -----------------------------------
        # 1. PROCESS PHYSICS (Individually)
        # -----------------------------------
        for track in tracks:
            x1, y1, x2, y2, track_id, conf, class_id = track[:7]
            track_id = int(track_id)
            class_id = int(class_id)
            cls_name = class_lookup.get(class_id, "Unknown")

            area = (x2 - x1) * (y2 - y1)
            if track_id not in self.track_area_histories:
                self.track_area_histories[track_id] = deque(maxlen=self.HISTORY_LEN)
            self.track_area_histories[track_id].append(area)

            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            if track_id not in self.track_histories:
                self.track_histories[track_id] = deque(maxlen=self.HISTORY_LEN)
            self.track_histories[track_id].append((cx, cy))

            if len(self.track_histories[track_id]) < self.HISTORY_LEN or self.scaler is None:
                raw_processed_items.append({
                    "track_id": track_id,
                    "object": cls_name,
                    "confidence": float(conf),
                    "threat_score": 0.0, 
                    "bbox-coords": [int(x1), int(y1), int(x2), int(y2)],
                    "predicted_path": [] 
                })
                continue

            hist_np = np.array(self.track_histories[track_id])
            deltas = np.diff(hist_np, axis=0)
            scaled = self.scaler.transform(deltas)
            padded = np.vstack([np.zeros((1, 2)), scaled])
            tensor = torch.from_numpy(padded).float().unsqueeze(0).to(self.device)

            with torch.no_grad():
                pred_scaled = self.prediction_model(tensor).squeeze(0).cpu().numpy()
                pred_deltas = self.scaler.inverse_transform(pred_scaled)

            predicted_path = np.zeros_like(pred_deltas)
            cur = hist_np[-1]
            for i in range(len(pred_deltas)):
                cur = cur + pred_deltas[i]
                predicted_path[i] = cur

            # Scores
            anomaly_score = 0.0
            if track_id in self.track_anomalies and "prev_pred" in self.track_anomalies[track_id]:
                prev_pos = self.track_anomalies[track_id]["prev_pred"][0]
                error = np.linalg.norm(np.array([cx, cy]) - prev_pos)
                anomaly_score = min(error / self.ANOMALY_THRESHOLD, 1.0)
            
            if track_id not in self.track_anomalies: self.track_anomalies[track_id] = {}
            self.track_anomalies[track_id]["prev_pred"] = predicted_path

            looming_score = 0.0
            if len(self.track_area_histories[track_id]) == self.HISTORY_LEN:
                areas = np.array(self.track_area_histories[track_id])
                if np.mean(areas[4:]) > np.mean(areas[:4]) * self.LOOMING_THRESHOLD:
                    looming_score = 1.0

            proximity_score = 0.0
            for point in predicted_path.astype(int):
                dx = point[0] - self.DANGER_ZONE_CENTER[0]
                dy = self.DANGER_ZONE_CENTER[1] - point[1]
                dist = np.sqrt(dx**2 + dy**2)
                angle = np.degrees(np.arctan2(dx, dy))
                if dist < self.DANGER_ZONE_RADIUS and abs(angle) < self.THREAT_VIEW_ANGLE / 2:
                    proximity_score = 1.0
                    break

            base_threat = (self.PROXIMITY_WEIGHT * proximity_score +
                           self.ANOMALY_WEIGHT * anomaly_score +
                           self.LOOMING_WEIGHT * looming_score)
            
            priority_mult = self.CLASS_PRIORITY_MULTIPLIERS.get(cls_name.lower(), self.DEFAULT_MULTIPLIER)
            threat_score = min(base_threat * priority_mult, 1.0)

            raw_processed_items.append({
                "track_id": track_id,
                "object": cls_name,
                "confidence": float(conf),
                "threat_score": float(threat_score),
                "bbox-coords": [int(x1), int(y1), int(x2), int(y2)],
                "predicted_path": predicted_path.tolist() 
            })

        # -----------------------------------
        # 2. CLUSTER ITEMS
        # -----------------------------------
        clustered_data_list = self._cluster_threats(raw_processed_items)
        final_threat_dict = {}

        # -----------------------------------
        # 3. DRAW VISUALIZATION (On Clusters)
        # -----------------------------------
        for cluster in clustered_data_list:
            x1, y1, x2, y2 = cluster["bbox-coords"]
            threat_score = cluster["threat_score"]
            display_name = cluster["object"]

            # Color Coding
            color = (0, 255, 0)
            if threat_score > 0.7: color = (0, 0, 255) # Red
            elif threat_score > 0.4: color = (0, 165, 255) # Orange

            # Draw Clustered Bounding Box
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 3)

            # Draw Label
            label = f"{display_name} | T:{threat_score:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            final_threat_dict[cluster["id"]] = cluster

        # ===============================
        # Forward Safety ROI Overlay
        # ===============================
        overlay = frame.copy()
        h, w = frame.shape[:2]
        zone_center = (w // 2, h - 2)
        major_axis = int(w * 0.45)
        minor_axis = int(h * 0.2)
        ROI_COLOR = (255, 255, 200)
        ALPHA = 0.22

        cv2.ellipse(overlay, zone_center, (major_axis, minor_axis), 0, 180, 360, ROI_COLOR, -1, cv2.LINE_AA)
        frame = cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0)
        cv2.ellipse(frame, zone_center, (major_axis, minor_axis), 0, 180, 360, ROI_COLOR, 2, cv2.LINE_AA)

        return frame, final_threat_dict