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

class ThreatAnalyzer:
    def __init__(self):
        print("🧠 Initializing Threat Analyzer...")

        models_path = os.path.join(os.path.dirname(__file__), "threat_detection_models")

        # --- Device ---
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

        # --- Parameters ---
        self.HISTORY_LEN = 8
        self.FUTURE_LEN = 12
        self.INPUT_SIZE = 2
        self.HIDDEN_SIZE = 128
        self.NUM_LAYERS = 2

        # --- Threat Weights ---
        self.PROXIMITY_WEIGHT = 0.5
        self.ANOMALY_WEIGHT = 0.3
        self.LOOMING_WEIGHT = 0.2

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

        # --- LSTM Model ---
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

        # Load prediction model
        self.prediction_model = Seq2SeqLSTM(
            self.INPUT_SIZE, self.HIDDEN_SIZE, self.NUM_LAYERS, self.FUTURE_LEN
        ).to(self.device)

        self.prediction_model.load_state_dict(
            torch.load(f"{models_path}/trajectory_model.pth", map_location=self.device)
        )
        self.prediction_model.eval()

        # Scaler
        self.scaler = joblib.load(f"{models_path}/scaler.gz")

        # Histories
        self.track_histories = {}
        self.track_predictions = {}
        self.track_anomalies = {}
        self.track_area_histories = {}

        self.initialized = False
        print("✅ Threat Analyzer Ready.")

    # -----------------------------------------------
    # Initialize geometry (once)
    # -----------------------------------------------
    def _init_geometry(self, frame):
        if not self.initialized:
            h, w = frame.shape[:2]
            self.DANGER_ZONE_CENTER = (w // 2, h)
            self.DANGER_ZONE_RADIUS = int(w * self.DANGER_ZONE_RADIUS_PERCENT)
            self.initialized = True

    # -----------------------------------------------
    # Main Threat Analysis Function
    # -----------------------------------------------
    def analyze(self, annotated_frame, detections):
        self._init_geometry(annotated_frame)

        frame = annotated_frame.copy()

        # Convert YOLO detections → numpy for tracker
        detections_np = np.array([
            [*det["xyxy"], det["conf"], det["class_id"]]
            for det in detections
        ]) if detections else np.empty((0, 6))

        # If no detections → skip
        if detections_np.shape[0] == 0:
            return frame, {}

        # Tracker update (safe)
        try:
            tracks = self.tracker.update(detections_np, frame)
        except:
            return frame, {}

        threat_data = {}

        # Build a lookup table: class_id → class_name
        # Example:
        # {0: "person", 2:"car"}
        class_lookup = {det["class_id"]: det["class"] for det in detections}

        # -----------------------------------
        # Iterate over tracked objects
        # -----------------------------------
        for track in tracks:
            x1, y1, x2, y2, track_id, conf, class_id = track[:7]
            track_id = int(track_id)
            class_id = int(class_id)

            cls_name = class_lookup.get(class_id, "Unknown")

            # ----------- Update movement histories -----------
            area = (x2 - x1) * (y2 - y1)
            if track_id not in self.track_area_histories:
                self.track_area_histories[track_id] = deque(maxlen=self.HISTORY_LEN)
            self.track_area_histories[track_id].append(area)

            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            if track_id not in self.track_histories:
                self.track_histories[track_id] = deque(maxlen=self.HISTORY_LEN)
            self.track_histories[track_id].append((cx, cy))

            # Not enough history → skip threat estimation
            if len(self.track_histories[track_id]) < self.HISTORY_LEN:
                continue

            # ------------ Motion Prediction ------------
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

            self.track_predictions[track_id] = predicted_path

            # ------------ Anomaly Score ------------
            anomaly_score = 0.0
            if track_id in self.track_anomalies and "prev_pred" in self.track_anomalies[track_id]:
                prev_pos = self.track_anomalies[track_id]["prev_pred"][0]
                actual = np.array([cx, cy])
                error = np.linalg.norm(actual - prev_pos)
                anomaly_score = min(error / self.ANOMALY_THRESHOLD, 1.0)

            if track_id not in self.track_anomalies:
                self.track_anomalies[track_id] = {}
            self.track_anomalies[track_id]["prev_pred"] = predicted_path

            # ------------ Looming Score ------------
            looming_score = 0.0
            if len(self.track_area_histories[track_id]) == self.HISTORY_LEN:
                areas = np.array(self.track_area_histories[track_id])
                if np.mean(areas[4:]) > np.mean(areas[:4]) * self.LOOMING_THRESHOLD:
                    looming_score = 1.0

            # ------------ Proximity Score ------------
            proximity_score = 0.0
            for point in predicted_path.astype(int):
                dx = point[0] - self.DANGER_ZONE_CENTER[0]
                dy = self.DANGER_ZONE_CENTER[1] - point[1]
                distance = np.sqrt(dx**2 + dy**2)
                angle = np.degrees(np.arctan2(dx, dy))
                if distance < self.DANGER_ZONE_RADIUS and abs(angle) < self.THREAT_VIEW_ANGLE / 2:
                    proximity_score = 1.0
                    break

            # ------------ Final Weighted Threat Score ------------
            threat_score = (
                0.5 * proximity_score +
                0.3 * anomaly_score +
                0.2 * looming_score
            )

            # ------------ Draw Overlays ------------
            color = (0, 255, 0)
            if threat_score > 0.7:
                color = (0, 0, 255)
            elif threat_score > 0.4:
                color = (0, 165, 255)

            # Overlay label
            text = f"{cls_name} | Conf:{conf:.2f} | T:{threat_score:.2f}"
            cv2.putText(frame, text, (int(x1), int(y1) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            # Re-color YOLO box
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                          color, 3)

            # Save output dictionary
            threat_data[track_id] = {
                "object": cls_name,
                "confidence": float(conf),
                "threat_score": float(threat_score),
                "proximity": float(proximity_score),
                "anomaly": float(anomaly_score),
                "looming": float(looming_score),
                "bbox-coords": [int(x1), int(y1), int(x2), int(y2)]
            }

        # ===============================
        # Forward Safety ROI (POV-aligned)
        # ===============================
        overlay = frame.copy()
        h, w = frame.shape[:2]

        # --- Center anchored just INSIDE bottom edge (prevents cutoff) ---
        zone_center = (w // 2, h - 2)

        # --- Axis tuning (85% bottom alignment, flatter depth) ---
        major_axis = int(w * 0.45)     # ~85% total width coverage
        minor_axis = int(h * 0.2)      # controlled vertical depth

        # --- Light cyan (true light cyan in BGR) ---
        ROI_COLOR = (255, 255, 200)     # light cyan
        ALPHA = 0.22

        # --- Filled upper-half ellipse (forward-only ROI) ---
        cv2.ellipse(
            overlay,
            zone_center,
            (major_axis, minor_axis),
            angle=0,
            startAngle=180,
            endAngle=360,
            color=ROI_COLOR,
            thickness=-1,
            lineType=cv2.LINE_AA
        )

        # --- Blend overlay smoothly ---
        frame = cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0)

        # --- Clean anti-aliased outline ---
        cv2.ellipse(
            frame,
            zone_center,
            (major_axis, minor_axis),
            angle=0,
            startAngle=180,
            endAngle=360,
            color=ROI_COLOR,
            thickness=2,
            lineType=cv2.LINE_AA
        )

        return frame, threat_data