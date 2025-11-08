import sys
import os
import json
import cv2
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

# --- Add project path ---
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# --- Import LUMEN pipeline ---
from models_pipeline.inference import InferenceManager

# ==============================
# 🌐 FASTAPI SETUP
# ==============================
app = FastAPI(title="Lumen API")

app.add_middleware(
    CORSMiddleware,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_origins=["*"],
)

# ==============================
# ⚙️ Initialize Inference Pipeline
# ==============================
print("🚀 Initializing full LUMEN inference pipeline...")
inference_manager = InferenceManager()
print("✅ LUMEN pipeline ready for live inference.")


# ==============================
# 🎥 LumenTrack - Full Inference Stream
# ==============================
class LumenTrack(VideoStreamTrack):
    """
    Receives frames from incoming WebRTC video track,
    runs full LUMEN inference (Router + YOLO + Threat Detection),
    and returns annotated frames in real time.
    """
    kind = "video"

    def __init__(self, track, pc, metadata_channel=None):
        super().__init__()
        self.track = track
        self.pc = pc
        self.metadata_channel = metadata_channel

    async def recv(self):
        # Get next frame
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        # Run the full inference pipeline
        annotated, router_probs, active_classes, detections, threat_data = inference_manager.process_frame(
            img, return_info=True
        )

        # --- Optional metadata stream over WebRTC DataChannel ---
        if self.metadata_channel and self.metadata_channel.readyState == "open":
            payload = json.dumps({
                "router_probs": router_probs,
                "active_classes": active_classes,
                "detections": detections,
                "threat_data": threat_data
            })
            asyncio.ensure_future(self.metadata_channel.send(payload))

        # Convert back to VideoFrame
        new_frame = VideoFrame.from_ndarray(annotated, format="bgr24")
        new_frame.pts, new_frame.time_base = frame.pts, frame.time_base
        return new_frame


# ==============================
# 🛰 WebSocket Endpoint
# ==============================
@app.websocket("/Lumen-ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebRTC + WebSocket endpoint for real-time video streaming inference.
    """
    await websocket.accept()
    print("🔌 Client connected to /Lumen-ws")

    try:
        # Receive SDP offer
        data = await websocket.receive_text()
        msg = json.loads(data)

        # Create PeerConnection
        pc = RTCPeerConnection()
        metadata_channel = None

        # Create optional DataChannel for threat metadata
        @pc.on("datachannel")
        def on_datachannel(channel):
            nonlocal metadata_channel
            metadata_channel = channel
            print(f"📡 Data channel established: {channel.label}")

        # Attach our Lumen inference stream
        @pc.on("track")
        def on_track(track):
            if track.kind == "video":
                print("🎥 Incoming video track connected.")
                lumen_track = LumenTrack(track, pc, metadata_channel)
                pc.addTrack(lumen_track)

        # Set remote description (offer from client)
        offer = RTCSessionDescription(sdp=msg["sdp"], type=msg["type"])
        await pc.setRemoteDescription(offer)

        # Create and send answer (return SDP back to client)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        await websocket.send_text(json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }))

        print("✅ WebRTC negotiation completed.")

    except Exception as e:
        print(f"❌ Error in WebSocket session: {e}")
    finally:
        print("🔴 Client disconnected.")
        await websocket.close()


# ==============================
# 🧠 Run via Uvicorn
# ==============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("websocket_server:app", host="0.0.0.0", port=8000, reload=True)