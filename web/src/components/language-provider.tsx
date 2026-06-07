"use client";

import { createContext, useContext, useMemo, useState } from "react";

import type { LanguageMode, LocalizedText } from "@/types/news";

type LanguageContextValue = {
  language: LanguageMode;
  setLanguage: (language: LanguageMode) => void;
  text: (value: LocalizedText) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [language, setLanguage] = useState<LanguageMode>("zh");
  const value = useMemo(
    () => ({
      language,
      setLanguage,
      text: (localized: LocalizedText) => localized[language],
    }),
    [language],
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return context;
}
