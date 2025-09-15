import React from 'react';
import { Text, View, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styled } from 'nativewind';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../App';

// Styled components
const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

// Props type
type LandingScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Landing'>;
};

const LandingScreen: React.FC<LandingScreenProps> = ({ navigation }) => {
  const handleStart = () => {
    navigation.navigate('CameraCapture');
  };

  return (
    <SafeAreaView className="flex-1 bg-zinc-900 p-5 justify-between">
      <StyledView className="flex-1 justify-center items-center">
        <StyledText className="text-6xl font-bold text-white mb-2">Lumen</StyledText>
        <StyledText className="text-lg text-gray-400 text-center">
          Your visual companion for navigating the world.
        </StyledText>
      </StyledView>

      <StyledTouchable
        className="bg-green-500 w-full py-5 rounded-full items-center justify-center"
        onPress={handleStart}
      >
        <StyledText className="text-white text-lg font-bold">
          Start Camera Capture
        </StyledText>
      </StyledTouchable>
    </SafeAreaView>
  );
};

export default LandingScreen;
