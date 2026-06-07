"use client";

import { useEffect, useState } from "react";
import {
  BellRing,
  Check,
  Clock3,
  Gauge,
  Languages,
  LoaderCircle,
  Newspaper,
  Save,
  Sparkles,
} from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { getUserSettings, updateUserSettings } from "@/lib/api";
import type { UserSettings, UserSettingsUpdate } from "@/types/api";

export function SettingsPanel() {
  const { language } = useLanguage();
  const zh = language === "zh";
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getUserSettings()
      .then(setSettings)
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : "设置读取失败。",
        ),
      );
  }, []);

  const update = <Key extends keyof UserSettingsUpdate>(
    key: Key,
    value: UserSettingsUpdate[Key],
  ) => {
    setSettings((current) =>
      current ? { ...current, [key]: value } : current,
    );
    setDirty(true);
    setSaved(false);
    setError("");
  };

  const save = async () => {
    if (!settings) {
      return;
    }
    if (settings.max_items_per_category > settings.max_total_news) {
      setError(
        zh
          ? "每类新闻数量不能大于新闻总数。"
          : "Items per category cannot exceed the total news count.",
      );
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = await updateUserSettings(toUpdatePayload(settings));
      setSettings(result);
      setDirty(false);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2600);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "设置保存失败。",
      );
    } finally {
      setSaving(false);
    }
  };

  if (error && !settings) {
    return <StatusCard message={error} destructive />;
  }
  if (!settings) {
    return (
      <StatusCard
        message={zh ? "正在读取 SQLite 设置..." : "Loading SQLite settings..."}
        loading
      />
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header>
        <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          Runtime configuration
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          {zh ? "真实设置" : "Live settings"}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
          {zh
            ? "所有选项都会写入本机 SQLite，并在下一次运行 python -m src.main --dry-run 或 --send 时生效。"
            : "Every option is saved to local SQLite and takes effect on the next Python dry-run or send run."}
        </p>
        {settings.updated_at ? (
          <p className="mt-2 text-xs text-muted-foreground">
            {zh ? "数据库更新时间：" : "Database updated: "}
            {formatDateTime(settings.updated_at)}
          </p>
        ) : null}
      </header>

      <SettingsCard
        icon={BellRing}
        title={zh ? "邮件推送" : "Email delivery"}
        description={
          zh
            ? "关闭后，--send 仍会生成日报，但会跳过 SMTP 校验和邮件发送。"
            : "When disabled, --send still generates the digest but skips SMTP validation and delivery."
        }
      >
        <SettingRow
          title={zh ? "启用邮件推送" : "Enable email delivery"}
          description={
            zh
              ? "控制下一次 --send 是否实际发送邮件。"
              : "Controls whether the next --send run delivers email."
          }
        >
          <Switch
            aria-label={zh ? "启用邮件推送" : "Enable email delivery"}
            checked={settings.email_enabled}
            onCheckedChange={(checked) => update("email_enabled", checked)}
          />
        </SettingRow>

        <label className="mt-5 block rounded-xl border bg-background/55 p-4">
          <span className="flex items-center gap-2 text-sm font-medium">
            <Clock3 className="size-4" />
            {zh ? "每日推送时间" : "Daily delivery time"}
          </span>
          <span className="mt-1 block text-xs leading-5 text-muted-foreground">
            {zh
              ? "供本地邮件调度器读取；手动运行 --send 会立即执行。"
              : "Used by the local scheduler; manual --send runs immediately."}
          </span>
          <input
            type="time"
            aria-label={zh ? "每日推送时间" : "Daily delivery time"}
            value={settings.email_send_time}
            onChange={(event) =>
              update("email_send_time", event.target.value)
            }
            className="mt-3 h-11 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/20 sm:max-w-xs"
          />
        </label>
      </SettingsCard>

      <SettingsCard
        icon={Gauge}
        title={zh ? "API 使用模式" : "API usage"}
        description={
          zh
            ? "省 API 模式只让排名靠前的候选新闻进入 DeepSeek 精评。"
            : "Low API mode sends only top-ranked candidates to DeepSeek scoring."
        }
      >
        <SettingRow
          title={zh ? "启用省 API 模式" : "Enable low API mode"}
          description={
            zh
              ? "适合日常使用，可减少调用量；关闭后会尝试对全部候选新闻评分。"
              : "Reduces routine API calls; disabling it scores all candidates."
          }
        >
          <Switch
            aria-label={zh ? "启用省 API 模式" : "Enable low API mode"}
            checked={settings.low_api_mode}
            onCheckedChange={(checked) => update("low_api_mode", checked)}
          />
        </SettingRow>
      </SettingsCard>

      <SettingsCard
        icon={Newspaper}
        title={zh ? "新闻数量" : "News volume"}
        description={
          zh
            ? "控制最终进入日报的新闻上限。实际数量还会受到评分阈值和去重影响。"
            : "Sets digest limits. Scores, thresholds, and deduplication may reduce the final count."
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField
            label={zh ? "新闻总数" : "Total news"}
            description={zh ? "允许范围：1–100" : "Allowed: 1–100"}
            value={settings.max_total_news}
            min={1}
            max={100}
            onChange={(value) => update("max_total_news", value)}
          />
          <NumberField
            label={zh ? "每类新闻数量" : "Items per category"}
            description={zh ? "允许范围：1–30" : "Allowed: 1–30"}
            value={settings.max_items_per_category}
            min={1}
            max={30}
            onChange={(value) => update("max_items_per_category", value)}
          />
        </div>
      </SettingsCard>

      <SettingsCard
        icon={Languages}
        title={zh ? "日报输出" : "Digest output"}
        description={
          zh
            ? "语言和背景补充会影响下一次生成的 Markdown、邮件和 Pages 日报。"
            : "Language and enrichment affect the next Markdown, email, and Pages digest."
        }
      >
        <div className="space-y-3">
          <SettingRow
            title={zh ? "生成中英文双语日报" : "Generate bilingual digest"}
            description={
              zh
                ? "开启后，日报标题、重点和正文会使用中英文双语格式。"
                : "Uses bilingual titles, highlights, and story content."
            }
          >
            <Switch
              aria-label={
                zh ? "生成中英文双语日报" : "Generate bilingual digest"
              }
              checked={settings.enable_bilingual_report}
              onCheckedChange={(checked) =>
                update("enable_bilingual_report", checked)
              }
            />
          </SettingRow>
          <SettingRow
            title={zh ? "启用核心新闻背景补充" : "Enable story enrichment"}
            description={
              zh
                ? "对核心高分新闻生成背景、影响和后续关注点。"
                : "Adds context, impact, and follow-up points to core stories."
            }
          >
            <Switch
              aria-label={
                zh
                  ? "启用核心新闻背景补充"
                  : "Enable story enrichment"
              }
              checked={settings.enable_enrichment}
              onCheckedChange={(checked) =>
                update("enable_enrichment", checked)
              }
            />
          </SettingRow>
        </div>
      </SettingsCard>

      {error ? (
        <p
          role="alert"
          className="rounded-xl border border-destructive/25 bg-destructive/8 px-4 py-3 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}

      <div className="sticky bottom-24 flex justify-end lg:bottom-6">
        <Button
          size="lg"
          className="h-11 rounded-full px-5 shadow-lg"
          disabled={!dirty || saving}
          onClick={save}
        >
          {saving ? (
            <LoaderCircle className="size-4 animate-spin" />
          ) : saved ? (
            <Check className="size-4" />
          ) : (
            <Save className="size-4" />
          )}
          {saving
            ? zh
              ? "正在写入 SQLite..."
              : "Saving to SQLite..."
            : saved
              ? zh
                ? "已保存并将在下次运行生效"
                : "Saved for the next run"
              : zh
                ? "保存真实设置"
                : "Save live settings"}
        </Button>
      </div>
    </div>
  );
}

function toUpdatePayload(settings: UserSettings): UserSettingsUpdate {
  return {
    email_enabled: settings.email_enabled,
    email_send_time: settings.email_send_time,
    low_api_mode: settings.low_api_mode,
    max_total_news: settings.max_total_news,
    max_items_per_category: settings.max_items_per_category,
    enable_bilingual_report: settings.enable_bilingual_report,
    enable_enrichment: settings.enable_enrichment,
  };
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

function SettingRow({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-5 rounded-xl border bg-background/55 p-4">
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {description}
        </p>
      </div>
      {children}
    </div>
  );
}

function NumberField({
  label,
  description,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="rounded-xl border bg-background/55 p-4">
      <span className="flex items-center gap-2 text-sm font-medium">
        <Sparkles className="size-4" />
        {label}
      </span>
      <span className="mt-1 block text-xs text-muted-foreground">
        {description}
      </span>
      <input
        type="number"
        aria-label={label}
        value={value}
        min={min}
        max={max}
        step={1}
        onChange={(event) => {
          const next = Number(event.target.value);
          if (Number.isFinite(next)) {
            onChange(next);
          }
        }}
        className="mt-3 h-11 w-full rounded-xl border bg-background px-3 font-mono text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/20"
      />
    </label>
  );
}

function StatusCard({
  message,
  loading = false,
  destructive = false,
}: {
  message: string;
  loading?: boolean;
  destructive?: boolean;
}) {
  return (
    <Card className="mx-auto mt-16 max-w-xl border-dashed">
      <CardContent className="flex min-h-48 flex-col items-center justify-center p-8 text-center">
        {loading ? (
          <LoaderCircle className="mb-4 size-6 animate-spin" />
        ) : null}
        <p className={destructive ? "text-destructive" : "text-muted-foreground"}>
          {message}
        </p>
      </CardContent>
    </Card>
  );
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("zh-CN", { hour12: false });
}
