import React, { createContext, useState, useContext, ReactNode } from 'react';

type Language = 'English' | 'Hindi';
type Duration = 15 | 20 | 30;

interface SettingsContextType {
  duration: Duration;
  setDuration: (d: Duration) => void;
  language: Language;
  setLanguage: (l: Language) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider = ({ children }: { children: ReactNode }) => {
  const [duration, setDuration] = useState<Duration>(15);
  const [language, setLanguage] = useState<Language>('English');

  return (
    <SettingsContext.Provider value={{ duration, setDuration, language, setLanguage }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) throw new Error("useSettings must be used within a SettingsProvider");
  return context;
};