import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import numpy as np
import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from Object_Detection_and_Scene_Description_Model.main_model import object_detection_and_results
from models import coordinates
from ultralytics import YOLO

app = FastAPI(title="Lumen API")
app.add_middleware(
    CORSMiddleware,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_origins=["*"],
)

HOME = os.getenv("HOME")
MODEL_PATH = HOME + "/LUMEN-Visual-Navigation-Assistant/runs/detect/train3/weights"
model = YOLO(MODEL_PATH)

@app.websocket("/Lumen-ws")
async def vio_service(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data_str = await websocket.receive_text()
            data_pack = json.loads(data_str)

            # Handle IMU readings
            if 'imu_readings' in data_pack:
                for imu_data in data_pack['imu_readings']:
                    response = coordinates(coord_x=imu_data['x'], coord_y=imu_data['y'], coord_z=imu_data['z'])
                    print({'type': imu_data.get('type'), 'coordinates': response.model_dump()})

                await websocket.send_text(json.dumps({'status': 'batch_received', 'count': len(data_pack['imu_readings'])}))

            # Handle raw frame
            if 'frame' in data_pack and data_pack['frame'] is not None:
                raw_bytes = np.array(data_pack['frame'], dtype=np.uint8)
                frame_height = data_pack['frame_height']
                frame_width = data_pack['frame_width']

                # Reshape YUV bytes into image (YUV420)
                y_size = frame_width * frame_height
                u_size = v_size = y_size // 4
                y = raw_bytes[0:y_size].reshape((frame_height, frame_width))
                u = raw_bytes[y_size:y_size+u_size].reshape((frame_height//2, frame_width//2))
                v = raw_bytes[y_size+u_size:y_size+u_size+v_size].reshape((frame_height//2, frame_width//2))

                u_up = cv2.resize(u, (frame_width, frame_height), interpolation=cv2.INTER_LINEAR)
                v_up = cv2.resize(v, (frame_width, frame_height), interpolation=cv2.INTER_LINEAR)
                yuv = cv2.merge([y, u_up, v_up])
                bgr_frame = cv2.cvtColor(yuv, cv2.COLOR_YCrCb2BGR)

                detections = object_detection_and_results(bgr_frame, model)

                await websocket.send_text(json.dumps({
                    'status': 'frame_processed',
                    'detected_objects': [d.model_dump() for d in detections],
                    'timeFrame': datetime.now().isoformat()
                }))

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("Exception:", str(e))

    await websocket.close()
