import React, { useEffect, useState } from "react";
import { View, StyleSheet } from "react-native";
import {
  RTCPeerConnection,
  mediaDevices,
  RTCView,
  MediaStream,
} from "react-native-webrtc";

export default function CameraCaptureScreen() {
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);

  useEffect(() => {
    const init = async () => {
      const pc = new RTCPeerConnection();

      // ✅ Handle incoming video from backend
      (pc as any).ontrack = (event: any) => {
        const [stream] = event.streams;
        setRemoteStream(stream);
      };

      // ✅ Get local camera
      const stream = await mediaDevices.getUserMedia({
        video: {

          facingMode: "environment", // "environment" = rear camera, "user" = front camera
          width: 1920,
          height: 1080,
          frameRate: 60,
        },
        audio: false,
      });
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));

      // ✅ Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // ✅ Connect WebSocket to backend
      const ws = new WebSocket("ws://192.168.29.63:8001/Lumen-ws");

      ws.onopen = () => {
        ws.send(JSON.stringify(offer));
      };

      ws.onmessage = async (msg) => {
        const data = JSON.parse(msg.data);
        await pc.setRemoteDescription(data);
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
