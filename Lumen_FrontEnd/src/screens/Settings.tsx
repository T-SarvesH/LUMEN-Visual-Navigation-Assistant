import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, Vibration } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ArrowLeft, Languages, Timer, Smartphone } from 'lucide-react-native';
import { styled } from 'nativewind';
import { SettingsProvider, useSettings } from '../context/SettingsContext';
import TTSTester from '../components/TTS';

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

const SettingsScreen = ({ navigation }: any) => {
  const {
    duration, setDuration,
    language, setLanguage,
    isDevMode, setIsDevMode,
    isRecordingEnabled, setIsRecordingEnabled
  } = useSettings();

  const isActive = isDevMode; // Alias for color logic in replacement chunk

  const OptionButton = ({ label, isActive, onPress }: any) => (
    <StyledTouchable
      onPress={onPress}
      className={`flex-1 py-4 rounded-xl border-2 items-center justify-center ${isActive ? 'bg-green-500 border-green-400' : 'bg-zinc-800 border-zinc-700'
        }`}
    >
      <StyledText className={`font-bold ${isActive ? 'text-zinc-900' : 'text-gray-400'}`}>
        {label}
      </StyledText>
    </StyledTouchable>
  );

  return (
    <SafeAreaView className="flex-1 bg-zinc-900 p-5">
      {/* Header */}
      <StyledView className="flex-row items-center mb-10">
        <StyledTouchable
          onPress={() => navigation.goBack()}
          className="p-2 bg-zinc-800 rounded-full mr-4"
        >
          <ArrowLeft color="#22c55e" size={24} />
        </StyledTouchable>
        <StyledText className="text-3xl font-bold text-white">Settings</StyledText>
      </StyledView>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Language Selection */}
        <StyledView className="mb-8">
          <StyledView className="flex-row items-center mb-4">
            <Languages color="#22c55e" size={20} className="mr-2" />
            <StyledText className="text-xl text-gray-300 font-semibold">Speech Language</StyledText>
          </StyledView>
          <StyledView className="flex-row space-x-4">
            <OptionButton
              label="English"
              isActive={language === 'English'}
              onPress={() => setLanguage('English')}
            />
            <OptionButton
              label="Hindi"
              isActive={language === 'Hindi'}
              onPress={() => setLanguage('Hindi')}
            />
          </StyledView>
        </StyledView>

        {/* Duration Selection */}
        <StyledView className="mb-8">
          <StyledView className="flex-row items-center mb-4">
            <Timer color="#22c55e" size={20} className="mr-2" />
            <StyledText className="text-xl text-gray-300 font-semibold">Description Interval</StyledText>
          </StyledView>
          <StyledView className="flex-row space-x-2">
            {[15, 20, 30].map((d) => (
              <OptionButton
                key={d}
                label={`${d}s`}
                isActive={duration === d}
                onPress={() => setDuration(d as any)}
              />
            ))}
          </StyledView>
        </StyledView>
        {/* Haptic Feedback Test */}
        <StyledView className="mb-8">
          <StyledView className="flex-row items-center mb-4">
            <Smartphone color="#22c55e" size={20} className="mr-2" />
            <StyledText className="text-xl text-gray-300 font-semibold">Haptic Feedback</StyledText>
          </StyledView>
          <StyledTouchable
            onPress={() => Vibration.vibrate(200)}
            className="flex-row items-center justify-center py-4 rounded-xl bg-zinc-800 border-2 border-zinc-700 active:bg-green-500 active:border-green-400"
          >
            <Smartphone color="#FFF" size={20} className="mr-2" />
            <StyledText className="text-white font-bold">TEST VIBRATION</StyledText>
          </StyledTouchable>
        </StyledView>

        {/* Developer Mode Toggle */}
        <StyledView className="mb-8 p-4 bg-zinc-800 rounded-xl border-2 border-zinc-700">
          <StyledView className="flex-row items-center justify-between mb-2">
            <StyledView className="flex-row items-center">
              <Smartphone color={isDevMode ? "#ef4444" : "#22c55e"} size={20} className="mr-2" />
              <StyledText className="text-xl text-gray-300 font-semibold">Developer Mode</StyledText>
            </StyledView>
            <StyledTouchable
              onPress={() => setIsDevMode(!isDevMode)}
              className={`px-4 py-2 rounded-lg ${isDevMode ? 'bg-green-500' : 'bg-red-500'}`}
            >
              <StyledText className="text-white font-bold">{isDevMode ? "ON" : "OFF"}</StyledText>
            </StyledTouchable>
          </StyledView>
          <StyledText className="text-gray-400 text-sm mb-4">
            Enables visual bounding boxes, FPS stats, and research data tagging.
          </StyledText>

          {/* Video Recording Sub-Toggle (Only visible if Dev Mode is ON, or always visible? User said "we can also save recordings") 
              Let's make it always visible but grouped near research settings.
          */}
          <View className="h-[1px] bg-zinc-700 my-2" />

          <StyledView className="flex-row items-center justify-between mt-2">
            <StyledView className="flex-row items-center">
              {/* Use a different icon or recycle Smartphone for now */}
              <StyledText className="text-lg text-gray-300">Record Session Video</StyledText>
            </StyledView>
            <StyledTouchable
              onPress={() => setIsRecordingEnabled(!isRecordingEnabled)}
              className={`px-4 py-2 rounded-lg ${isRecordingEnabled ? 'bg-green-500' : 'bg-zinc-600'}`}
            >
              <StyledText className="text-white font-bold">{isRecordingEnabled ? "REC" : "OFF"}</StyledText>
            </StyledTouchable>
          </StyledView>
          <StyledText className="text-gray-500 text-xs mt-1">
            Saves MP4 video to server. Consumes storage space.
          </StyledText>
        </StyledView>

        <TTSTester />
      </ScrollView>
    </SafeAreaView>
  );
};

export default SettingsScreen;