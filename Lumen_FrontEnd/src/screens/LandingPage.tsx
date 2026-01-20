import React from 'react';
import { Text, View, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styled } from 'nativewind';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../App';
import { Settings, Info } from 'lucide-react-native'; // Added Info import

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

type LandingScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Landing'>;
};

const LandingScreen: React.FC<LandingScreenProps> = ({ navigation }) => {
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
        <StyledView className="mb-4 p-4 rounded-2xl bg-zinc-800 border border-green-500/30">
          <StyledText className="text-6xl font-bold text-white">Lumen</StyledText>
        </StyledView>
        <StyledText className="text-lg text-gray-400 text-center px-4">
          Your visual companion for navigating the world.
        </StyledText>
      </StyledView>

      {/* Action Button */}
      <StyledTouchable
        className="bg-green-500 w-full py-5 rounded-full items-center justify-center shadow-lg shadow-green-500/50"
        onPress={() => navigation.navigate('CameraCapture')}
      >
        <StyledText className="text-white text-lg font-bold">
          Start Capture
        </StyledText>
      </StyledTouchable>
    </SafeAreaView>
  );
};

export default LandingScreen;