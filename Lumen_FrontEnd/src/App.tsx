import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator, NativeStackNavigationProp } from '@react-navigation/native-stack';

// Screens
import LandingScreen from './screens/LandingPage';
import CameraCaptureScreen from './screens/CameraCaptureScreen';

// Stack param list
export type RootStackParamList = {
  Landing: undefined;
  CameraCapture: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const App: React.FC = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Landing" screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Landing" component={LandingScreen} />
        <Stack.Screen name="CameraCapture" component={CameraCaptureScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default App;
