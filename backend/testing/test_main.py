import sys, os, json, asyncio, logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import cv2
import django

# --- DJANGO SETUP FOR STANDALONE SCRIPT ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Add backend root
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Adjusted Imports for 'testing' app location
from api.models import UserState
from models_pipeline.inference import InferenceManager
from .session_logger import SessionLogger

# --- Optimization Setup ---
executor = ThreadPoolExecutor(max_workers=2) # Decouples AI from WebRTC heartbeats
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Lumen Test API (Port 8002)")
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

    def __init__(self, track, pc, user_state, metadata_channel=None, logger=None):
        super().__init__()
        self.track, self.pc, self.user_state = track, pc, user_state
        self.metadata_channel = metadata_channel
        self.logger = logger
        self.queue = asyncio.Queue(maxsize=1)
        self.orientation = "portrait"
        self.frame_count = 0

    async def _consume_inbound(self):
        """Continuously drains the inbound 720p stream to prevent backpressure."""
        try:
            while True:
                frame = await self.track.recv()
                # Clear queue to ensure we only keep the newest frame (No Lag)
                while not self.queue.empty():
                    self.queue.get_nowait()
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
            
            # Extract Stats
            fps = results.get("fps", 0.0)
            latency = results.get("latency", 0.0)
            obj_count = len(results.get("threat_data", {}))

            if self.metadata_channel and self.metadata_channel.readyState == "open":
                
                # PRIORITY 1: Critical Alert
                if critical_alert:
                    print(f"!!! CRITICAL ALERT SENT: {critical_alert}")
                    self.metadata_channel.send(json.dumps({
                        "type": "critical_alert",
                        "text": critical_alert,
                        "language": self.user_state.speech_language
                    }))
                
                # PRIORITY 2: Standard Narration
                elif narration:
                    self.metadata_channel.send(json.dumps({
                        "type": "narration_event",
                        "text": narration,
                        "language": self.user_state.speech_language
                    }))

                # PRIORITY 3: Research Stats (Send every frame or decimated)
                # We send every frame for smooth graph, frontend handles rendering
                try:
                    self.metadata_channel.send(json.dumps({
                        "type": "stats",
                        "fps": fps,
                        "latency": latency,
                        "obj_count": obj_count
                    }))
                except Exception:
                    pass # Don't crash if buffer full

            # --- FORCE SESSION LOGGING FOR TEST SERVER ---
            if self.logger:
                self.logger.log_frame_data(
                    frame_id=self.frame_count,
                    threat_data=results.get("threat_data"),
                    detections=results.get("detections"),
                    narration=narration or critical_alert, 
                    frame_img=annotated_img
                )
            self.frame_count += 1

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
        
        # --- ENFORCE 720p RESOLUTION FOR CONSISTENT PROCESSING ---
        TARGET_WIDTH, TARGET_HEIGHT = 1280, 720
        h, w = img.shape[:2]
        if h != TARGET_HEIGHT or w != TARGET_WIDTH:
            img = cv2.resize(img, (TARGET_WIDTH, TARGET_HEIGHT))
        
        results = inference_manager.process_frame(img, return_info=True)
        return results



# ... imports ...

# --- DEPENDENCY INJECTION SETUP ---
class SessionFactory:
    """
    Factory for creating session components.
    Allows for easy mocking and swapping of logging strategies.
    """
    def create_logger(self, session_name: str, record_video: bool) -> SessionLogger:
        return SessionLogger(session_name=session_name, record_video=record_video)

@lru_cache()
def get_session_factory() -> SessionFactory:
    return SessionFactory()

# ... existing code ...

@app.websocket("/Lumen-test-ws")
async def websocket_endpoint(
    websocket: WebSocket,
    factory: SessionFactory = Depends(get_session_factory)
):
    await websocket.accept()
    # ... existing setup ...
    pc = RTCPeerConnection()
    active_sessions.add(pc)
    l_track = None
    metadata_channel = None
    session_logger = None

    # ... datachannel and ready message ...

    try:
        # --- RESTORED LOGIC ---
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
        
        # USE FACTORY FOR DI
        record_video = config.get("record_session", False)
        # We inject the factory to create the logger
        session_logger = factory.create_logger(session_name="TEST_Session", record_video=record_video)

        # ... rest of the logic ...

        @pc.on("track")
        def on_track(track):
            print(f"DEBUG: Track received: kind={track.kind}, id={track.id}")
            nonlocal l_track
            if track.kind == "video":
                l_track = LumenTrack(track, pc, user_state, metadata_channel=metadata_channel, logger=session_logger)
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
        
        await websocket.send_text(json.dumps({
            "type": "init_complete",
            "status": "active"
        }))

        while pc.connectionState not in ["closed", "failed"]:
            await asyncio.sleep(1)
    finally:
        active_sessions.discard(pc)
        await pc.close()
        if session_logger:
            session_logger.close()
