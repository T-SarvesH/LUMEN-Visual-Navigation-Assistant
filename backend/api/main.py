import sys
import os
import json
import asyncio
import time
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
from models import UserState

# --- FastAPI Setup ---
app = FastAPI(title="Lumen API")
app.add_middleware(
    CORSMiddleware,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_origins=["*"],
)

# --- Inference Setup ---
from models_pipeline.inference import InferenceManager
inference_manager = InferenceManager()

class LumenTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, track, pc, user_state: UserState, metadata_channel=None):
        super().__init__()
        self.track = track
        self.pc = pc
        self.user_state = user_state
        self.metadata_channel = metadata_channel
        self.last_description_time = 0

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        # Core Inference (Real-time detection)
        annotated, router_probs, active_classes, detections, threat_data = inference_manager.process_frame(
            img, return_info=True
        )

        # Scenery Description logic using Pydantic validated state
        current_time = time.time()
        if current_time - self.last_description_time >= self.user_state.description_interval:
            self.last_description_time = current_time
            # Trigger TTS logic using self.user_state.speech_language
            print(f"Narrator [{self.user_state.speech_language}]: Describing scene...")

        # Metadata output
        if self.metadata_channel and self.metadata_channel.readyState == "open":
            payload = json.dumps({
                "router_probs": router_probs,
                "threat_data": threat_data,
                "settings_active": self.user_state.dict()
            })
            asyncio.ensure_future(self.metadata_channel.send(payload))

        new_frame = VideoFrame.from_ndarray(annotated, format="bgr24")
        new_frame.pts, new_frame.time_base = frame.pts, frame.time_base
        return new_frame

@app.websocket("/Lumen-ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pc = RTCPeerConnection()
    metadata_channel = None

    try:
        # 1. Receive Initial Handshake
        raw_data = await websocket.receive_text()
        msg = json.loads(raw_data)

        # 2. Validate Config with Pydantic
        # Matches frontend: payload.config { description_interval, language }
        try:
            config_data = msg.get("config")
            user_state = UserState(
                description_interval=config_data.get("description_interval"),
                speech_language=config_data.get("language")
            )
            print(f"✅ State Validated: {user_state}")
        except Exception as ve:
            print(f"⚠️ Validation Error: {ve}")
            # Fallback to defaults if validation fails
            user_state = UserState(description_interval=15, speech_language="English")

        @pc.on("datachannel")
        def on_datachannel(channel):
            nonlocal metadata_channel
            metadata_channel = channel

        @pc.on("track")
        def on_track(track):
            if track.kind == "video":
                pc.addTrack(LumenTrack(track, pc, user_state, metadata_channel))

        # 3. WebRTC Negotiation
        offer = RTCSessionDescription(sdp=msg["sdp"], type=msg["type"])
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        await websocket.send_text(json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }))

        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        print(f"❌ Session Error: {e}")
    finally:
        await pc.close()
        print("🔌 Session Closed")