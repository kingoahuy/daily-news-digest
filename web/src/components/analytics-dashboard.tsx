"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, Database, LoaderCircle, Newspaper, TrendingUp } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from "recharts";

import { useLanguage } from "@/components/language-provider";
import {
  ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { categories } from "@/data/category-data";
import { getAnalytics } from "@/lib/api";
import type { AnalyticsData } from "@/types/api";

const palette = ["#d97706", "#0f766e", "#2563eb", "#7c3aed", "#be123c"];

const trendConfig = {
  important_count: { label: "高分新闻", color: "#2f6f5e" },
  average_score: { label: "平均分", color: "#d99a35" },
} satisfies ChartConfig;

export function AnalyticsDashboard() {
  const { language } = useLanguage();
  const zh = language === "zh";
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : "分析数据读取失败。",
        ),
      );
  }, []);

  const categoryData = useMemo(
    () =>
      categories.map((category, index) => ({
        category: category.label.zh,
        count: data?.category_counts[category.key] ?? 0,
        color: palette[index],
      })),
    [data],
  );
  const sourceData = useMemo(
    () =>
      Object.entries(data?.source_counts ?? {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6)
        .map(([name, value], index) => ({
          key: `source_${index}`,
          name,
          value,
          color: palette[index % palette.length],
        })),
    [data],
  );
  const sourceConfig = Object.fromEntries(
    sourceData.map((source) => [
      source.key,
      { label: source.name, color: source.color },
    ]),
  ) satisfies ChartConfig;
  const categoryConfig = Object.fromEntries(
    categoryData.map((category, index) => [
      `category_${index}`,
      { label: category.category, color: category.color },
    ]),
  ) satisfies ChartConfig;

  if (error) {
    return <AnalyticsMessage message={error} destructive />;
  }
  if (!data) {
    return <AnalyticsMessage message="正在读取真实分析数据..." loading />;
  }

  const latestAverage =
    data.trend[data.trend.length - 1]?.average_score ?? 0;

  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          Signal overview
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          {zh ? "数据分析" : "News analytics"}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          {zh
            ? "图表来自 SQLite 中的真实日报、新闻和互动记录。"
            : "Charts are generated from real reports, stories, and interactions in SQLite."}
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Newspaper} label="最新日报新闻" value={data.latest_news_count} />
        <Metric icon={Database} label="统计日报数" value={data.report_count} />
        <Metric
          icon={Activity}
          label="总互动"
          value={data.interaction_summary.total}
        />
        <Metric
          icon={TrendingUp}
          label="最新平均分"
          value={latestAverage.toFixed(1)}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="border-border/70 bg-card/88">
          <CardHeader>
            <CardTitle className="font-display text-2xl">各分类新闻数量</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={categoryConfig} className="h-[310px] w-full">
              <BarChart data={categoryData} margin={{ left: -18, right: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="category" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} allowDecimals={false} />
                <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                <Bar dataKey="count" radius={[8, 8, 2, 2]}>
                  {categoryData.map((entry) => (
                    <Cell key={entry.category} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/88">
          <CardHeader>
            <CardTitle className="font-display text-2xl">重要新闻趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={trendConfig} className="h-[310px] w-full">
              <LineChart data={data.trend} margin={{ left: -18, right: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Line
                  type="monotone"
                  dataKey="important_count"
                  stroke="var(--color-important_count)"
                  strokeWidth={3}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="average_score"
                  stroke="var(--color-average_score)"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 bg-card/88">
        <CardHeader>
          <CardTitle className="font-display text-2xl">来源占比</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:items-center">
          {sourceData.length ? (
            <>
              <ChartContainer
                config={sourceConfig}
                className="mx-auto h-[280px] w-full max-w-md"
              >
                <PieChart>
                  <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                  <Pie
                    data={sourceData}
                    dataKey="value"
                    nameKey="key"
                    innerRadius={62}
                    outerRadius={104}
                    paddingAngle={3}
                  >
                    {sourceData.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                  </Pie>
                  <ChartLegend
                    content={<ChartLegendContent nameKey="key" />}
                  />
                </PieChart>
              </ChartContainer>
              <div className="space-y-3">
                {sourceData.map((source) => (
                  <div
                    key={source.key}
                    className="flex items-center justify-between rounded-xl border bg-background/55 px-4 py-3"
                  >
                    <span className="flex items-center gap-3 text-sm font-medium">
                      <span
                        className="size-2.5 rounded-full"
                        style={{ backgroundColor: source.color }}
                      />
                      {source.name}
                    </span>
                    <span className="font-mono text-sm text-muted-foreground">
                      {source.value}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">暂无来源数据。</p>
          )}
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
  icon: typeof Newspaper;
  label: string;
  value: string | number;
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

function AnalyticsMessage({
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
