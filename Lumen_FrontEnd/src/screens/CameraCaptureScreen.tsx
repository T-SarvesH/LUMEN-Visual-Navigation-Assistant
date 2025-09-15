import React, { useEffect, useState } from 'react';
import { View, Text, Platform, PermissionsAndroid } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Camera, useCameraDevice } from 'react-native-vision-camera';
import { vioService } from '../services/VioService'; // your VIO JS service
import { styled } from 'nativewind';

const StyledView = styled(View);
const StyledText = styled(Text);

const CameraCaptureScreen: React.FC = () => {
  const device = useCameraDevice('back');
  const [serverResponse, setServerResponse] = useState('Initializing...');
  const [isCameraActive, setIsCameraActive] = useState(true);

  useEffect(() => {
    const initializeApp = async () => {
      // Request camera permission on Android
      if (Platform.OS === 'android') {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.CAMERA
        );
        if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
          console.log('Camera permission denied');
          setIsCameraActive(false);
          return;
        }
      }

      // Connect VioService
      vioService.connect((message: string) => setServerResponse(message));

      // Start streaming after 1s
      const streamTimeout = setTimeout(() => vioService.startStreaming(), 1000);
      return () => clearTimeout(streamTimeout);
    };

    initializeApp();

    return () => vioService.disconnect();
  }, []);

  if (!device) {
    return (
      <SafeAreaView className="flex-1 justify-center items-center bg-black">
        <StyledText className="text-white text-lg">No camera device found</StyledText>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-black relative">
      <Camera style={{ flex: 1 }} device={device} isActive={isCameraActive} />

      <StyledView className="absolute bottom-8 w-11/12 self-center bg-black/60 p-4 rounded-lg">
        <StyledText className="text-white text-xl font-bold text-center mb-2">
          Lumen Data Capture
        </StyledText>
        <StyledText className="text-white text-base text-center">
          Server Status: {serverResponse}
        </StyledText>
      </StyledView>
    </SafeAreaView>
  );
};

export default CameraCaptureScreen;
