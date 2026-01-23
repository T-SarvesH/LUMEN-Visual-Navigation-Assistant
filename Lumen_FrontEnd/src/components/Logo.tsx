import React from 'react';
import { Svg, Path, Circle, G, Defs, LinearGradient, Stop } from 'react-native-svg';

export const LumenLogo = ({ size = 120 }: { size?: number }) => (
  <Svg width={size} height={size} viewBox="0 0 100 100">
    <Defs>
      <LinearGradient id="bg_grad" x1="0" y1="0" x2="100" y2="100">
        <Stop offset="0" stopColor="#22c55e" stopOpacity="1" />
        <Stop offset="1" stopColor="#15803d" stopOpacity="1" />
      </LinearGradient>
    </Defs>
    
    {/* Soft Rounded Outer Background */}
    <Circle cx="50" cy="50" r="48" fill="url(#bg_grad)" />
    
    {/* The White "Vision" Shape */}
    <G transform="translate(20, 30)">
      {/* Friendly Eye Shape */}
      <Path
        d="M5 20C5 20 15 5 30 5C45 5 55 20 55 20C55 20 45 35 30 35C15 35 5 20 5 20Z"
        fill="white"
      />
      {/* Pupil with a "Compass" gap representing guidance */}
      <Circle cx="30" cy="20" r="8" fill="#15803d" />
      <Circle cx="30" cy="20" r="3" fill="white" />
    </G>
    
    {/* "Aura" Lines representing sound/feedback */}
    <Path
      d="M25 75 Q 50 65 75 75"
      stroke="white"
      strokeWidth="4"
      strokeLinecap="round"
      fill="none"
      opacity="0.6"
    />
  </Svg>
);