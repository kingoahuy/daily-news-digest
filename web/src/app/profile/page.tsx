"use client";

import { useEffect, useMemo, useState } from "react";
import { Bookmark, Heart, LoaderCircle, MessageCircle, Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { categories } from "@/data/category-data";
import { getProfile } from "@/lib/api";
import type { PreferenceProfile } from "@/types/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<PreferenceProfile | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : "偏好画像读取失败。",
        ),
      );
  }, []);

  const keywordRows = useMemo(
    () =>
      Object.entries(profile?.interaction_keyword_adjustments ?? {})
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        .slice(0, 8),
    [profile],
  );

  if (error) {
    return <ProfileMessage message={error} destructive />;
  }
  if (!profile) {
    return <ProfileMessage message="正在分析互动偏好..." loading />;
  }

  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          Preference signals
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          我的偏好画像
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          画像由真实点赞、收藏和评论按透明规则计算，并在下一次生成日报时影响排序。
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          icon={Heart}
          label="点赞"
          value={profile.interaction_summary.like}
        />
        <Metric
          icon={Bookmark}
          label="收藏"
          value={profile.interaction_summary.favorite}
        />
        <Metric
          icon={MessageCircle}
          label="评论"
          value={profile.interaction_summary.comment}
        />
        <Metric
          icon={Sparkles}
          label="有效互动"
          value={profile.interaction_count}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="border-border/70 bg-card/88">
          <CardHeader>
            <CardTitle className="font-display text-2xl">分类影响</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {categories.map((category) => {
              const adjustment =
                profile.interaction_category_adjustments[category.key] ?? 0;
              const base = profile.category_weights[category.key] ?? 1;
              const progress = Math.max(
                0,
                Math.min(100, 50 + adjustment * 35),
              );
              return (
                <div key={category.key}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 font-medium">
                      <span
                        className={`size-2 rounded-full ${category.accent}`}
                      />
                      {category.label.zh}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      基础 {base.toFixed(1)} · 互动 {formatSigned(adjustment)}
                    </span>
                  </div>
                  <Progress value={progress} />
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/88">
          <CardHeader>
            <CardTitle className="font-display text-2xl">关键词信号</CardTitle>
          </CardHeader>
          <CardContent>
            {keywordRows.length ? (
              <div className="space-y-3">
                {keywordRows.map(([keyword, weight]) => (
                  <div
                    key={keyword}
                    className="flex items-center justify-between rounded-xl border bg-background/55 px-4 py-3"
                  >
                    <span className="text-sm font-medium">{keyword}</span>
                    <span
                      className={
                        weight >= 0
                          ? "font-mono text-sm text-emerald-700"
                          : "font-mono text-sm text-destructive"
                      }
                    >
                      {formatSigned(weight)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">
                当前互动还不足以形成关键词偏好。继续点赞、收藏或评论后，这里会出现变化。
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 bg-[#f1e6d3]">
        <CardContent className="p-6 text-sm leading-7">
          正面评论 {profile.positive_comment_count} 条，负面评论{" "}
          {profile.negative_comment_count} 条。收藏对来源偏好的影响高于点赞，评论中的
          “继续关注”或“不感兴趣”等词会进一步调整推荐。
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Heart;
  label: string;
  value: number;
}) {
  return (
    <Card className="border-border/70 bg-card/88">
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-2 font-display text-3xl font-semibold">{value}</p>
        </div>
        <span className="grid size-10 place-items-center rounded-2xl bg-secondary">
          <Icon className="size-4.5" />
        </span>
      </CardContent>
    </Card>
  );
}

function ProfileMessage({
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
      <CardContent className="flex min-h-48 flex-col items-center justify-center p-8">
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

function formatSigned(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}
