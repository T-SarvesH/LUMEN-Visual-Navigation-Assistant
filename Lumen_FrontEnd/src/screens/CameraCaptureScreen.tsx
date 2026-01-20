import React, { useEffect, useState } from "react";
import { View, StyleSheet } from "react-native";
import {
  RTCPeerConnection,
  mediaDevices,
  RTCView,
  MediaStream,
  RTCSessionDescription,
} from "react-native-webrtc";
import { useSettings } from "../context/SettingsContext";

export default function CameraCaptureScreen() {
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const { duration, language } = useSettings();

  useEffect(() => {
    const init = async () => {
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
      });
      
      (pc as any).ontrack = (event: any) => {
        const [stream] = event.streams;
        setRemoteStream(stream);
      };

      // Use onaddstream as a fallback for older versions
      (pc as any).onaddstream = (event: any) => {
        setRemoteStream(event.stream);
      };

      const stream = await mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: 1280,
          height: 720,
          frameRate: 30,
        },
        audio: false,
      });
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const ws = new WebSocket("ws://192.168.29.63:8001/Lumen-ws");

      ws.onopen = () => {
        const payload = {
          type: "offer",
          sdp: offer.sdp,
          config: {
            description_interval: duration,
            language: language,
            client_id: "LUMEN_HANDHELD_V1"
          }
        };
        
        ws.send(JSON.stringify(payload));
      };

      ws.onmessage = async (msg) => {
        const data = JSON.parse(msg.data);
        
        if (data.type === "answer") {
          await pc.setRemoteDescription(new RTCSessionDescription(data));
        }
      };

      ws.onerror = (e) => {
        // Handle websocket connectivity issues here
      };
    };

    init();
  }, []);

  return (
    <View style={styles.container}>
      {remoteStream && (
        <RTCView
          streamURL={(remoteStream as any).toURL()}
          style={styles.video}
          objectFit="cover"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "black" },
  video: { flex: 1 },
});