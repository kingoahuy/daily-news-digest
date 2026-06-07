"use client";

import { useState } from "react";
import { BellRing, Check, Clock3, Languages, ListFilter, Save } from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { categories } from "@/data/mock-data";
import { cn } from "@/lib/utils";

const languageOptions = [
  { value: "zh", zh: "中文", en: "Chinese" },
  { value: "en", zh: "英文", en: "English" },
  { value: "bilingual", zh: "中英双语", en: "Bilingual" },
];

const summaryOptions = [
  {
    value: "concise",
    zh: "简洁版",
    en: "Concise",
    zhDesc: "快速了解重点，适合晨间阅读",
    enDesc: "Fast scanning for a morning briefing",
  },
  {
    value: "detailed",
    zh: "详细版",
    en: "Detailed",
    zhDesc: "增加背景、影响与后续看点",
    enDesc: "More context, impact, and follow-up points",
  },
  {
    value: "podcast",
    zh: "播客叙事版",
    en: "Podcast narrative",
    zhDesc: "更自然的连贯叙述方式",
    enDesc: "A more conversational, flowing narrative",
  },
];

export function SettingsPanel() {
  const { language } = useLanguage();
  const zh = language === "zh";
  const [selectedCategories, setSelectedCategories] = useState(
    categories.map((category) => category.key),
  );
  const [deliveryEnabled, setDeliveryEnabled] = useState(true);
  const [deliveryTime, setDeliveryTime] = useState("08:13");
  const [preferredLanguage, setPreferredLanguage] = useState("bilingual");
  const [summaryStyle, setSummaryStyle] = useState("concise");
  const [saved, setSaved] = useState(false);

  const toggleCategory = (key: (typeof categories)[number]["key"]) => {
    setSaved(false);
    setSelectedCategories((current) =>
      current.includes(key)
        ? current.filter((item) => item !== key)
        : [...current, key],
    );
  };

  const save = () => {
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2200);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header>
        <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          Personalize
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          {zh ? "偏好设置" : "Preferences"}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          {zh
            ? "设置会保存在当前页面状态中。接入后端后可写入现有 SQLite 配置。"
            : "Settings currently live in page state. They can map to the existing SQLite configuration after backend integration."}
        </p>
      </header>

      <SettingsCard
        icon={ListFilter}
        title={zh ? "关注分类" : "Topics to follow"}
        description={
          zh ? "至少保留一个关注方向。" : "Keep at least one topic selected."
        }
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((category) => {
            const checked = selectedCategories.includes(category.key);
            return (
              <button
                key={category.key}
                type="button"
                onClick={() => toggleCategory(category.key)}
                className={cn(
                  "flex items-center gap-3 rounded-xl border p-4 text-left transition-colors",
                  checked
                    ? "border-primary/30 bg-secondary"
                    : "bg-background/55 text-muted-foreground",
                )}
              >
                <Checkbox checked={checked} aria-label={category.label.zh} />
                <span className={`size-2 rounded-full ${category.accent}`} />
                <span className="text-sm font-medium">
                  {zh ? category.label.zh : category.label.en}
                </span>
              </button>
            );
          })}
        </div>
      </SettingsCard>

      <SettingsCard
        icon={BellRing}
        title={zh ? "推送设置" : "Delivery"}
        description={
          zh
            ? "本页面暂不修改现有邮件调度器。"
            : "This preview does not modify the existing mail scheduler."
        }
      >
        <div className="flex items-center justify-between rounded-xl border bg-background/55 p-4">
          <div>
            <p className="text-sm font-medium">
              {zh ? "每日邮件推送" : "Daily email delivery"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {zh ? "在设定时间生成并发送日报" : "Generate and send the digest at the selected time"}
            </p>
          </div>
          <Switch
            checked={deliveryEnabled}
            onCheckedChange={(checked) => {
              setDeliveryEnabled(checked);
              setSaved(false);
            }}
          />
        </div>
        <label className="mt-4 block">
          <span className="mb-2 flex items-center gap-2 text-sm font-medium">
            <Clock3 className="size-4" />
            {zh ? "推送时间" : "Delivery time"}
          </span>
          <input
            type="time"
            value={deliveryTime}
            disabled={!deliveryEnabled}
            onChange={(event) => {
              setDeliveryTime(event.target.value);
              setSaved(false);
            }}
            className="h-11 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/20 disabled:opacity-45 sm:max-w-xs"
          />
        </label>
      </SettingsCard>

      <SettingsCard
        icon={Languages}
        title={zh ? "语言偏好" : "Language"}
        description={zh ? "控制日报默认输出语言。" : "Choose the default digest language."}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {languageOptions.map((option) => (
            <ChoiceButton
              key={option.value}
              active={preferredLanguage === option.value}
              title={zh ? option.zh : option.en}
              onClick={() => {
                setPreferredLanguage(option.value);
                setSaved(false);
              }}
            />
          ))}
        </div>
      </SettingsCard>

      <SettingsCard
        icon={ListFilter}
        title={zh ? "摘要风格" : "Summary style"}
        description={
          zh ? "决定日报的长度和叙事方式。" : "Controls digest length and narrative style."
        }
      >
        <div className="grid gap-3">
          {summaryOptions.map((option) => (
            <ChoiceButton
              key={option.value}
              active={summaryStyle === option.value}
              title={zh ? option.zh : option.en}
              description={zh ? option.zhDesc : option.enDesc}
              onClick={() => {
                setSummaryStyle(option.value);
                setSaved(false);
              }}
            />
          ))}
        </div>
      </SettingsCard>

      <div className="sticky bottom-24 flex justify-end lg:bottom-6">
        <Button
          size="lg"
          className="h-11 rounded-full px-5 shadow-lg"
          disabled={selectedCategories.length === 0}
          onClick={save}
        >
          {saved ? <Check className="size-4" /> : <Save className="size-4" />}
          {saved
            ? zh
              ? "已保存 Mock 设置"
              : "Mock settings saved"
            : zh
              ? "保存设置"
              : "Save preferences"}
        </Button>
      </div>
    </div>
  );
}

function SettingsCard({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof BellRing;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="border-border/70 bg-card/88">
      <CardHeader>
        <div className="flex gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-secondary text-secondary-foreground">
            <Icon className="size-4.5" />
          </span>
          <div>
            <CardTitle className="font-display text-2xl">{title}</CardTitle>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {description}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function ChoiceButton({
  active,
  title,
  description,
  onClick,
}: {
  active: boolean;
  title: string;
  description?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center justify-between gap-4 rounded-xl border p-4 text-left transition-colors",
        active ? "border-primary/35 bg-secondary" : "bg-background/55",
      )}
    >
      <span>
        <span className="block text-sm font-medium">{title}</span>
        {description ? (
          <span className="mt-1 block text-xs leading-5 text-muted-foreground">
            {description}
          </span>
        ) : null}
      </span>
      <span
        className={cn(
          "grid size-5 shrink-0 place-items-center rounded-full border",
          active && "border-primary bg-primary text-primary-foreground",
        )}
      >
        {active ? <Check className="size-3" /> : null}
      </span>
    </button>
  );
}
