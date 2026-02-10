import React from 'react';
import { Text, View, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styled } from 'nativewind';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../App';
import { Settings, Info, Video, VideoOff } from 'lucide-react-native';
import { LumenLogo } from '../components/Logo';
import { useSettings } from '../context/SettingsContext';

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

type LandingScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Landing'>;
};

const LandingScreen: React.FC<LandingScreenProps> = ({ navigation }) => {
  const { isDevMode, setIsDevMode, setIsRecordingEnabled } = useSettings();
  return (
    <SafeAreaView className="flex-1 bg-zinc-900 p-5 justify-between">

      {/* Updated Header Section: Info (Left) and Settings (Right) */}
      <StyledView className="flex-row justify-between items-center">
        {/* About Us (Top Left) */}
        <StyledTouchable
          onPress={() => navigation.navigate('AboutUs')}
          className="p-3 rounded-full bg-zinc-800 border border-zinc-700"
          accessibilityLabel="About Project Lumen"
        >
          <Info color="#22c55e" size={24} strokeWidth={2.5} />
        </StyledTouchable>

        {/* Settings (Top Right) */}
        <StyledTouchable
          onPress={() => navigation.navigate('Settings')}
          className="p-3 rounded-full bg-zinc-800 border border-zinc-700"
          accessibilityLabel="Open Developer Settings"
        >
          <Settings color="#22c55e" size={24} strokeWidth={2.5} />
        </StyledTouchable>
      </StyledView>

      {/* Main Content */}
      <StyledView className="flex-1 justify-center items-center">
        <StyledView className="mb-6">
          <LumenLogo size={100} />
        </StyledView>

        <StyledView className="mb-4 p-4 rounded-2xl bg-zinc-800 border border-green-500/30">
          <StyledText className="text-6xl font-bold text-white">Lumen</StyledText>
        </StyledView>
        <StyledText className="text-lg text-gray-400 text-center px-4 mb-8">
          Your visual companion for navigating the world.
        </StyledText>

        {/* MODE SELECTOR */}
        <StyledView className="flex-row bg-zinc-900/80 p-1.5 rounded-2xl border border-zinc-700/50 w-full max-w-[340px] mb-8 shadow-inner">
          <StyledTouchable
            onPress={() => setIsDevMode(false)}
            className={`flex-1 py-4 rounded-xl items-center transition-all ${!isDevMode ? 'bg-zinc-800 shadow-md' : 'bg-transparent'}`}
          >
            <StyledText className={`font-bold text-xs tracking-[2px] ${!isDevMode ? 'text-green-400' : 'text-zinc-500'}`}>
              PRODUCTION
            </StyledText>
          </StyledTouchable>
          <StyledTouchable
            onPress={() => setIsDevMode(true)}
            className={`flex-1 py-4 rounded-xl items-center transition-all ${isDevMode ? 'bg-zinc-800 shadow-md' : 'bg-transparent'}`}
          >
            <StyledText className={`font-bold text-xs tracking-[2px] ${isDevMode ? 'text-red-400' : 'text-zinc-500'}`}>
              RESEARCH
            </StyledText>
          </StyledTouchable>
        </StyledView>
      </StyledView>

      {/* Action Button */}
      {/* Action Buttons */}
      {!isDevMode ? (
        <StyledTouchable
          className="w-full py-5 rounded-full items-center justify-center shadow-lg active:scale-95 transition-transform bg-green-500 shadow-green-500/50"
          onPress={() => {
            setIsRecordingEnabled(false); // Default logic
            navigation.navigate('CameraCapture');
          }}
        >
          <StyledText className="text-white text-xl font-extrabold uppercase tracking-widest">
            START ASSISTANT
          </StyledText>
        </StyledTouchable>
      ) : (
        <StyledView className="w-full flex-col space-y-3 gap-3">
          {/* Primary: Record */}
          <StyledTouchable
            className="w-full py-4 rounded-2xl flex-row items-center justify-center bg-red-600 shadow-lg shadow-red-600/40 active:scale-[0.98] transition-all border border-red-500/50"
            onPress={() => {
              setIsRecordingEnabled(true);
              navigation.navigate('CameraCapture');
            }}
          >
            <Video color="white" size={24} strokeWidth={2.5} style={{ marginRight: 12 }} />
            <StyledText className="text-white text-lg font-black uppercase tracking-widest">
              RECORD SESSION
            </StyledText>
          </StyledTouchable>

          {/* Secondary: No Record */}
          <StyledTouchable
            className="w-full py-4 rounded-2xl flex-row items-center justify-center bg-zinc-800/80 border-2 border-red-900/50 active:scale-[0.98] transition-all"
            onPress={() => {
              setIsRecordingEnabled(false);
              navigation.navigate('CameraCapture');
            }}
          >
            <VideoOff color="#ef4444" size={22} strokeWidth={2.5} style={{ marginRight: 12 }} />
            <StyledText className="text-red-500 text-lg font-bold uppercase tracking-widest opacity-90">
              NO RECORDING
            </StyledText>
          </StyledTouchable>
        </StyledView>
      )}
    </SafeAreaView>
  );
};

export default LandingScreen;