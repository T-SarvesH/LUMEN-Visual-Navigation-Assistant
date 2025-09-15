from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
from models import coordinates

app = FastAPI(title="Lumen API")

app.add_middleware(
    CORSMiddleware,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_origins=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Lumen API"}

@app.websocket("/ws/vio")
async def vio_service(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data_str = await websocket.receive_text()
            data_pack = json.loads(data_str)

            # handle batch
            if 'imu_readings' in data_pack:
                for imu_data in data_pack['imu_readings']:
                    response = coordinates(
                        coord_x=imu_data['x'],
                        coord_y=imu_data['y'],
                        coord_z=imu_data['z']
                    )
                    print({'type': imu_data.get('type'), 'coordinates': response.model_dump()})

                # optionally send ack
                await websocket.send_text(json.dumps({
                    'status': 'batch_received',
                    'count': len(data_pack['imu_readings'])
                }))

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("Exception:", str(e))
