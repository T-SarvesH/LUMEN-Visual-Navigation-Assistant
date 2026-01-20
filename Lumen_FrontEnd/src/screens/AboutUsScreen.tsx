import React from 'react';
import { ScrollView, View, Text, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styled } from 'nativewind';
import { ArrowLeft } from 'lucide-react-native'; // Standard back icon
import AboutProfile from '../components/AboutProfile';

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

const AboutScreen = ({ navigation }: any) => {
  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Top Header Section with Back Button */}
      <StyledView className="flex-row items-center px-6 pt-4">
        <StyledTouchable 
          onPress={() => navigation.goBack()}
          className="p-2 bg-zinc-800 rounded-full mr-4"
        >
          <ArrowLeft color="#22c55e" size={28} strokeWidth={2.5} />
        </StyledTouchable>
      </StyledView>

      <ScrollView contentContainerStyle={{ padding: 24 }}>
        <StyledView className="mb-10 mt-2">
          <StyledText className="text-white text-3xl font-bold">About LUMEN</StyledText>
          <StyledText className="text-zinc-500 font-mono mt-2">v1.0.4 // Project_Intelligence</StyledText>
        </StyledView>

        <AboutProfile 
          name="Sarvesh Tikekar"
          role="Lead Developer / AI Architect"
          description="Building neural prosthetics for visual navigation. Passionate about real-time CV and accessibility technology."
          imageUri="https://github.com/Sarvesh-Tikekar.png"
          githubUrl="https://github.com/Sarvesh-Tikekar"
          linkedinUrl="https://linkedin.com/in/sarveshtikekar"
          instaUrl="https://instagram.com/sarveshtikekar"
        />

        <AboutProfile 
          name="Shaun Menezes"
          role="Frontend Engineer / UI/UX"
          description="Crafting seamless mobile experiences for assistive technology. Focused on high-performance React Native apps."
          imageUri="https://github.com/shaun-menezes.png" 
          githubUrl="https://github.com/shaun-menezes"
          linkedinUrl="https://linkedin.com/in/shaunmenezes"
          instaUrl="https://instagram.com/shaunmenezes"
        />

        <AboutProfile 
          name="Dwayne George Nixon"
          role="Backend Engineer / API Design"
          description="Designing robust architectures for real-time video processing. Specialized in FastAPI and WebRTC scaling."
          imageUri="https://github.com/dwayne-george.png"
          githubUrl="https://github.com/dwayne-george"
          linkedinUrl="https://linkedin.com/in/dwaynegeorge"
          instaUrl="https://instagram.com/dwaynegeorge"
        />

        <AboutProfile 
          name="Ramya Kulkarni"
          role="Data Scientist / ML Engineer"
          description="Optimizing YOLO models for edge devices. Dedicated to enhancing object detection accuracy in dynamic environments."
          imageUri="https://github.com/ramya-kulkarni.png"
          githubUrl="https://github.com/ramya-kulkarni"
          linkedinUrl="https://linkedin.com/in/ramyakulkarni"
          instaUrl="https://instagram.com/ramyakulkarni"
        />

        <StyledView className="mt-4 opacity-50 border-t border-zinc-800 pt-6">
          <StyledText className="text-zinc-500 text-xs text-center font-mono">
            Developed with React Native, FastAPI, and YOLOv8.
          </StyledText>
        </StyledView>
      </ScrollView>
    </SafeAreaView>
  );
};

export default AboutScreen;