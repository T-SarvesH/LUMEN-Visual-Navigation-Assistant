import React, { useEffect, useRef, useState } from "react";
import { View, StyleSheet, Text, TouchableOpacity, Dimensions, Vibration } from "react-native";
import {
  RTCView,
  mediaDevices,
  RTCPeerConnection,
  RTCSessionDescription,
} from "react-native-webrtc";
import Tts from "react-native-tts";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../App";
import { useSettings } from "../context/SettingsContext";
import { getWebSocketUrl } from "../utils/ipUtils";
import ReactNativeHapticFeedback from "react-native-haptic-feedback";

const hapticOptions = {
  enableVibrateFallback: true,
  ignoreAndroidSystemSettings: true,
};

type Props = NativeStackScreenProps<RootStackParamList, "CameraCapture">;
type Phase = "startup" | "ready" | "capture" | "failed";

export default function CameraCaptureScreen({ navigation }: Props) {
  const [phase, setPhase] = useState<Phase>("startup");
  const [logs, setLogs] = useState<string[]>([]);
  const [remoteStream, setRemoteStream] = useState<any>(null);
  const [dims, setDims] = useState(Dimensions.get("window"));

  // State to track if backend neural models are loaded
  const [isPipelineReady, setIsPipelineReady] = useState(false);

  const { duration, language } = useSettings();

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const dataChannelRef = useRef<any>(null);
  const streamRef = useRef<any>(null);
  const offerSentRef = useRef(false);

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

    const onStart = (event: any) => console.log("TTS Started", event);
    const onFinish = (event: any) => console.log("TTS Finished", event);
    const onCancel = (event: any) => console.log("TTS Cancelled", event);

    // Cast to 'any' because strict types say it returns void, but runtime returns a subscription
    const startSub = Tts.addEventListener("tts-start", onStart) as any;
    const finishSub = Tts.addEventListener("tts-finish", onFinish) as any;
    const cancelSub = Tts.addEventListener("tts-cancel", onCancel) as any;

    return () => {
      // Library's removeEventListener calls deprecated 'removeListener' which crashes.
      // We use the subscription's .remove() method instead.
      if (startSub?.remove) startSub.remove();
      if (finishSub?.remove) finishSub.remove();
      if (cancelSub?.remove) cancelSub.remove();
    };
  }, [language]);

  // Main Logic (WebRTC + WebSocket)
  useEffect(() => {
    let isMounted = true;

    // 1. Setup WebSocket + Listen for Readiness
    const setupSocket = () => {
      try {
        if (!isMounted) return;
        addLog("Connecting to Server...");
        const ws = new WebSocket(getWebSocketUrl());
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
          else if (data.type === "init_complete") {
            console.log("Received init_complete (Redundant check)");
          }
        };

        ws.onerror = () => {
          if (!isMounted) return;
          addLog("WS Error. Is backend running?");
          setPhase("failed");
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

        const stream = await mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
            width: { ideal: 1280, min: 1280 },
            height: { ideal: 720, min: 720 },
            frameRate: { ideal: 30, min: 24 },
          },
          audio: false,
        });

        // SAFETY: If unmounted during getUserMedia await, stop stream immediately
        if (!isMounted) {
          stream.getTracks().forEach((t: any) => t.stop());
          return;
        }

        streamRef.current = stream;

        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        // Add Tracks
        stream.getTracks().forEach((track) => pc.addTrack(track, stream));

        // Data Channel
        const dc = pc.createDataChannel("lumen_sync");
        const dcAny = dc as any;
        dataChannelRef.current = dc;

        dcAny.onmessage = (e: { data: string }) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(e.data);
            if (data.type === "narration_event") {
              console.log("Attempting to speak:", data.text);
              console.log("Triggering Haptics (Vibration Core)...");
              // ReactNativeHapticFeedback.trigger("impactHeavy", hapticOptions);
              Vibration.vibrate(200); // 200ms basic vibration, universally supported
              try { Tts.speak(data.text); } catch (err) { console.error(err); }
            }
          } catch (err) { console.error(err); }
        };

        dcAny.onopen = () => {
          if (isMounted) addLog("DataChannel connected.");
        };

        const pcAny = pc as any;
        pcAny.ontrack = (event: any) => {
          if (isMounted && event.streams && event.streams[0]) {
            setRemoteStream(event.streams[0]);
          }
        };

        // Create Offer
        const offer = await pc.createOffer();
        if (!isMounted) return;
        await pc.setLocalDescription(offer);

        // Send Offer via existing WS
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: "offer",
            sdp: offer.sdp,
            config: { description_interval: duration, language },
          }));
        }

      } catch (err: any) {
        if (!isMounted) return;
        addLog(`Media/PC Error: ${err.message}`);
        setPhase("failed");
      }
    };

    setupSocket();

    return () => {
      console.log("Cleaning up CameraCaptureScreen resources...");
      isMounted = false;
      streamRef.current?.getTracks().forEach((t: any) => t.stop());
      pcRef.current?.close();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [duration, language]); // Re-run if settings change, though this might cause re-connection

  return (
    <View style={styles.container}>
      {/* 1. Landscape Enforcement Overlay */}
      {dims.height > dims.width && (
        <View style={styles.overlay}>
          <Text style={styles.overlayText}>PLEASE ROTATE DEVICE</Text>
          <Text style={styles.overlaySubText}>LUMEN requires Landscape Mode</Text>
        </View>
      )}

      {/* 2. Main Content (Disabled underneath if portrait, though overlay covers it) */}
      {phase === "capture" && remoteStream ? (
        <RTCView
          streamURL={remoteStream.toURL()}
          style={{ width: dims.width, height: dims.height }}
          objectFit="cover"
          mirror={false}
          zOrder={1}
        />
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
          phase === "failed" ? styles.btnError : styles.btnPrimary,
          // Fade out if disabled
          (phase !== "ready" && phase !== "failed" && !isPipelineReady) || dims.height > dims.width
            ? { opacity: 0.5, backgroundColor: "#27272a" } // Zinc-800 disabled state
            : {}
        ]}
        disabled={(phase !== "ready" && phase !== "failed") || dims.height > dims.width}
        onPress={() =>
          phase === "ready" ? setPhase("capture") : navigation.goBack()
        }
      >
        <Text style={styles.btnText}>
          {/* ... existing text logic ... */}
          {/* Just keep existing text logic, but the button checks disabled state */}
          {phase === "ready"
            ? "START VISUAL ASSISTANCE"
            : phase === "failed"
              ? "RETURN HOME"
              : isPipelineReady ? "FINALIZING..." : "CONNECTING TO SERVER..."}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#09090b" }, // Zinc-950 equivalent
  terminal: {
    flex: 1,
    backgroundColor: "#18181b", // Zinc-900
    margin: 16,
    borderRadius: 16,
    padding: 20,
    justifyContent: "flex-end", // Logs start from bottom like terminal
    borderWidth: 1,
    borderColor: "#27272a", // Zinc-800
    elevation: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  logText: {
    color: "#4ade80", // Green-400
    fontFamily: "monospace",
    fontSize: 15, // Optimal size for readability
    marginBottom: 8,
    lineHeight: 22,
  },
  button: {
    marginHorizontal: 16,
    marginBottom: 24,
    paddingVertical: 20,
    alignItems: "center",
    borderRadius: 9999, // Pill shape
    elevation: 6,
    shadowColor: "#22c55e", // Green shadow
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  btnPrimary: {
    backgroundColor: "#22c55e", // Lumen Green
  },
  btnError: {
    backgroundColor: "#ef4444", // Red-500
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
