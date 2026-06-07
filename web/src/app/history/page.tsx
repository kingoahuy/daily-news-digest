"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Filter,
  LoaderCircle,
  MessageSquareText,
  Newspaper,
  Search,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { categories } from "@/data/category-data";
import { getReports } from "@/lib/api";
import type { ReportSummary } from "@/types/api";

export default function HistoryPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadReports = async (filters?: {
    query?: string;
    category?: string;
    dateFrom?: string;
    dateTo?: string;
  }) => {
    setLoading(true);
    setError("");
    try {
      setReports(await getReports(filters));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "历史日报读取失败。",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    getReports()
      .then((items) => {
        if (active) {
          setReports(items);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "历史日报读取失败。",
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void loadReports({ query, category, dateFrom, dateTo });
  };

  const reset = () => {
    setQuery("");
    setCategory("");
    setDateFrom("");
    setDateTo("");
    void loadReports();
  };

  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          Report archive
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          历史日报
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          查看 SQLite 中已经生成的日报、当日新闻和互动，并可直接重新发送存量邮件。
        </p>
      </header>

      <Card className="border-border/70 bg-card/88">
        <CardContent className="p-5">
          <form
            onSubmit={submit}
            className="grid gap-4 lg:grid-cols-[1.5fr_0.8fr_0.8fr_0.8fr_auto]"
          >
            <label>
              <span className="mb-2 block text-xs font-medium text-muted-foreground">
                搜索
              </span>
              <span className="relative block">
                <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  aria-label="搜索历史日报"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="标题、核心议题或新闻..."
                  className="h-10 w-full rounded-xl border bg-background pr-3 pl-9 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/20"
                />
              </span>
            </label>
            <label>
              <span className="mb-2 block text-xs font-medium text-muted-foreground">
                分类
              </span>
              <select
                aria-label="按分类筛选"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="h-10 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:border-ring"
              >
                <option value="">全部分类</option>
                {categories.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label.zh}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="mb-2 block text-xs font-medium text-muted-foreground">
                开始日期
              </span>
              <input
                type="date"
                aria-label="开始日期"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
                className="h-10 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:border-ring"
              />
            </label>
            <label>
              <span className="mb-2 block text-xs font-medium text-muted-foreground">
                结束日期
              </span>
              <input
                type="date"
                aria-label="结束日期"
                value={dateTo}
                onChange={(event) => setDateTo(event.target.value)}
                className="h-10 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:border-ring"
              />
            </label>
            <div className="flex items-end gap-2">
              <Button type="submit" className="h-10 rounded-xl px-4">
                <Filter />
                筛选
              </Button>
              <Button
                type="button"
                variant="outline"
                className="h-10 rounded-xl"
                onClick={reset}
              >
                重置
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {loading ? (
        <StatusCard message="正在读取历史日报..." loading />
      ) : error ? (
        <StatusCard message={error} destructive />
      ) : reports.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {reports.map((report) => (
            <Link
              key={report.report_id}
              href={`/reports/${report.report_date}`}
              className="group"
            >
              <Card className="h-full border-border/70 bg-card/88 transition-all group-hover:-translate-y-0.5 group-hover:border-foreground/20 group-hover:shadow-lg">
                <CardContent className="p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="flex items-center gap-2 font-mono text-sm font-semibold">
                      <CalendarDays className="size-4 text-[#b45309]" />
                      {report.report_date}
                    </span>
                    <Badge
                      variant={report.email_sent ? "secondary" : "outline"}
                      className="rounded-full"
                    >
                      {report.email_sent ? (
                        <CheckCircle2 className="size-3" />
                      ) : null}
                      {report.email_sent ? "已发送" : "未发送"}
                    </Badge>
                  </div>
                  <h2 className="mt-5 font-display text-2xl leading-tight font-semibold tracking-tight">
                    {report.title}
                  </h2>
                  <p className="mt-3 line-clamp-2 text-sm leading-6 text-muted-foreground">
                    {report.core_topic || "该日报暂无核心议题。"}
                  </p>
                  <div className="mt-6 flex flex-wrap gap-4 border-t pt-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <Newspaper className="size-3.5" />
                      {report.news_count} 条新闻
                    </span>
                    <span className="flex items-center gap-1.5">
                      <MessageSquareText className="size-3.5" />
                      {report.interaction_count} 次互动
                    </span>
                    <span className="ml-auto">
                      {formatDateTime(report.generated_at)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <StatusCard message="没有找到符合条件的历史日报。" />
      )}
    </div>
  );
}

function StatusCard({
  message,
  loading = false,
  destructive = false,
}: {
  message: string;
  loading?: boolean;
  destructive?: boolean;
}) {
  return (
    <Card className="border-dashed bg-card/70">
      <CardContent className="flex min-h-52 flex-col items-center justify-center p-8 text-center">
        {loading ? (
          <LoaderCircle className="mb-4 size-7 animate-spin" />
        ) : null}
        <p className={destructive ? "text-destructive" : "text-muted-foreground"}>
          {message}
        </p>
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
