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
        self.THREAT_VIEW_ANGLE = 210  # Semi-spherical FoV
        self.DANGER_ZONE_RADIUS_PERCENT = 0.25

        # --- Tracker ---
        self.tracker = DeepOcSort(
            reid_weights=Path(f"{models_path}/osnet_x0_25_msmt17.pt"),
            device=self.device,
            half=True
        )

        # --- LSTM model for trajectory prediction ---
        class Seq2SeqLSTM(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, output_seq_len):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.linear = nn.Linear(hidden_size, output_seq_len * 2)
                self.output_seq_len = output_seq_len
            def forward(self, x):
                _, (hidden, _) = self.lstm(x)
                last_layer_hidden_state = hidden[-1]
                out = self.linear(last_layer_hidden_state)
                out = out.view(-1, self.output_seq_len, 2)
                return out

        self.prediction_model = Seq2SeqLSTM(
            self.INPUT_SIZE, self.HIDDEN_SIZE, self.NUM_LAYERS, self.FUTURE_LEN
        ).to(self.device)
        self.prediction_model.load_state_dict(torch.load(f"{models_path}/trajectory_model.pth", map_location=self.device))
        self.prediction_model.eval()

        # --- Scaler ---
        self.scaler = joblib.load(f"{models_path}/scaler.gz")

        # --- Histories ---
        self.track_histories = {}
        self.track_predictions = {}
        self.track_anomalies = {}
        self.track_area_histories = {}

        self.initialized = False
        print("✅ Threat Analyzer Ready.")

    # ------------------------------------------------
    # ⚙️ Initialize frame-dependent parameters
    # ------------------------------------------------
    def _init_geometry(self, frame):
        if not self.initialized:
            h, w = frame.shape[:2]
            self.DANGER_ZONE_CENTER = (w // 2, h)
            self.DANGER_ZONE_RADIUS = int(w * self.DANGER_ZONE_RADIUS_PERCENT)
            self.initialized = True

    # ------------------------------------------------
    # 🚨 Analyze Threats on Annotated Frame
    # ------------------------------------------------
    def analyze(self, annotated_frame, detections):
        self._init_geometry(annotated_frame)

        frame = annotated_frame.copy()
        current_track_ids = set()
        detections_np = np.array([
            [*det["xyxy"], det["conf"], det.get("class_id", 0)]
            for det in detections
        ]) if detections else np.empty((0, 6))

        # ✅ Safety check before calling DeepOcSort
        if detections_np.shape[0] == 0:
            # No detections → skip tracker update
            return frame, {}
        try:
            tracks = self.tracker.update(detections_np, frame)
        except cv2.error as e:
            print(f"⚠️ [ThreatAnalyzer] Optical flow tracking failed this frame: {str(e)}")
            return frame, {}
        threat_data = {}

        if tracks.shape[0] > 0:
            for track in tracks:
                x1, y1, x2, y2, track_id, conf, cls = track[:7]
                track_id = int(track_id)
                current_track_ids.add(track_id)
                area = (x2 - x1) * (y2 - y1)

                if track_id not in self.track_area_histories:
                    self.track_area_histories[track_id] = deque(maxlen=self.HISTORY_LEN)
                self.track_area_histories[track_id].append(area)

                x_center, y_center = (x1 + x2) / 2, (y1 + y2) / 2
                if track_id not in self.track_histories:
                    self.track_histories[track_id] = deque(maxlen=self.HISTORY_LEN)
                self.track_histories[track_id].append((x_center, y_center))

                # --- Threat computation (same logic as before) ---
                proximity_score, anomaly_score, looming_score = 0.0, 0.0, 0.0

                if len(self.track_histories[track_id]) == self.HISTORY_LEN:
                    hist_np = np.array(self.track_histories[track_id])
                    hist_deltas = np.diff(hist_np, axis=0)
                    scaled = self.scaler.transform(hist_deltas)
                    padded = np.vstack([np.zeros((1, 2)), scaled])
                    hist_tensor = torch.from_numpy(padded).float().unsqueeze(0).to(self.device)

                    with torch.no_grad():
                        pred_deltas_tensor = self.prediction_model(hist_tensor)
                        pred_scaled = pred_deltas_tensor.squeeze(0).cpu().numpy()
                        pred_deltas = self.scaler.inverse_transform(pred_scaled)

                    predicted_path = np.zeros_like(pred_deltas)
                    current_pos = hist_np[-1]
                    for i in range(len(pred_deltas)):
                        current_pos = current_pos + pred_deltas[i]
                        predicted_path[i] = current_pos
                    self.track_predictions[track_id] = predicted_path

                    if len(self.track_area_histories[track_id]) == self.HISTORY_LEN:
                        areas = np.array(self.track_area_histories[track_id])
                        if np.mean(areas[self.HISTORY_LEN//2:]) > np.mean(areas[:self.HISTORY_LEN//2]) * self.LOOMING_THRESHOLD:
                            looming_score = 1.0

                    if track_id in self.track_anomalies and 'prev_pred' in self.track_anomalies[track_id]:
                        prev_pred = self.track_anomalies[track_id]['prev_pred'][0]
                        actual = np.array([x_center, y_center])
                        error = np.linalg.norm(actual - prev_pred)
                        anomaly_score = min(error / self.ANOMALY_THRESHOLD, 1.0)
                        self.track_anomalies[track_id]['error'] = error

                    if track_id not in self.track_anomalies:
                        self.track_anomalies[track_id] = {}
                    self.track_anomalies[track_id]['prev_pred'] = predicted_path

                    for point in predicted_path.astype(int):
                        dx = point[0] - self.DANGER_ZONE_CENTER[0]
                        dy = self.DANGER_ZONE_CENTER[1] - point[1]
                        distance = np.sqrt(dx**2 + dy**2)
                        angle = np.degrees(np.arctan2(dx, dy))
                        if distance < self.DANGER_ZONE_RADIUS and abs(angle) < (self.THREAT_VIEW_ANGLE / 2):
                            proximity_score = 1.0
                            break

                    threat_score = (
                        proximity_score * self.PROXIMITY_WEIGHT +
                        anomaly_score * self.ANOMALY_WEIGHT +
                        looming_score * self.LOOMING_WEIGHT
                    )

                    # Color-code the existing YOLO bbox (no new boxes)
                    color = (0, 255, 0)
                    if threat_score > 0.7:
                        color = (0, 0, 255)
                    elif threat_score > 0.4:
                        color = (0, 165, 255)

                    cls_name = str(int(cls))
                    label_text = f"{cls_name} | Conf:{conf:.2f} | T:{threat_score:.2f}"
                    cv2.putText(frame, label_text, (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    # Apply thicker border color overlay to YOLO bbox
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 3)

                    threat_data[track_id] = {
                        "object": cls_name,
                        "confidence": float(conf),
                        "threat_score": threat_score,
                        "proximity": proximity_score,
                        "anomaly": anomaly_score,
                        "looming": looming_score
                    }

        # --- Draw improved semi-spherical safety zone ---
        overlay = frame.copy()

        h, w = frame.shape[:2]

        # ✅ Center slightly below bottom edge for full curvature
        zone_center = (w // 2, int(h * 1.02))  # 2% below bottom edge
        adaptive_radius = int(w * 0.38)        # slightly wider horizontally
        ellipse_height = int(adaptive_radius * 0.42)  # balanced curvature

        # ✅ Draw filled semi-transparent magenta arc (240° span)
        cv2.ellipse(
            overlay,
            zone_center,
            (adaptive_radius, ellipse_height),
            0,
            -120,  # start angle
            120,   # end angle
            (255, 0, 255),
            -1
        )

        # ✅ Blend with transparency for smooth overlay
        frame = cv2.addWeighted(overlay, 0.28, frame, 0.72, 0)

        # ✅ Draw a clean magenta outline for definition
        cv2.ellipse(
            frame,
            zone_center,
            (adaptive_radius, ellipse_height),
            0,
            -120,
            120,
            (255, 0, 255),
            3
        )

        return frame, threat_data
