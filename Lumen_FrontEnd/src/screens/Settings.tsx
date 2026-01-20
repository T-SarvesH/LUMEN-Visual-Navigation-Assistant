import React from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ArrowLeft, Languages, Timer } from 'lucide-react-native';
import { styled } from 'nativewind';
import { SettingsProvider, useSettings } from '../context/SettingsContext';
import TTSTester from '../components/TTS';

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

const SettingsScreen = ({ navigation }: any) => {
  const { duration, setDuration, language, setLanguage } = useSettings();

  const OptionButton = ({ label, isActive, onPress }: any) => (
    <StyledTouchable
      onPress={onPress}
      className={`flex-1 py-4 rounded-xl border-2 items-center justify-center ${
        isActive ? 'bg-green-500 border-green-400' : 'bg-zinc-800 border-zinc-700'
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
        <TTSTester/>
      </ScrollView>
    </SafeAreaView>
  );
};

export default SettingsScreen;