"use client";

import Link from "next/link";
import { Clock3 } from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { NewsInteractions } from "@/components/news-interactions";
import { ScoreBadge } from "@/components/score-badge";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { categoryMap } from "@/data/category-data";
import type { ApiNews, InteractionState } from "@/types/api";

export function NewsCard({
  article,
  onInteractionChange,
}: {
  article: ApiNews;
  onInteractionChange?: (state: InteractionState) => void;
}) {
  const { text } = useLanguage();
  const category = categoryMap[article.category] ?? categoryMap.society;
  const score = article.ai_score || article.score;

  return (
    <Card className="group h-full gap-0 overflow-hidden border-border/75 bg-card/88 py-0 shadow-[0_14px_42px_-32px_rgba(51,38,20,0.8)] transition-all hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-[0_22px_50px_-30px_rgba(51,38,20,0.55)]">
      <CardHeader className="gap-4 p-5 pb-3">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="outline" className="rounded-full bg-background/70">
            <span className={`mr-1.5 size-1.5 rounded-full ${category.accent}`} />
            {text(category.label)}
          </Badge>
          <ScoreBadge score={score} />
        </div>
        <CardTitle className="font-display text-xl leading-snug tracking-[-0.01em]">
          <Link href={`/news/${article.id}`} className="hover:underline">
            {article.title}
          </Link>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-5 pb-4">
        <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
          {article.ai_summary || article.summary || "暂无摘要。"}
        </p>
        {article.ai_reason ? (
          <p className="mt-3 line-clamp-2 text-xs leading-5 text-foreground/65">
            <span className="font-medium text-foreground">推荐理由：</span>
            {article.ai_reason}
          </p>
        ) : null}
      </CardContent>
      <CardFooter className="mt-auto block border-t border-border/60 px-5 py-3.5">
        <div className="mb-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <span className="truncate font-medium text-foreground/75">
            {article.source}
          </span>
          <span className="flex shrink-0 items-center gap-1">
            <Clock3 className="size-3" />
            {formatPublishedAt(article.published_at)}
          </span>
        </div>
        <NewsInteractions
          newsId={article.id}
          url={article.url}
          initialState={article.interactions}
          compact
          onStateChange={onInteractionChange}
        />
      </CardFooter>
    </Card>
  );
}

function formatPublishedAt(value: string) {
  if (!value) {
    return "时间未知";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
}
