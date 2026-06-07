"use client";

import { useEffect, useState } from "react";
import { Bookmark, LoaderCircle } from "lucide-react";

import { NewsCard } from "@/components/news-card";
import { Card, CardContent } from "@/components/ui/card";
import { getFavorites } from "@/lib/api";
import type { ApiNews } from "@/types/api";

export default function FavoritesPage() {
  const [items, setItems] = useState<ApiNews[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getFavorites()
      .then(setItems)
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : "收藏读取失败。",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          Saved stories
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          我的收藏
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">
          收藏记录来自本机 SQLite，取消收藏后会立即从这里移除。
        </p>
      </header>

      {loading ? (
        <EmptyState
          icon={LoaderCircle}
          message="正在读取收藏..."
          spin
        />
      ) : error ? (
        <EmptyState message={error} destructive />
      ) : items.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((article) => (
            <NewsCard
              key={article.id}
              article={article}
              onInteractionChange={(state) => {
                if (!state.favorited) {
                  setItems((current) =>
                    current.filter((item) => item.id !== article.id),
                  );
                }
              }}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Bookmark}
          message="还没有收藏新闻。你可以在日报卡片上点击收藏。"
        />
      )}
    </div>
  );
}

function EmptyState({
  icon: Icon,
  message,
  spin = false,
  destructive = false,
}: {
  icon?: typeof Bookmark;
  message: string;
  spin?: boolean;
  destructive?: boolean;
}) {
  return (
    <Card className="border-dashed bg-card/70">
      <CardContent className="flex min-h-56 flex-col items-center justify-center p-8 text-center">
        {Icon ? (
          <Icon className={`mb-4 size-7 ${spin ? "animate-spin" : ""}`} />
        ) : null}
        <p className={destructive ? "text-destructive" : "text-muted-foreground"}>
          {message}
        </p>
      </CardContent>
    </Card>
  );
}
