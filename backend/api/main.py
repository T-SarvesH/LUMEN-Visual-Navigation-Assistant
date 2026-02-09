import sys, os, json, asyncio, logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import cv2
from .models import UserState
from models_pipeline.inference import InferenceManager

# --- Optimization Setup ---
executor = ThreadPoolExecutor(max_workers=2) # Decouples AI from WebRTC heartbeats
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Lumen API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

inference_manager = InferenceManager()
active_sessions = set()

class LumenTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, track, pc, user_state, metadata_channel=None):
        super().__init__()
        self.track, self.pc, self.user_state = track, pc, user_state
        self.metadata_channel = metadata_channel
        self.queue = asyncio.Queue(maxsize=1)
        self.orientation = "portrait"

    async def _consume_inbound(self):
        """Continuously drains the inbound 720p stream to prevent backpressure."""
        try:
            while True:
                frame = await self.track.recv()
                # Clear queue to ensure we only keep the newest frame (No Lag)
                while not self.queue.empty():
                    self.queue.get_nowait()
                # print(f"DEBUG: Frame received in queue. Size: {self.queue.qsize()}")
                await self.queue.put(frame)
        except Exception as e:
            print(f"DEBUG: Inbound consumption stopped: {e}")
            import traceback
            traceback.print_exc()

    async def recv(self):
        frame = await self.queue.get()
        loop = asyncio.get_event_loop()
        
        try:
            results = await loop.run_in_executor(
                executor, self._process_ai, frame
            )
            
            annotated_img = results["annotated_frame"]
            narration = results["narration"]
            critical_alert = results.get("critical_alert")

            if self.metadata_channel and self.metadata_channel.readyState == "open":
                
                # PRIORITY 1: Critical Alert
                if critical_alert:
                    print(f"!!! CRITICAL ALERT SENT: {critical_alert}")
                    self.metadata_channel.send(json.dumps({
                        "type": "critical_alert",
                        "text": critical_alert,
                        "language": self.user_state.speech_language
                    }))
                
                # PRIORITY 2: Standard Narration (only if no critical alert to avoid overlap)
                elif narration:
                    self.metadata_channel.send(json.dumps({
                        "type": "narration_event",
                        "text": narration,
                        "language": self.user_state.speech_language
                    }))

            new_frame = VideoFrame.from_ndarray(annotated_img, format="bgr24")
            new_frame.pts, new_frame.time_base = frame.pts, frame.time_base
            return new_frame

        except Exception as e:
            print(f"ERROR in recv loop: {e}")
            import traceback
            traceback.print_exc()
            return frame

    def _process_ai(self, frame):
        """Synchronous processing: Handles YOLO inference."""
        img = frame.to_ndarray(format="bgr24")
        
        # --- LANDSCAPE OPTIMIZATION ---
        # We now enforce Landscape mode on frontend, so we expect wide (1280x720) frames.
        # No rotation needed.
        
        results = inference_manager.process_frame(img, return_info=True)
        return results

@app.websocket("/Lumen-ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"DEBUG: WebSocket accepted from {websocket.client}")
    pc = RTCPeerConnection()
    active_sessions.add(pc)
    l_track = None
    metadata_channel = None

    @pc.on("datachannel")
    def on_datachannel(channel):
        nonlocal metadata_channel
        metadata_channel = channel
        print("DEBUG: DataChannel established")
        
        # If track already exists, attach channel now
        if l_track:
            l_track.metadata_channel = channel

        @channel.on("message")
        def on_message(message):
            data = json.loads(message)
            if data["type"] == "orientation_sync" and l_track:
                l_track.orientation = data["value"]

    try:
        # --- OPTIMIZATION: Signal Server Readiness Immediately ---
        # This tells the frontend it's safe to start the camera
        await websocket.send_text(json.dumps({
            "type": "server_ready",
            "status": "active" 
        }))

        raw_data = await websocket.receive_text()
        print("DEBUG: Received WebSocket message")
        msg = json.loads(raw_data)
        config = msg.get("config", {})
        user_state = UserState(
            speech_language=config.get("language", "English"),
            description_interval=config.get("description_interval", 10)
        )
        config = msg.get("config", {})
        user_state = UserState(
            speech_language=config.get("language", "English"),
            description_interval=config.get("description_interval", 10)
        )

        @pc.on("track")
        def on_track(track):
            print(f"DEBUG: Track received: kind={track.kind}, id={track.id}")
            nonlocal l_track
            if track.kind == "video":
                # Pass the captured channel (if exists) to the track
                l_track = LumenTrack(track, pc, user_state, metadata_channel=metadata_channel)
                asyncio.ensure_future(l_track._consume_inbound())
                pc.addTrack(l_track)
        
        @pc.on("iceconnectionstatechange")
        async def on_ice_connection_state_change():
            print(f"DEBUG: ICE Connection State changed to: {pc.iceConnectionState}")
            if pc.iceConnectionState == "failed":
                print("DEBUG: ICE Connection failed! Check firewall or network.")

        offer = RTCSessionDescription(sdp=msg["sdp"], type=msg["type"])
        await pc.setRemoteDescription(offer)
        print("DEBUG: Remote Description set")
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        while pc.iceGatheringState != "complete":
            await asyncio.sleep(0.05)
        
        await websocket.send_text(json.dumps({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}))
        
        # --- Signal that Models/Pipeline are Ready ---
        # Since InferenceManager is initialized at startup, we just confirm it here.
        # In a real heavy-load scenario, we would check inference_manager.status
        await websocket.send_text(json.dumps({
            "type": "init_complete",
            "status": "active"
        }))

        while pc.connectionState not in ["closed", "failed"]:
            await asyncio.sleep(1)
    finally:
        active_sessions.discard(pc)
        await pc.close()