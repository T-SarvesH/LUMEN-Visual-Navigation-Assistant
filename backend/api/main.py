from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware import CORSMiddleware
import json
import logging

#Importing all API models
from models import coordinates

app = FastAPI(title="Lumen Application Programming interface")

app.add_middleware(

    CORSMiddleware,
    allowed_origins=["*"],
    allowed_headers=["*"],
    allowed_hosts=["*"],
    allowed_methods=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Lumen API"}


# Websocket endpoint for IMU data
@app.websocket("/ws/vioService")
async def vioService(websocket: WebSocket):

    await websocket.accept()
    try:
        while True:
            data_str = await websocket.receive()
            data_pack = json.loads(data_str)

            if 'imu_reading' in data_pack:

                imu_data = data_pack['imu_reading']

                response = coordinates(

                    coord_x=imu_data['x'],
                    coord_y=imu_data['y'],
                    coord_z=imu_data['z']
                )
                await websocket.send_text(json.dumps({'coordinates': response.model_dump()}))

    except WebSocketDisconnect:
        return {'message': 'Client is Disconnected'}
    except Exception as e:
        return {'Exception': str(e)}