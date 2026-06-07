"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  BrainCircuit,
  CircleHelp,
  Clock3,
  Lightbulb,
  LoaderCircle,
} from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { NewsInteractions } from "@/components/news-interactions";
import { ScoreBadge } from "@/components/score-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { categoryMap } from "@/data/category-data";
import { getNews } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ApiNews } from "@/types/api";

export function ArticleDetail({ newsId }: { newsId: number }) {
  const { language, text } = useLanguage();
  const [article, setArticle] = useState<ApiNews | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getNews(newsId)
      .then((data) => {
        if (active) {
          setArticle(data);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "新闻读取失败。",
          );
        }
      });
    return () => {
      active = false;
    };
  }, [newsId]);

  if (error) {
    return <MessageCard message={error} destructive />;
  }
  if (!article) {
    return <MessageCard message="正在读取新闻详情..." loading />;
  }

  const category = categoryMap[article.category] ?? categoryMap.society;
  const enrichment = article.enrichment || {};
  const beginnerExplanation =
    enrichment.background ||
    article.ai_summary ||
    "当前信息来自 RSS 标题与摘要，暂没有更多可核验的通俗解释。";

  return (
    <article className="mx-auto max-w-5xl">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        {language === "zh" ? "返回今日简报" : "Back to today’s digest"}
      </Link>

      <header className="mt-8">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="rounded-full bg-card">
            <span className={`mr-1.5 size-1.5 rounded-full ${category.accent}`} />
            {text(category.label)}
          </Badge>
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock3 className="size-3.5" />
            {formatDateTime(article.published_at)}
          </span>
          <span className="text-xs text-muted-foreground">{article.source}</span>
        </div>
        <div className="mt-5 flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <h1 className="max-w-4xl font-display text-4xl leading-[1.08] font-semibold tracking-[-0.035em] sm:text-5xl lg:text-6xl">
            {article.title}
          </h1>
          <ScoreBadge score={article.ai_score || article.score} large />
        </div>
        <p className="mt-6 max-w-3xl text-lg leading-8 text-muted-foreground">
          {article.summary || article.ai_summary || "暂无摘要。"}
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {article.ai_tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="rounded-full">
              {tag}
            </Badge>
          ))}
        </div>
        <div className="mt-7 max-w-3xl">
          <NewsInteractions
            newsId={article.id}
            url={article.url}
            initialState={article.interactions}
          />
        </div>
      </header>

      <Separator className="my-10" />

      <div className="grid gap-5 lg:grid-cols-2">
        <ExplanationCard
          icon={Lightbulb}
          eyebrow={language === "zh" ? "AI 判断" : "AI assessment"}
          title={language === "zh" ? "为什么重要" : "Why it matters"}
          content={
            article.ai_reason ||
            enrichment.why_it_matters ||
            "当前没有 AI 推荐理由。"
          }
          className="bg-[#f1e6d3]"
        />
        <ExplanationCard
          icon={BookOpen}
          eyebrow={language === "zh" ? "上下文" : "Context"}
          title={language === "zh" ? "背景解释" : "Background"}
          content={
            enrichment.background ||
            "根据当前摘要信息，暂不能判断更多背景细节。"
          }
          className="bg-[#e2ece8]"
        />
      </div>

      <Card className="mt-5 overflow-hidden border-primary/15 bg-primary text-primary-foreground">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2 text-xs tracking-[0.18em] text-white/55 uppercase">
            <BrainCircuit className="size-4" />
            AI summary
          </div>
          <CardTitle className="mt-2 font-display text-2xl sm:text-3xl">
            {language === "zh" ? "AI 摘要" : "AI summary"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="max-w-4xl text-base leading-8 text-white/78">
            {article.ai_summary || article.summary || "暂无 AI 摘要。"}
          </p>
        </CardContent>
      </Card>

      <Card className="mt-5 border-border/70 bg-card/88">
        <CardHeader>
          <div className="flex items-center gap-2 text-xs tracking-[0.18em] text-muted-foreground uppercase">
            <CircleHelp className="size-4" />
            Plain-language explanation
          </div>
          <CardTitle className="font-display text-2xl">
            {language === "zh" ? "新手也能看懂" : "Explain it simply"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-7 text-muted-foreground">
            {beginnerExplanation}
          </p>
          {enrichment.possible_impact ? (
            <p className="mt-4 text-sm leading-7">
              <span className="font-medium">可能影响：</span>
              {enrichment.possible_impact}
            </p>
          ) : null}
          {enrichment.follow_up_points?.length ? (
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              {enrichment.follow_up_points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>
    </article>
  );
}

function ExplanationCard({
  icon: Icon,
  eyebrow,
  title,
  content,
  className,
}: {
  icon: typeof Lightbulb;
  eyebrow: string;
  title: string;
  content: string;
  className: string;
}) {
  return (
    <Card className={cn("border-transparent", className)}>
      <CardHeader>
        <div className="flex items-center gap-2 text-xs tracking-[0.18em] text-foreground/50 uppercase">
          <Icon className="size-4" />
          {eyebrow}
        </div>
        <CardTitle className="font-display text-2xl">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-7 text-foreground/72">{content}</p>
      </CardContent>
    </Card>
  );
}

function MessageCard({
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

function formatDateTime(value: string) {
  if (!value) {
    return "时间未知";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("zh-CN", { hour12: false });
}
