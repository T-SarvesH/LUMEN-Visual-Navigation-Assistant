import React, { useEffect, useRef, useState } from "react";
import { View, StyleSheet, Text, TouchableOpacity, Dimensions } from "react-native";
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

type Props = NativeStackScreenProps<RootStackParamList, "CameraCapture">;
type Phase = "startup" | "ready" | "capture" | "failed";

export default function CameraCaptureScreen({ navigation }: Props) {
  const [phase, setPhase] = useState<Phase>("startup");
  const [logs, setLogs] = useState<string[]>([]);
  const [remoteStream, setRemoteStream] = useState<any>(null);
  const [dims, setDims] = useState(Dimensions.get("window"));

  const { duration, language } = useSettings();

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const dataChannelRef = useRef<any>(null);
  const streamRef = useRef<any>(null);
  const offerSentRef = useRef(false);

  const addLog = (msg: string) => {
    setLogs((prev) => [...prev, `> ${msg}`].slice(-10));
  };

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

    const startup = async () => {
      try {
        addLog("Initializing 720p Neural Pipeline...");

        const stream = await mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
            width: { ideal: 1280, min: 1280 },
            height: { ideal: 720, min: 720 },
            frameRate: { ideal: 30, min: 24 },
          },
          audio: false,
        });

        streamRef.current = stream;

        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        const pcAny = pc as any;

        // ✅ FIX: Typed-safe event wiring
        pcAny.ontrack = (event: any) => {
          if (event.streams && event.streams[0]) {
            setRemoteStream(event.streams[0]);
          }
        };

        // DataChannel for narration + orientation
        const dc = pc.createDataChannel("lumen_sync");
        const dcAny = dc as any;
        dataChannelRef.current = dc;

        dcAny.onmessage = (e: { data: string }) => {
          try {
            const data = JSON.parse(e.data);
            if (data.type === "narration_event") {
              Tts.stop();
              Tts.speak(data.text);
            }
          } catch (err) {
            console.error("Data parsing error:", err);
          }
        };

        dcAny.onopen = () => addLog("DataChannel connected.");

        stream.getTracks().forEach((track) => pc.addTrack(track, stream));

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const ws = new WebSocket("ws://192.168.29.63:8001/Lumen-ws");
        wsRef.current = ws;

        ws.onopen = () => {
          if (offerSentRef.current) return;
          offerSentRef.current = true;

          ws.send(
            JSON.stringify({
              type: "offer",
              sdp: offer.sdp,
              config: {
                description_interval: duration,
                language,
              },
            })
          );
        };

        ws.onmessage = async (msg) => {
          const data = JSON.parse(msg.data);
          if (data.type === "answer") {
            await pc.setRemoteDescription(new RTCSessionDescription(data));
            addLog("System check complete.");
            Tts.speak("LUMEN is active.");
            setPhase("ready");
          }
        };

        ws.onerror = () => setPhase("failed");
      } catch (err: any) {
        addLog(`Critical failure: ${err.message}`);
        setPhase("failed");
      }
    };

    startup();

    return () => {
      subscription.remove();
      if (phase !== "capture") {
        streamRef.current?.getTracks().forEach((t: any) => t.stop());
        pcRef.current?.close();
        wsRef.current?.close();
      }
    };
  }, [duration, language]);

  return (
    <View style={styles.container}>
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
        ]}
        onPress={() =>
          phase === "ready" ? setPhase("capture") : navigation.goBack()
        }
      >
        <Text style={styles.btnText}>
          {phase === "ready"
            ? "START VISUAL ASSISTANCE"
            : phase === "failed"
            ? "RETURN HOME"
            : "INITIALIZING..."}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "black" },
  terminal: {
    flex: 1,
    backgroundColor: "#050505",
    padding: 20,
    justifyContent: "center",
  },
  logText: {
    color: "#00FF00",
    fontFamily: "monospace",
    fontSize: 13,
    marginBottom: 6,
  },
  button: { paddingVertical: 18, alignItems: "center" },
  btnPrimary: {
    backgroundColor: "#111",
    borderTopWidth: 1,
    borderColor: "#333",
  },
  btnError: { backgroundColor: "#CC0000" },
  btnText: { color: "#FFF", fontWeight: "bold", letterSpacing: 1 },
});
