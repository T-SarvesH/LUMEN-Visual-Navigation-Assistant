import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import cv2
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaStreamTrack
from av import VideoFrame

app = FastAPI(title="Lumen API")
app.add_middleware(
    CORSMiddleware,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_origins=["*"],
)

#MODEL_PATH is a env var so set it up on .bashrc
model = YOLO(os.getenv("MODEL_PATH") + '/' + 'best.pt').to("cuda")

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

class YoloTrack(VideoStreamTrack):
    """
    Takes frames from incoming track, runs YOLO, returns annotated frames.
    """
    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        # Run YOLO detection
        results = model(img, verbose=False)
        annotated = results[0].plot()

        # Convert back to VideoFrame
        new_frame = VideoFrame.from_ndarray(annotated, format="bgr24")
        new_frame.pts, new_frame.time_base = frame.pts, frame.time_base
        return new_frame


@app.websocket("/Lumen-ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Receive SDP offer
    data = await websocket.receive_text()
    msg = json.loads(data)

    pc = RTCPeerConnection()

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            pc.addTrack(YoloTrack(track))

    # Set remote description
    offer = RTCSessionDescription(sdp=msg["sdp"], type=msg["type"])
    await pc.setRemoteDescription(offer)

    # Create and send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    await websocket.send_text(json.dumps({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }))

