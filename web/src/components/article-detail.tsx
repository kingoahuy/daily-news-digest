"use client";

import Link from "next/link";
import {
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  CircleHelp,
  Clock3,
  Lightbulb,
} from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { ScoreBadge } from "@/components/score-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { categories } from "@/data/mock-data";
import { cn } from "@/lib/utils";
import type { NewsArticle } from "@/types/news";

const sectionIcons = {
  why: Lightbulb,
  background: BookOpen,
  beginner: CircleHelp,
};

export function ArticleDetail({ article }: { article: NewsArticle }) {
  const { language, text } = useLanguage();
  const category = categories.find((item) => item.key === article.category)!;

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
            {article.publishedAt}
          </span>
          <span className="text-xs text-muted-foreground">{article.source}</span>
        </div>
        <div className="mt-5 flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <h1 className="max-w-4xl font-display text-4xl leading-[1.08] font-semibold tracking-[-0.035em] sm:text-5xl lg:text-6xl">
            {text(article.title)}
          </h1>
          <ScoreBadge score={article.score} large />
        </div>
        <p className="mt-6 max-w-3xl text-lg leading-8 text-muted-foreground">
          {text(article.fullSummary)}
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {article.tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="rounded-full">
              {tag}
            </Badge>
          ))}
        </div>
      </header>

      <Separator className="my-10" />

      <div className="grid gap-5 lg:grid-cols-2">
        <ExplanationCard
          icon={sectionIcons.why}
          eyebrow={language === "zh" ? "影响判断" : "Impact"}
          title={language === "zh" ? "为什么重要" : "Why it matters"}
          content={text(article.whyItMatters)}
          className="bg-[#f1e6d3]"
        />
        <ExplanationCard
          icon={sectionIcons.background}
          eyebrow={language === "zh" ? "上下文" : "Context"}
          title={language === "zh" ? "背景解释" : "Background"}
          content={text(article.background)}
          className="bg-[#e2ece8]"
        />
      </div>

      <Card className="mt-5 overflow-hidden border-primary/15 bg-primary text-primary-foreground">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2 text-xs tracking-[0.18em] text-white/55 uppercase">
            <BrainCircuit className="size-4" />
            AI plain-language mode
          </div>
          <CardTitle className="mt-2 font-display text-2xl sm:text-3xl">
            {language === "zh" ? "新手也能看懂" : "Explain it like I’m new"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="max-w-4xl text-base leading-8 text-white/78">
            {text(article.beginnerExplanation)}
          </p>
        </CardContent>
      </Card>

      <section className="mt-10">
        <h2 className="font-display text-2xl font-semibold">
          {language === "zh" ? "相关链接" : "Related links"}
        </h2>
        {article.relatedLinks.length ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {article.relatedLinks.map((link) => (
              <a
                key={link.url}
                href={link.url}
                target="_blank"
                rel="noreferrer"
                className={cn(
                  buttonVariants({ variant: "outline" }),
                  "h-auto justify-between rounded-xl px-4 py-3",
                )}
              >
                {text(link.label)}
                <ArrowUpRight className="size-4" />
              </a>
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-dashed bg-card/50 p-6 text-sm text-muted-foreground">
            {language === "zh"
              ? "Mock 数据暂未配置外部链接。接入真实后端后，这里将显示原始新闻与相关来源。"
              : "No external links are configured for this mock item. Original and related sources will appear here after backend integration."}
          </div>
        )}
      </section>
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
