"use client";

import Link from "next/link";
import { ArrowRight, CalendarDays, Sparkles } from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { NewsCard } from "@/components/news-card";
import { ScoreBadge } from "@/components/score-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { articles, categories, reportMeta } from "@/data/mock-data";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const { language, text } = useLanguage();
  const coreArticle = articles[0];

  return (
    <div className="space-y-10">
      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="rounded-full bg-[#2f6f5e] text-white">
              <Sparkles className="size-3.5" />
              AI curated
            </Badge>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CalendarDays className="size-3.5" />
              {reportMeta.date}
            </span>
          </div>
          <h1 className="mt-5 max-w-4xl font-display text-4xl leading-[1.08] font-semibold tracking-[-0.035em] sm:text-5xl lg:text-6xl">
            {language === "zh" ? "今日新闻日报" : "Today’s News Digest"}
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            {text(reportMeta.overview)}
          </p>
        </div>

        <Card className="border-border/70 bg-primary text-primary-foreground shadow-[0_30px_70px_-42px_rgba(45,31,17,0.9)]">
          <CardContent className="flex h-full flex-col justify-between p-6">
            <div>
              <p className="text-xs tracking-[0.18em] text-primary-foreground/55 uppercase">
                {reportMeta.edition}
              </p>
              <p className="mt-4 font-display text-2xl leading-tight">
                {language === "zh"
                  ? "62 条新闻 → 10 条精选"
                  : "62 stories → 10 selected"}
              </p>
            </div>
            <div className="mt-8 grid grid-cols-3 gap-3 text-center">
              {[
                ["5", language === "zh" ? "分类" : "Topics"],
                ["8.1", language === "zh" ? "均分" : "Avg"],
                ["14", language === "zh" ? "来源" : "Sources"],
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

      <section className="relative overflow-hidden rounded-[2rem] border bg-[#f2e7d5] p-6 shadow-[0_26px_80px_-55px_rgba(90,56,17,0.8)] sm:p-8 lg:p-10">
        <div className="paper-grid absolute inset-0 opacity-35" />
        <div className="relative grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="text-xs font-semibold tracking-[0.2em] text-[#8a5a18] uppercase">
              {language === "zh" ? "今日核心议题" : "Today’s core topic"}
            </p>
            <h2 className="mt-4 max-w-4xl font-display text-3xl leading-tight font-semibold tracking-[-0.025em] sm:text-4xl">
              {text(reportMeta.coreTopic)}
            </h2>
            <p className="mt-5 max-w-3xl text-sm leading-7 text-foreground/70 sm:text-base">
              {text(coreArticle.fullSummary)}
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {coreArticle.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="rounded-full bg-white/45">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3 lg:flex-col lg:items-end">
            <ScoreBadge score={coreArticle.score} large />
            <Link
              href={`/news/${coreArticle.slug}`}
              className={cn(buttonVariants(), "rounded-full")}
            >
              {language === "zh" ? "阅读深度解读" : "Read the briefing"}
              <ArrowRight className="size-4" />
            </Link>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground uppercase">
              Curated feed
            </p>
            <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight">
              {language === "zh" ? "分类新闻" : "Stories by category"}
            </h2>
          </div>
          <Link
            href="/analytics"
            className="hidden items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground sm:flex"
          >
            {language === "zh" ? "查看分析" : "View analytics"}
            <ArrowRight className="size-4" />
          </Link>
        </div>

        <div className="space-y-10">
          {categories.map((category) => {
            const categoryArticles = articles
              .filter((article) => article.category === category.key)
              .slice(0, 2);
            return (
              <div key={category.key}>
                <div className="mb-4 flex items-center gap-3">
                  <span className={`size-2.5 rounded-full ${category.accent}`} />
                  <h3 className="font-display text-xl font-semibold">
                    {text(category.label)}
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {categoryArticles.length.toString().padStart(2, "0")}
                  </span>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  {categoryArticles.map((article) => (
                    <NewsCard
                      key={article.slug}
                      article={article}
                      category={category}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
