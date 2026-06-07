"use client";

import { Activity, Database, Newspaper, TrendingUp } from "lucide-react";
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
import {
  categoryChartData,
  importanceTrendData,
  sourceShareData,
} from "@/data/mock-data";

const categoryConfig = {
  technology: { label: "科技", color: "#d97706" },
  finance: { label: "财经", color: "#0f766e" },
  sports: { label: "体育", color: "#2563eb" },
  politics: { label: "政治", color: "#7c3aed" },
  society: { label: "社会", color: "#be123c" },
} satisfies ChartConfig;

const trendConfig = {
  high: { label: "高分新闻", color: "#2f6f5e" },
  average: { label: "平均分", color: "#d99a35" },
} satisfies ChartConfig;

const sourceConfig = {
  techwire: { label: "TechWire", color: "#d97706" },
  market: { label: "Market Lens", color: "#0f766e" },
  world: { label: "World Affairs", color: "#7c3aed" },
  sportsdesk: { label: "Sports Desk", color: "#2563eb" },
  others: { label: "Others", color: "#b9aa94" },
} satisfies ChartConfig;

export function AnalyticsDashboard() {
  const { language } = useLanguage();
  const zh = language === "zh";

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
            ? "观察新闻结构、重要性变化和来源分布。当前图表使用 mock 数据。"
            : "Explore story mix, importance trends, and source distribution. Charts currently use mock data."}
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Newspaper} label={zh ? "今日抓取" : "Stories fetched"} value="286" />
        <Metric icon={Database} label={zh ? "去重后" : "After dedupe"} value="252" />
        <Metric icon={Activity} label={zh ? "高分新闻" : "High-score stories"} value="12" />
        <Metric icon={TrendingUp} label={zh ? "平均分" : "Average score"} value="7.7" />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="border-border/70 bg-card/88">
          <CardHeader>
            <CardTitle className="font-display text-2xl">
              {zh ? "各分类新闻数量" : "Stories by category"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={categoryConfig} className="h-[310px] w-full">
              <BarChart data={categoryChartData} margin={{ left: -18, right: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="category" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                <Bar dataKey="count" radius={[8, 8, 2, 2]}>
                  {categoryChartData.map((entry, index) => (
                    <Cell
                      key={entry.category}
                      fill={Object.values(categoryConfig)[index].color}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/88">
          <CardHeader>
            <CardTitle className="font-display text-2xl">
              {zh ? "重要新闻趋势" : "Important-story trend"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={trendConfig} className="h-[310px] w-full">
              <LineChart data={importanceTrendData} margin={{ left: -18, right: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Line
                  type="monotone"
                  dataKey="high"
                  stroke="var(--color-high)"
                  strokeWidth={3}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="average"
                  stroke="var(--color-average)"
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
          <CardTitle className="font-display text-2xl">
            {zh ? "来源占比" : "Source share"}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:items-center">
          <ChartContainer config={sourceConfig} className="mx-auto h-[280px] w-full max-w-md">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent hideLabel />} />
              <Pie
                data={sourceShareData}
                dataKey="value"
                nameKey="key"
                innerRadius={62}
                outerRadius={104}
                paddingAngle={3}
              >
                {sourceShareData.map((entry, index) => (
                  <Cell
                    key={entry.name}
                    fill={Object.values(sourceConfig)[index].color}
                  />
                ))}
              </Pie>
              <ChartLegend content={<ChartLegendContent nameKey="key" />} />
            </PieChart>
          </ChartContainer>
          <div className="space-y-3">
            {sourceShareData.map((source, index) => (
              <div
                key={source.name}
                className="flex items-center justify-between rounded-xl border bg-background/55 px-4 py-3"
              >
                <span className="flex items-center gap-3 text-sm font-medium">
                  <span
                    className="size-2.5 rounded-full"
                    style={{
                      backgroundColor: Object.values(sourceConfig)[index].color,
                    }}
                  />
                  {source.name}
                </span>
                <span className="font-mono text-sm text-muted-foreground">
                  {source.value}%
                </span>
              </div>
            ))}
          </div>
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
  value: string;
}) {
  return (
    <Card className="border-border/70 bg-card/88">
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-2 font-display text-3xl font-semibold">{value}</p>
        </div>
        <span className="grid size-10 place-items-center rounded-2xl bg-secondary text-secondary-foreground">
          <Icon className="size-4.5" />
        </span>
      </CardContent>
    </Card>
  );
}
