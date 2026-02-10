import csv
import time
import os
import json
import cv2
import threading
from datetime import datetime
from django.conf import settings

class SessionLogger:
    def __init__(self, session_name=None, record_video=False):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if session_name:
            self.session_id = f"{session_name}_{self.session_id}"
            
        # Ensure logs directory exists
        base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
        self.log_dir = os.path.join(base_dir, 'testing', 'logs', self.session_id)
        os.makedirs(self.log_dir, exist_ok=True)

        self.record_video = record_video
        
        # --- 1. Threats Log ---
        self.f_threats = open(os.path.join(self.log_dir, "threats.csv"), 'w', newline='', encoding='utf-8')
        self.w_threats = csv.writer(self.f_threats)
        self.w_threats.writerow(["timestamp", "frame_id", "threat_score", "count", "label", "confidence", "bbox"])
        
        # --- 2. Detections Log (Raw) ---
        self.f_detections = open(os.path.join(self.log_dir, "detections.csv"), 'w', newline='', encoding='utf-8')
        self.w_detections = csv.writer(self.f_detections)
        self.w_detections.writerow(["timestamp", "frame_id", "class", "confidence", "xyxy"])
        
        # --- 3. Narrations Log ---
        self.f_narrations = open(os.path.join(self.log_dir, "narrations.csv"), 'w', newline='', encoding='utf-8')
        self.w_narrations = csv.writer(self.f_narrations)
        self.w_narrations.writerow(["timestamp", "frame_id", "type", "content"])
        
        # --- 4. Video Image Writer ---
        self.video_writer = None
        if self.record_video:
            # Video writer will be initialized on first frame to get dimensions
            self.video_path = os.path.join(self.log_dir, "session_recording.mp4")
            self.frame_size = None
            
        print(f"📝 Session Logger initialized: {self.log_dir}")
        print(f"📹 Video Recording: {'ENABLED' if record_video else 'DISABLED'}")
        
        # Capture start time for relative timestamping
        self.start_time = time.time()
        
    def log_frame_data(self, frame_id: int, threat_data: dict, detections: list, narration: str = None, frame_img = None):
        """
        Master logging function called every frame.
        """
        now = time.time()
        
        if self.record_video:
            # Video Format: 00:30 (Minutes:Seconds from start)
            elapsed = now - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            ts = f"{minutes:02d}:{seconds:02d}"
        else:
            # Human Readable: 8:30pm
            ts = datetime.fromtimestamp(now).strftime("%I:%M%p").lower()
        
        # OPTIMIZATION: Log only every 6th frame (~5 FPS) to save space, 
        # UNLESS there is a non-zero threat score which we want high resolution for.
        should_log = (frame_id % 6 == 0)

        # 1. Log Threats
        if threat_data:
            for obj_id, data in threat_data.items():
                t_score = data.get("threat_score", 0.0)
                
                # Always log if threat is detected, otherwise respect decimation
                if t_score > 0 or should_log:
                    self.w_threats.writerow([
                        ts, frame_id, 
                        f"{t_score:.2f}", 
                        data.get("count", 1),
                        data.get("object", "Unknown"),
                        f"{data.get('confidence', 0.0):.2f}",
                        json.dumps(data.get("bbox-coords", []))
                    ])

        # 2. Log Raw Detections (Decimated)
        if detections and should_log:
            for d in detections:
                self.w_detections.writerow([
                    ts, frame_id,
                    d.get("class", "?"),
                    f"{d.get('conf', 0.0):.2f}",
                    json.dumps(d.get("xyxy", []))
                ])
                
        # 3. Log Narration
        if narration:
            self.w_narrations.writerow([ts, frame_id, "narration", narration])
            self.f_narrations.flush() # Flush important events
            
        # 4. Record Video
        if self.record_video and frame_img is not None:
            self._write_video_frame(frame_img)

    def _write_video_frame(self, frame):
        if self.video_writer is None:
            h, w = frame.shape[:2]
            self.frame_size = (w, h)
            # mp4v or h264
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(self.video_path, fourcc, 30.0, (w, h))
            
        self.video_writer.write(frame)

    def close(self):
        try:
            self.f_threats.close()
            self.f_detections.close()
            self.f_narrations.close()
            if self.video_writer:
                self.video_writer.release()
            print(f"📝 Session Logger closed.")
        except Exception as e:
            print(f"❌ Logger Close Error: {e}")
