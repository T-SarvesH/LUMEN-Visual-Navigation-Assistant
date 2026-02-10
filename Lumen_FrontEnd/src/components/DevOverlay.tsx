import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { styled } from 'nativewind';


const StyledView = styled(View);
const StyledText = styled(Text);

interface Props {
    fps: number;
    latency: number;
    threats: any[]; // List of detected objects with coords
    isActive: boolean;
}

const DevOverlay = ({ fps, latency, threats, isActive }: Props) => {
    if (!isActive) return null;

    // We use absolute positioning to overlay on top of the camera
    return (
        <View style={StyleSheet.absoluteFill} pointerEvents="none">
            {/* 1. FPS / Latency Stats Box */}
            <StyledView className="absolute top-10 left-4 bg-black/60 p-2 rounded-lg border border-white/20">
                <StyledText className="text-green-400 font-bold text-xs">FPS: {fps.toFixed(1)}</StyledText>
                <StyledText className="text-yellow-400 font-bold text-xs">LAT: {latency.toFixed(0)}ms</StyledText>
                {/* <StyledText className="text-blue-400 font-bold text-xs">OBJS: {threats ? threats.length : 0}</StyledText> */}
            </StyledView>

            {/* 2. Visual Bounding Boxes (Simulated for WebRTC Stream) 
               Note: Since the video is a WebRTC stream, we can't easily draw *on* the video 
               perfectly synced without complex canvas work. 
               However, the backend ALREADY draws bounding boxes on the video frame itself ("annotated_frame").
               
               So the "DevOverlay" mainly provides the *STATS* which are not burned into the video.
               The "Visual Bounding Boxes" are handled by the backend drawing on the frame.
            */}
        </View>
    );
};

export default DevOverlay;
