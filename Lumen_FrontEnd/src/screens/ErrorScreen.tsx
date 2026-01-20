// components/GlobalErrorFallback.tsx
import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styled } from 'nativewind';
import { Terminal, AlertCircle, RotateCcw } from 'lucide-react-native';

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

export const GlobalErrorFallback = ({ error, resetErrorBoundary }: any) => {
  return (
    <SafeAreaView className="flex-1 bg-zinc-950 p-6 justify-between">
      <StyledView className="mt-10">
        <StyledView className="flex-row items-center space-x-2 mb-6">
          <Terminal color="#ef4444" size={24} />
          <StyledText className="text-red-500 font-mono text-xs tracking-tighter">
            LUMEN_CORE_V1.0 // ERROR_REPORT
          </StyledText>
        </StyledView>

        <StyledView className="bg-red-500/10 border border-red-500/30 p-6 rounded-2xl mb-6">
          <AlertCircle color="#ef4444" size={48} strokeWidth={1.5} />
          <StyledText className="text-white text-2xl font-bold mt-4">
            Context Failure
          </StyledText>
          <StyledText className="text-gray-400 font-mono text-sm mt-2 leading-5">
            {error.message || "An unexpected hook execution error occurred outside the Provider scope."}
          </StyledText>
        </StyledView>

        <StyledView className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800">
          <StyledText className="text-zinc-500 font-mono text-[10px]">
            {`> STACK_TRACE: ${new Date().toISOString()}\n> MODULE: SettingsContext\n> STATUS: DETACHED`}
          </StyledText>
        </StyledView>
      </StyledView>

      <StyledTouchable
        onPress={resetErrorBoundary}
        className="bg-red-600 py-5 rounded-full items-center justify-center shadow-lg shadow-red-900/40"
      >
        <StyledView className="flex-row items-center space-x-2">
          <RotateCcw color="white" size={20} />
          <StyledText className="text-white font-bold text-lg">REBOOT SYSTEM</StyledText>
        </StyledView>
      </StyledTouchable>
    </SafeAreaView>
  );
};