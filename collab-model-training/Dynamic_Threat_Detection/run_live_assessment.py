import cv2
import numpy as np
from ultralytics import YOLO
from boxmot import DeepOcSort
from pathlib import Path
import torch
import torch.nn as nn
import joblib
from collections import deque

# --- 1. LOAD ALL ASSETS ---
print("Loading assets...")

VIDEO_PATH = 'car_approaching.mp4'
MODEL_SAVE_PATH = 'trajectory_model.pth'
SCALER_FILE = 'scaler.gz'
DEVICE = 'cuda:0' if torch.cuda.is_available() else 'cpu'

HISTORY_LEN = 8
FUTURE_LEN = 12

INPUT_SIZE = 2
HIDDEN_SIZE = 128
NUM_LAYERS = 2

# ==============================
# 🔹 Threat Assessment Parameters
# ==============================
DANGER_ZONE_RADIUS_PERCENT = 0.25
DANGER_ZONE_CENTER = None

# Updated weights (your chosen configuration)
PROXIMITY_WEIGHT = 0.5
ANOMALY_WEIGHT   = 0.3
LOOMING_WEIGHT   = 0.2

# Semi-spherical region (Field of View)
THREAT_VIEW_ANGLE = 210  # degrees of forward awareness

ANOMALY_THRESHOLD = 15.0
LOOMING_THRESHOLD = 1.15

# Load perception models
yolo_model = YOLO('yolo11s')
tracker = DeepOcSort(
    reid_weights=Path('osnet_x0_25_msmt17.pt'),
    device=DEVICE,
    half=True
)

# ==============================
# 🔹 LSTM Model Definition
# ==============================
class Seq2SeqLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_seq_len):
        super(Seq2SeqLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_size, output_seq_len * 2)
        self.output_seq_len = output_seq_len
    def forward(self, x):
        _, (hidden, _) = self.lstm(x)
        last_layer_hidden_state = hidden[-1]
        out = self.linear(last_layer_hidden_state)
        out = out.view(-1, self.output_seq_len, 2)
        return out

prediction_model = Seq2SeqLSTM(INPUT_SIZE, HIDDEN_SIZE, NUM_LAYERS, FUTURE_LEN).to(DEVICE)
prediction_model.load_state_dict(torch.load(MODEL_SAVE_PATH))
prediction_model.eval()

scaler = joblib.load(SCALER_FILE)
print(f"Assets loaded. Running on device: {DEVICE}")

# ==============================
# 🔹 Setup
# ==============================
track_histories = {}
track_predictions = {}
track_anomalies = {}
track_area_histories = {}

cap = cv2.VideoCapture(VIDEO_PATH)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
DANGER_ZONE_CENTER = (frame_width // 2, frame_height)
DANGER_ZONE_RADIUS = int(frame_width * DANGER_ZONE_RADIUS_PERCENT)

print("Processing video... Press Q to quit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = yolo_model(frame, classes=[0, 2, 3, 5, 7], conf=0.5, verbose=False)
    detections = results[0].boxes.data.cpu().numpy() if len(results[0]) > 0 else np.empty((0, 6))
    tracks = tracker.update(detections, frame)

    current_track_ids = set()

    if tracks.shape[0] > 0:
        for track in tracks:
            x1, y1, x2, y2, track_id, conf, cls = track[:7]
            area = (x2 - x1) * (y2 - y1)
            track_id = int(track_id)
            current_track_ids.add(track_id)

            if track_id not in track_area_histories:
                track_area_histories[track_id] = deque(maxlen=HISTORY_LEN)
            track_area_histories[track_id].append(area)

            x_center, y_center = (x1 + x2) / 2, (y1 + y2) / 2
            if track_id not in track_histories:
                track_histories[track_id] = deque(maxlen=HISTORY_LEN)
            track_histories[track_id].append((x_center, y_center))

            # --- Prediction and Threat Logic remain identical ---
            # (same as before for LSTM, anomaly, looming)
            # ... [your existing prediction logic here] ...

            # --- Refined Proximity Scoring (Semi-spherical Zone) ---
            proximity_score = 0.0
            if track_id in track_predictions:
                path = track_predictions[track_id].astype(int)
                for i in range(len(path) - 1):
                    cv2.line(frame, tuple(path[i]), tuple(path[i+1]), (0, 255, 255), 2)
                for point in path:
                    dx = point[0] - DANGER_ZONE_CENTER[0]
                    dy = DANGER_ZONE_CENTER[1] - point[1]
                    distance = np.sqrt(dx**2 + dy**2)
                    angle = np.degrees(np.arctan2(dx, dy))
                    if distance < DANGER_ZONE_RADIUS and abs(angle) < (THREAT_VIEW_ANGLE / 2):
                        proximity_score = 1.0
                        break

            # Compute final weighted threat score
            threat_score = (
                proximity_score * PROXIMITY_WEIGHT +
                track_anomalies.get(track_id, {}).get('error', 0) / ANOMALY_THRESHOLD * ANOMALY_WEIGHT +
                (1.0 if track_id in track_area_histories and len(track_area_histories[track_id]) == HISTORY_LEN else 0) * LOOMING_WEIGHT
            )

            color = (0, 255, 0)
            if threat_score > 0.7:
                color = (0, 0, 255)
            elif threat_score > 0.4:
                color = (0, 165, 255)

            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID:{track_id} T:{threat_score:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Draw the semi-spherical region
    cv2.ellipse(
        frame,
        DANGER_ZONE_CENTER,
        (DANGER_ZONE_RADIUS, DANGER_ZONE_RADIUS // 2),
        0,
        -THREAT_VIEW_ANGLE / 2,
        THREAT_VIEW_ANGLE / 2,
        (255, 0, 255),
        2
    )

    cv2.imshow("Dynamic Threat Assessment (Semi-Spherical)", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()