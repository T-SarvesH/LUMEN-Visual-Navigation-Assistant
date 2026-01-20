import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator, NativeStackNavigationProp } from '@react-navigation/native-stack';
import { SettingsProvider } from './context/SettingsContext';
import ErrorBoundary from 'react-native-error-boundary';

// Screens
import LandingScreen from './screens/LandingPage';
import CameraCaptureScreen from './screens/CameraCaptureScreen';
import SettingsScreen from './screens/Settings';
import { GlobalErrorFallback } from './screens/ErrorScreen';
import AboutScreen from './screens/AboutUsScreen';
// Stack param list
export type RootStackParamList = {
  Landing: undefined;
  CameraCapture: undefined;
  Settings: undefined;
  AboutUs: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const App: React.FC = () => {
  return (
    <ErrorBoundary FallbackComponent={GlobalErrorFallback}>
    <SettingsProvider>
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Landing" screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Landing" component={LandingScreen} />
        <Stack.Screen name="CameraCapture" component={CameraCaptureScreen} />
        <Stack.Screen name="Settings" component={SettingsScreen} />
        <Stack.Screen name="AboutUs" component={AboutScreen}></Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  </SettingsProvider>
  </ErrorBoundary>
  );
};

export default App;
