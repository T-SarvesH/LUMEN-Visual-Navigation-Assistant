import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import Tts from 'react-native-tts';
import { Play, Volume2 } from 'lucide-react-native';
import { styled } from 'nativewind';
import { useSettings } from '../context/SettingsContext';

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

const TTSTester = () => {
  const { language } = useSettings();

  const testSpeech = () => {
    // Ensure the native engine is ready before calling any methods
    Tts.getInitStatus().then(() => {
      const langCode = language === 'Hindi' ? 'hi-IN' : 'en-US';
      const message = language === 'Hindi'
        ? "नमस्ते, लुमेन अब हिंदी में बात करने के लिए तैयार है।"
        : "Hello, Lumen is now ready to assist you in English.";

      // Use a safety check for the Tts object itself
      if (Tts) {
        Tts.stop();
        Tts.setDefaultLanguage(langCode);
        Tts.speak(message);
      }
    }).catch((err) => {
      if (err.code === 'no_engine') {
        // Prompt user to install a TTS engine if one isn't found
        Tts.requestInstallEngine();
      }
      console.error("TTS Initialization Failed:", err);
    });
  };

  return (
    <StyledView className="mt-6 p-5 bg-zinc-800/50 border border-zinc-700 rounded-2xl">
      <StyledView className="flex-row items-center mb-4">
        <Volume2 color="#22c55e" size={20} className="mr-2" />
        <StyledText className="text-xl text-gray-300 font-semibold">Voice Diagnostics</StyledText>
      </StyledView>

      <StyledText className="text-sm text-gray-500 mb-5 font-mono">
        {`Testing in: ${language}`}
      </StyledText>

      <StyledTouchable
        onPress={testSpeech}
        className="flex-row items-center justify-center py-4 rounded-xl bg-zinc-800 border-2 border-zinc-700 active:bg-green-500 active:border-green-400"
        accessibilityLabel="Test Text to Speech"
        accessibilityHint={`Speaks a test phrase in ${language}`}
      >
        <Play color="#FFF" size={20} className="mr-2" fill="#FFF" />
        <StyledText className="text-white font-bold">PLAY SAMPLE</StyledText>
      </StyledTouchable>
    </StyledView>
  );
};

export default TTSTester;