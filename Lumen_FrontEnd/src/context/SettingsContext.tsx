import React, { createContext, useState, useContext, ReactNode } from 'react';

type Language = 'English' | 'Hindi';
type Duration = 15 | 20 | 30;

interface SettingsContextType {
  duration: Duration;
  setDuration: (d: Duration) => void;
  language: Language;
  setLanguage: (l: Language) => void;
  isDevMode: boolean;
  setIsDevMode: (v: boolean) => void;
  isRecordingEnabled: boolean;
  setIsRecordingEnabled: (v: boolean) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

// Module-level variable to persist state across Activity restarts (Orientation Changes)
let globalIsDevMode = false;

export const SettingsProvider = ({ children }: { children: ReactNode }) => {
  const [duration, setDuration] = useState<Duration>(15);
  const [language, setLanguage] = useState<Language>('English');
  // Initialize from global variable
  const [isDevMode, _setIsDevMode] = useState<boolean>(globalIsDevMode);
  const [isRecordingEnabled, setIsRecordingEnabled] = useState<boolean>(false);

  // Wrapper to update both state and global variable
  const setIsDevMode = (val: boolean) => {
    globalIsDevMode = val;
    _setIsDevMode(val);
  };

  return (
    <SettingsContext.Provider value={{
      duration, setDuration,
      language, setLanguage,
      isDevMode, setIsDevMode,
      isRecordingEnabled, setIsRecordingEnabled
    }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) throw new Error("useSettings must be used within a SettingsProvider");
  return context;
};