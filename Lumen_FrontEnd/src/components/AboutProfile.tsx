import React from 'react';
import { View, Text, Image, TouchableOpacity, Linking } from 'react-native';
import { styled } from 'nativewind';
// We switch to FontAwesome for brand icons
import Icon from 'react-native-vector-icons/FontAwesome'; 

const StyledView = styled(View);
const StyledText = styled(Text);
const StyledTouchable = styled(TouchableOpacity);

interface ProfileProps {
  name: string;
  role: string;
  description: string;
  imageUri: string;
  githubUrl: string;
  linkedinUrl: string;
  instaUrl: string;
}

const AboutProfile: React.FC<ProfileProps> = ({ 
  name, role, description, imageUri, githubUrl, linkedinUrl, instaUrl 
}) => {
  return (
    <StyledView className="bg-zinc-900 border border-zinc-800 p-6 rounded-3xl items-center mb-6">
      <View className="p-1 rounded-full border-2 border-green-500 mb-4">
        <Image 
          source={{ uri: imageUri }} 
          className="w-24 h-24 rounded-full"
          resizeMode="cover"
        />
      </View>

      <StyledText className="text-white text-xl font-bold">{name}</StyledText>
      <StyledText className="text-green-500 font-mono text-[10px] mb-3 uppercase tracking-[2px]">
        {role}
      </StyledText>
      
      <StyledText className="text-gray-400 text-center text-sm leading-5 mb-6 px-2">
        {description}
      </StyledText>

      {/* Replaced Lucide icons with FontAwesome icons */}
      <StyledView className="flex-row space-x-8">
        <StyledTouchable onPress={() => Linking.openURL(githubUrl)}>
          <Icon name="github" color="#94a3b8" size={24} />
        </StyledTouchable>
        <StyledTouchable onPress={() => Linking.openURL(linkedinUrl)}>
          <Icon name="linkedin" color="#94a3b8" size={24} />
        </StyledTouchable>
        <StyledTouchable onPress={() => Linking.openURL(instaUrl)}>
          <Icon name="instagram" color="#94a3b8" size={24} />
        </StyledTouchable>
      </StyledView>
    </StyledView>
  );
};

export default AboutProfile;