import React, { useEffect, useRef, useState } from "react";
import { View, StyleSheet, Text, TouchableOpacity, Dimensions, Vibration } from "react-native";
import {
  RTCView,
  mediaDevices,
  RTCPeerConnection,
  RTCSessionDescription,
  MediaStream,
} from "react-native-webrtc";
import Tts from "react-native-tts";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../App";
import { useSettings } from "../context/SettingsContext";
import { getWebSocketUrl } from "../utils/ipUtils";
import ReactNativeHapticFeedback from "react-native-haptic-feedback";
import DevOverlay from "../components/DevOverlay";

const hapticOptions = {
  enableVibrateFallback: true,
  ignoreAndroidSystemSettings: true,
};

type Props = NativeStackScreenProps<RootStackParamList, "CameraCapture">;
type Phase = "startup" | "ready" | "capture" | "failed";

export default function CameraCaptureScreen({ navigation }: Props) {
  const [phase, setPhase] = useState<Phase>("startup");
  const [logs, setLogs] = useState<string[]>([]);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [dims, setDims] = useState(Dimensions.get("window"));

  // State to track if backend neural models are loaded
  const [isPipelineReady, setIsPipelineReady] = useState(false);

  // Dev Stats
  const [fps, setFps] = useState(0);
  const [latency, setLatency] = useState(0);
  const [threatCount, setThreatCount] = useState(0);

  const { duration, language, isDevMode, isRecordingEnabled } = useSettings();

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const dataChannelRef = useRef<any>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const addLog = (msg: string) => {
    setLogs((prev) => [...prev, `> ${msg}`].slice(-10));
  };

  // Dimensions & Orientation Handler
  useEffect(() => {
    const subscription = Dimensions.addEventListener("change", ({ window }) => {
      setDims(window);
      const orientation = window.width > window.height ? "landscape" : "portrait";
      if (dataChannelRef.current?.readyState === "open") {
        dataChannelRef.current.send(
          JSON.stringify({ type: "orientation_sync", value: orientation })
        );
      }
    });
    return () => subscription.remove();
  }, []);

  // TTS Initialization
  useEffect(() => {
    Tts.getInitStatus().then(() => {
      Tts.setDefaultLanguage(language);
      Tts.setDucking(true);
      console.log(`TTS Initialized. Language: ${language}`);
    }, (err) => {
      if (err.code === 'no_engine') {
        Tts.requestInstallEngine();
      }
      console.error("TTS Init error:", err);
    });

    return () => {
      // Cleanup listeners if necessary, though Tts is global usually
    };
  }, [language]);

  // Main Logic (WebRTC + WebSocket)
  useEffect(() => {
    let isMounted = true;

    // 1. Setup WebSocket + Listen for Readiness
    const setupSocket = () => {
      try {
        if (!isMounted) return;
        addLog(`Connecting to ${isDevMode ? "Test" : "Main"} Server...`);
        // Connect to 8002 if DevMode is true, else 8001
        const ws = new WebSocket(getWebSocketUrl(isDevMode));
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) { ws.close(); return; }
          addLog("WS Connected. Waiting for Neural Pipeline...");
        };

        ws.onmessage = async (msg) => {
          if (!isMounted) return;
          const data = JSON.parse(msg.data);
          console.log("WS Received:", data.type);

          if (data.type === "server_ready") {
            addLog("Neural Pipeline Ready (Models Loaded).");
            addLog("Initializing Camera & Neural Uplink...");
            setIsPipelineReady(true);
            // NOW start the heavy lifting
            setupMediaAndPeerConnection(ws);
          }
          else if (data.type === "init_complete") {
            // Redundant but confirms readiness
            setIsPipelineReady(true);
          }
          else if (data.type === "answer") {
            if (pcRef.current) {
              await pcRef.current.setRemoteDescription(new RTCSessionDescription(data));
              if (!isMounted) return;
              addLog("System Ready.");
              setIsPipelineReady(true);
              setPhase("ready");
              Vibration.vibrate(200);
              Tts.speak("LUMEN is active.");
            }
          }
        };

        ws.onerror = (e) => {
          if (!isMounted) return;
          console.error("WS Error:", e);
          addLog("WS Error. Is backend running?");
          setPhase("failed");
        };

        ws.onclose = () => {
          if (isMounted) addLog("WS Closed.");
        };

      } catch (e: any) {
        if (!isMounted) return;
        addLog(`WS Setup Failed: ${e.message}`);
        setPhase("failed");
      }
    };

    // 2. Heavy Setup (Camera + WebRTC) - Triggered ONLY after server_ready
    const setupMediaAndPeerConnection = async (ws: WebSocket) => {
      try {
        if (!isMounted) return;

        // Get User Media
        const stream = await mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
            width: { exact: 1280 },
            height: { exact: 720 },
            frameRate: { ideal: 30, min: 24 },
          },
          audio: false,
        }) as MediaStream;

        if (!isMounted) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        streamRef.current = stream;
        setLocalStream(stream);

        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        stream.getTracks().forEach((track) => pc.addTrack(track, stream));

        const dc = pc.createDataChannel("lumen_sync");
        const dcAny = dc as any;
        dataChannelRef.current = dc;

        dcAny.onmessage = (e: { data: string }) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(e.data);

            // STATS
            if (data.type === "stats") {
              setFps(data.fps);
              setLatency(data.latency);
              setThreatCount(data.obj_count);
            }
            // CRITICAL ALERT
            else if (data.type === "critical_alert") {
              console.log("CRITICAL ALERT RECEIVED:", data.text);
              Vibration.vibrate([0, 500, 100, 500]);
              try {
                Tts.stop();
                Tts.speak(data.text);
              } catch (err) { console.error(err); }
            }
            // STANDARD NARRATION
            else if (data.type === "narration_event") {
              ReactNativeHapticFeedback.trigger("impactLight", hapticOptions);
              try { Tts.speak(data.text); } catch (err) { console.error(err); }
            }
          } catch (err) { console.error(err); }
        };

        const pcAny = pc as any;
        pcAny.ontrack = (event: any) => {
          if (isMounted && event.streams && event.streams[0]) {
            setRemoteStream(event.streams[0]);
          }
        };

        const offer = await pc.createOffer(undefined);
        if (!isMounted) return;
        await pc.setLocalDescription(offer);

        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: "offer",
            sdp: offer.sdp,
            config: {
              description_interval: duration,
              language,
              record_session: isRecordingEnabled
            },
          }));
        }

      } catch (err: any) {
        if (!isMounted) return;
        console.error("Media Error:", err);
        addLog(`Media/PC Error: ${err.message}`);
        setPhase("failed");
      }
    };

    setupSocket();

    return () => {
      console.log("Cleaning up CameraCaptureScreen resources...");
      isMounted = false;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      pcRef.current?.close();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [duration, language, isDevMode, isRecordingEnabled]);

  return (
    <View style={styles.container}>
      {dims.height > dims.width && (
        <View style={styles.overlay}>
          <Text style={styles.overlayText}>PLEASE ROTATE DEVICE</Text>
          <Text style={styles.overlaySubText}>LUMEN requires Landscape Mode</Text>
        </View>
      )}

      {/* Render Remote Stream if capturing, else Terminal or Local if needed (usually just Terminal until ready) */}
      {phase === "capture" && remoteStream ? (
        <>
          <RTCView
            streamURL={remoteStream.toURL()}
            style={{ width: dims.width, height: dims.height }}
            objectFit="cover"
            mirror={false}
            zOrder={1}
          />
          <DevOverlay
            isActive={isDevMode}
            fps={fps}
            latency={latency}
            threats={[]}
          />
        </>
      ) : (
        <View style={styles.terminal}>
          {logs.map((log, i) => (
            <Text key={i} style={styles.logText}>
              {log}
            </Text>
          ))}
        </View>
      )}

      <TouchableOpacity
        style={[
          styles.button,
          (phase === "failed" || phase === "capture") ? styles.btnError : styles.btnPrimary,
          (phase !== "ready" && phase !== "failed" && phase !== "capture" && !isPipelineReady) || dims.height > dims.width
            ? { opacity: 0.5, backgroundColor: "#27272a", shadowOpacity: 0 }
            : {}
        ]}
        disabled={(phase !== "ready" && phase !== "failed" && phase !== "capture") || dims.height > dims.width}
        onPress={() =>
          phase === "ready" ? setPhase("capture") : navigation.goBack()
        }
      >
        <Text style={styles.btnText}>
          {phase === "ready"
            ? "START VISUAL ASSISTANCE"
            : phase === "capture"
              ? "STOP SESSION"
              : phase === "failed"
                ? "RETURN HOME"
                : isPipelineReady ? "SYSTEM READY" : "CONNECTING..."}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#09090b" },
  terminal: {
    flex: 1,
    backgroundColor: "#18181b",
    margin: 16,
    borderRadius: 16,
    padding: 20,
    justifyContent: "flex-end",
    borderWidth: 1,
    borderColor: "#27272a",
    elevation: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  logText: {
    color: "#4ade80",
    fontFamily: "monospace",
    fontSize: 15,
    marginBottom: 8,
    lineHeight: 22,
  },
  button: {
    marginHorizontal: 16,
    marginBottom: 24,
    paddingVertical: 20,
    alignItems: "center",
    borderRadius: 9999,
    elevation: 6,
    shadowColor: "#22c55e",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  btnPrimary: {
    backgroundColor: "#22c55e",
  },
  btnError: {
    backgroundColor: "#ef4444",
  },
  btnText: {
    color: "#FFF",
    fontWeight: "800",
    fontSize: 18,
    letterSpacing: 1.5,
    textTransform: "uppercase",
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "#000",
    zIndex: 999,
    justifyContent: "center",
    alignItems: "center",
  },
  overlayText: {
    color: "#ef4444",
    fontSize: 28,
    fontWeight: "900",
    marginBottom: 16,
    letterSpacing: 2,
    textTransform: "uppercase",
  },
  overlaySubText: {
    color: "#a1a1aa",
    fontSize: 18,
    fontWeight: "500",
  },
});
