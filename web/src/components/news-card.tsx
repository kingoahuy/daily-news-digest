"use client";

import Link from "next/link";
import { ArrowUpRight, Clock3 } from "lucide-react";

import { useLanguage } from "@/components/language-provider";
import { ScoreBadge } from "@/components/score-badge";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { CategoryMeta, NewsArticle } from "@/types/news";

export function NewsCard({
  article,
  category,
}: {
  article: NewsArticle;
  category: CategoryMeta;
}) {
  const { text } = useLanguage();

  return (
    <Card className="group h-full gap-0 overflow-hidden border-border/75 bg-card/88 py-0 shadow-[0_14px_42px_-32px_rgba(51,38,20,0.8)] transition-all hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-[0_22px_50px_-30px_rgba(51,38,20,0.55)]">
      <CardHeader className="gap-4 p-5 pb-3">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="outline" className="rounded-full bg-background/70">
            <span className={`mr-1.5 size-1.5 rounded-full ${category.accent}`} />
            {text(category.label)}
          </Badge>
          <ScoreBadge score={article.score} />
        </div>
        <CardTitle className="font-display text-xl leading-snug tracking-[-0.01em]">
          <Link href={`/news/${article.slug}`} className="hover:underline">
            {text(article.title)}
          </Link>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-5 pb-4">
        <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
          {text(article.summary)}
        </p>
      </CardContent>
      <CardFooter className="mt-auto flex items-center justify-between border-t border-border/60 px-5 py-3.5 text-xs text-muted-foreground">
        <div className="min-w-0">
          <span className="block truncate font-medium text-foreground/75">
            {article.source}
          </span>
          <span className="mt-0.5 flex items-center gap-1">
            <Clock3 className="size-3" />
            {article.publishedAt}
          </span>
        </div>
        <Link
          href={`/news/${article.slug}`}
          className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary text-secondary-foreground transition-colors group-hover:bg-primary group-hover:text-primary-foreground"
          aria-label={`Read ${text(article.title)}`}
        >
          <ArrowUpRight className="size-4" />
        </Link>
      </CardFooter>
    </Card>
  );
}
