"use client";

import { Languages } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/components/language-provider";

export function LanguageToggle() {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="flex items-center rounded-xl border bg-card p-1 shadow-sm">
      <span className="px-2 text-muted-foreground">
        <Languages className="size-4" />
      </span>
      <Button
        variant={language === "zh" ? "default" : "ghost"}
        size="sm"
        className="h-7 rounded-lg px-2.5 text-xs"
        onClick={() => setLanguage("zh")}
      >
        中文
      </Button>
      <Button
        variant={language === "en" ? "default" : "ghost"}
        size="sm"
        className="h-7 rounded-lg px-2.5 text-xs"
        onClick={() => setLanguage("en")}
      >
        EN
      </Button>
    </div>
  );
}
