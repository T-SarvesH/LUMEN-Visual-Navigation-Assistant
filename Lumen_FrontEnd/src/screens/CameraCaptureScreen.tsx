import React, { useEffect, useState } from 'react';
import { View, Text, Platform, PermissionsAndroid } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Camera, useCameraDevice, useFrameProcessor } from 'react-native-vision-camera';
import { styled } from 'nativewind';
import { vioService } from '../services/VioService';

const StyledView = styled(View);
const StyledText = styled(Text);

const CameraCaptureScreen: React.FC = () => {
  const device = useCameraDevice('back');
  const [serverResponse, setServerResponse] = useState('Initializing...');
  const [isCameraActive, setIsCameraActive] = useState(true);
  const [detections, setDetections] = useState<any[]>([]);
  const [frameTimestamp, setFrameTimestamp] = useState<string | null>(null);

  const frameProcessor = useFrameProcessor((frame: any) => {
    'worklet';
    try {
      if (!frame.planes || frame.planes.length < 3) return;

      const yPlane = frame.planes[0].bytes;
      const uPlane = frame.planes[1].bytes;
      const vPlane = frame.planes[2].bytes;

      const rawBytes = new Uint8Array(yPlane.length + uPlane.length + vPlane.length);
      rawBytes.set(yPlane, 0);
      rawBytes.set(uPlane, yPlane.length);
      rawBytes.set(vPlane, yPlane.length + uPlane.length);

      vioService.updateCameraFrame(rawBytes, frame.width, frame.height);
    } catch (err) {
      console.log('Frame processor error', err);
    }
  }, []);

  useEffect(() => {
    const initializeApp = async () => {
      if (Platform.OS === 'android') {
        const granted = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA);
        if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
          console.log('Camera permission denied');
          setIsCameraActive(false);
          return;
        }
      }

      vioService.connect((message: string) => {
        try {
          const parsed = JSON.parse(message);
          if (parsed.detected_objects) setDetections(parsed.detected_objects);
          if (parsed.timeFrame) setFrameTimestamp(parsed.timeFrame);
          setServerResponse(parsed.status || message);
        } catch {
          setServerResponse(message);
        }
      });

      return () => vioService.disconnect();
    };

    initializeApp();
  }, []);

  if (!device) return (
    <SafeAreaView className="flex-1 justify-center items-center bg-black">
      <StyledText className="text-white text-lg">No camera device found</StyledText>
    </SafeAreaView>
  );

  return (
    <SafeAreaView className="flex-1 bg-black relative">
      <Camera
        style={{ flex: 1 }}
        device={device}
        isActive={isCameraActive}
        frameProcessor={frameProcessor}
      />

      <StyledView className="absolute bottom-8 w-11/12 self-center bg-black/60 p-4 rounded-lg">
        <StyledText className="text-white text-xl font-bold text-center mb-2">Lumen Data Capture</StyledText>
        <StyledText className="text-white text-base text-center">Server Status: {serverResponse}</StyledText>
      </StyledView>

      <StyledView className="absolute bottom-24 w-11/12 self-center bg-black/60 p-2 rounded-lg">
        <StyledText className="text-white text-center text-sm">Frame Timestamp: {frameTimestamp || 'N/A'}</StyledText>
      </StyledView>

      {detections.map((det, idx) => {
        const [x1, y1, x2, y2] = det.xyxy;
        return (
          <StyledView key={idx} className="absolute border-2 border-red-500 rounded"
            style={{ left: x1, top: y1, width: x2 - x1, height: y2 - y1 }}>
            <StyledText className="text-white text-xs bg-red-500/70 px-1">
              {det.objClass} ({(det.conf * 100).toFixed(1)}%)
            </StyledText>
          </StyledView>
        );
      })}
    </SafeAreaView>
  );
};

export default CameraCaptureScreen;
