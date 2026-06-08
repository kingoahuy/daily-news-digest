"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  LoaderCircle,
  RefreshCw,
  Sparkles,
} from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { NewsCard } from "@/components/news-card";
import { ScoreBadge } from "@/components/score-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { categories } from "@/data/category-data";
import {
  ApiRequestError,
  generateTodayReport,
  getLatestReport,
  getReportNews,
  getTodayReportStatus,
} from "@/lib/api";
import type { ApiNews, ApiReport, TodayReportStatus } from "@/types/api";

export default function DashboardPage() {
  const { language, text } = useLanguage();
  const [report, setReport] = useState<ApiReport | null>(null);
  const [news, setNews] = useState<ApiNews[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [noReport, setNoReport] = useState(false);
  const [todayStatus, setTodayStatus] = useState<TodayReportStatus | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateMessage, setGenerateMessage] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [status, latest] = await Promise.all([
          getTodayReportStatus(),
          getLatestReport(),
        ]);
        const items = await getReportNews(latest.report_id);
        if (active) {
          setTodayStatus(status);
          setReport(latest);
          setNews(items);
        }
      } catch (requestError) {
        if (!active) {
          return;
        }
        if (
          requestError instanceof ApiRequestError &&
          requestError.status === 404
        ) {
          setNoReport(true);
        } else {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "日报读取失败。",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const reloadLatest = async () => {
    const [status, latest] = await Promise.all([
      getTodayReportStatus(),
      getLatestReport(),
    ]);
    const items = await getReportNews(latest.report_id);
    setTodayStatus(status);
    setReport(latest);
    setNews(items);
    setNoReport(false);
  };

  const generateToday = async () => {
    setGenerating(true);
    setError("");
    setGenerateMessage("");
    try {
      const result = await generateTodayReport();
      setGenerateMessage(result.message);
      const items = await getReportNews(result.report.report_id);
      setReport(result.report);
      setTodayStatus(result.today_status);
      setNews(items);
      setNoReport(false);
      await reloadLatest();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "今日日报生成失败。",
      );
    } finally {
      setGenerating(false);
    }
  };

  const coreArticle = useMemo(
    () =>
      news.find((item) => item.title === report?.core_topic) ??
      [...news].sort(
        (a, b) => (b.ai_score || b.score) - (a.ai_score || a.score),
      )[0],
    [news, report],
  );
  const averageScore = news.length
    ? news.reduce((sum, item) => sum + (item.ai_score || item.score), 0) /
      news.length
    : 0;
  const sourceCount = new Set(news.map((item) => item.source)).size;

  if (loading) {
    return <StatusCard icon={LoaderCircle} message="正在读取本地日报..." spin />;
  }
  if (error) {
    return <StatusCard message={error} destructive />;
  }
  if (noReport || !report) {
    return (
      <StatusCard
        message="还没有生成日报。可以点击按钮运行一次 python -m src.main --dry-run。"
        action={
          <Button
            className="mt-5 rounded-full"
            disabled={generating}
            onClick={generateToday}
          >
            {generating ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            立即生成今日日报
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-10">
      {todayStatus && !todayStatus.has_today_report ? (
        <Card className="border-amber-300/70 bg-amber-50 text-amber-950">
          <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 size-5 shrink-0" />
              <div>
                <p className="font-medium">
                  今天还没有生成日报。当前显示的是{" "}
                  {todayStatus.latest_report_date || report.report_date} 的历史日报。
                </p>
                <p className="mt-1 text-xs leading-5 text-amber-900/75">
                  为避免浪费 API，网页刷新只检查状态，不会自动调用 DeepSeek。
                </p>
              </div>
            </div>
            <Button
              className="rounded-full bg-amber-900 text-white hover:bg-amber-800"
              disabled={generating}
              onClick={generateToday}
            >
              {generating ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              立即生成今日日报
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {generateMessage ? (
        <p className="rounded-xl border border-emerald-600/20 bg-emerald-600/8 px-4 py-3 text-sm text-emerald-700">
          {generateMessage}
        </p>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="rounded-full bg-[#2f6f5e] text-white">
              <Sparkles className="size-3.5" />
              SQLite live
            </Badge>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CalendarDays className="size-3.5" />
              {report.report_date}
            </span>
            {report.email_sent ? (
              <span className="flex items-center gap-1 text-xs text-emerald-700">
                <CheckCircle2 className="size-3.5" />
                邮件已发送
              </span>
            ) : null}
          </div>
          <h1 className="mt-5 max-w-4xl font-display text-4xl leading-[1.08] font-semibold tracking-[-0.035em] sm:text-5xl lg:text-6xl">
            {language === "zh" ? "今日新闻日报" : "Today’s News Digest"}
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
            {report.title}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            生成时间：{formatDateTime(report.generated_at)}
          </p>
        </div>

        <Card className="border-border/70 bg-primary text-primary-foreground shadow-[0_30px_70px_-42px_rgba(45,31,17,0.9)]">
          <CardContent className="flex h-full flex-col justify-between p-6">
            <div>
              <p className="text-xs tracking-[0.18em] text-primary-foreground/55 uppercase">
                Live local report
              </p>
              <p className="mt-4 font-display text-2xl leading-tight">
                {news.length} 条真实精选新闻
              </p>
            </div>
            <div className="mt-8 grid grid-cols-3 gap-3 text-center">
              {[
                [String(categories.length), "分类"],
                [averageScore.toFixed(1), "均分"],
                [String(sourceCount), "来源"],
              ].map(([value, label]) => (
                <div key={label} className="rounded-xl bg-white/8 px-2 py-3">
                  <div className="text-xl font-semibold">{value}</div>
                  <div className="mt-1 text-[10px] text-white/55">{label}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      {coreArticle ? (
        <section className="relative overflow-hidden rounded-[2rem] border bg-[#f2e7d5] p-6 shadow-[0_26px_80px_-55px_rgba(90,56,17,0.8)] sm:p-8 lg:p-10">
          <div className="paper-grid absolute inset-0 opacity-35" />
          <div className="relative grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
            <div>
              <p className="text-xs font-semibold tracking-[0.2em] text-[#8a5a18] uppercase">
                {language === "zh" ? "今日核心议题" : "Today’s core topic"}
              </p>
              <h2 className="mt-4 max-w-4xl font-display text-3xl leading-tight font-semibold tracking-[-0.025em] sm:text-4xl">
                {report.core_topic || coreArticle.title}
              </h2>
              <p className="mt-5 max-w-3xl text-sm leading-7 text-foreground/70 sm:text-base">
                {coreArticle.ai_summary ||
                  coreArticle.summary ||
                  "当前新闻暂无摘要。"}
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {coreArticle.ai_tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="outline"
                    className="rounded-full bg-white/45"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
            <ScoreBadge
              score={coreArticle.ai_score || coreArticle.score}
              large
            />
          </div>
        </section>
      ) : null}

      <section className="space-y-6">
        <div>
          <p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            Real news feed
          </p>
          <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight">
            {language === "zh" ? "分类新闻" : "Stories by category"}
          </h2>
        </div>

        <div className="space-y-10">
          {categories.map((category) => {
            const categoryNews = news.filter(
              (article) => article.category === category.key,
            );
            if (!categoryNews.length) {
              return null;
            }
            return (
              <div key={category.key}>
                <div className="mb-4 flex items-center gap-3">
                  <span className={`size-2.5 rounded-full ${category.accent}`} />
                  <h3 className="font-display text-xl font-semibold">
                    {text(category.label)}
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {categoryNews.length.toString().padStart(2, "0")}
                  </span>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  {categoryNews.map((article) => (
                    <NewsCard key={article.id} article={article} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <details className="rounded-2xl border bg-card/70 p-5">
        <summary className="cursor-pointer font-display text-xl font-semibold">
          查看完整 Markdown 日报
        </summary>
        <pre className="mt-5 overflow-x-auto whitespace-pre-wrap font-sans text-sm leading-7 text-muted-foreground">
          {report.markdown_content}
        </pre>
      </details>
    </div>
  );
}

function StatusCard({
  icon: Icon,
  message,
  action,
  spin = false,
  destructive = false,
}: {
  icon?: typeof LoaderCircle;
  message: string;
  action?: React.ReactNode;
  spin?: boolean;
  destructive?: boolean;
}) {
  return (
    <Card className="mx-auto mt-16 max-w-2xl border-dashed bg-card/70">
      <CardContent className="flex min-h-52 flex-col items-center justify-center p-8 text-center">
        {Icon ? (
          <Icon
            className={`mb-4 size-7 ${spin ? "animate-spin" : ""}`}
          />
        ) : null}
        <p
          className={
            destructive ? "text-destructive" : "text-muted-foreground"
          }
        >
          {message}
        </p>
        {action}
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
