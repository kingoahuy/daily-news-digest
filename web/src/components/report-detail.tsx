"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Clock3,
  History,
  LoaderCircle,
  Mail,
  RefreshCw,
  Send,
} from "lucide-react";

import { NewsCard } from "@/components/news-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getReportByDate,
  getReportDeliveries,
  getReportNewsByDate,
  sendStoredReport,
} from "@/lib/api";
import type { ApiNews, ApiReport, EmailDelivery } from "@/types/api";

export function ReportDetail({ reportDate }: { reportDate: string }) {
  const [report, setReport] = useState<ApiReport | null>(null);
  const [news, setNews] = useState<ApiNews[]>([]);
  const [deliveries, setDeliveries] = useState<EmailDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [sendMessage, setSendMessage] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const currentReport = await getReportByDate(reportDate);
        const [items, history] = await Promise.all([
          getReportNewsByDate(reportDate),
          getReportDeliveries(currentReport.report_id),
        ]);
        if (active) {
          setReport(currentReport);
          setNews(items);
          setDeliveries(history);
        }
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "历史日报读取失败。",
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
  }, [reportDate]);

  const sendReport = async () => {
    if (!report) {
      return;
    }
    setSending(true);
    setError("");
    setSendMessage("");
    try {
      const result = await sendStoredReport(report.report_id);
      setSendMessage(result.message);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "邮件发送失败。",
      );
    } finally {
      try {
        const [updatedReport, history] = await Promise.all([
          getReportByDate(reportDate),
          getReportDeliveries(report.report_id),
        ]);
        setReport(updatedReport);
        setDeliveries(history);
      } catch {
        // Keep the send result visible even if the follow-up refresh fails.
      }
      setSending(false);
    }
  };

  if (loading) {
    return <StatusCard message="正在读取当日日报..." loading />;
  }
  if (!report) {
    return <StatusCard message={error || "该日期没有日报。"} destructive />;
  }

  return (
    <div className="space-y-9">
      <Link
        href="/history"
        className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        返回历史日报
      </Link>

      <header className="grid gap-6 xl:grid-cols-[1fr_auto] xl:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="rounded-full bg-card">
              <CalendarDays />
              {report.report_date}
            </Badge>
            <Badge
              variant={report.email_sent ? "secondary" : "outline"}
              className="rounded-full"
            >
              {report.email_sent ? <CheckCircle2 /> : <Mail />}
              {report.email_sent ? "邮件已发送" : "邮件未发送"}
            </Badge>
          </div>
          <h1 className="mt-5 max-w-5xl font-display text-4xl leading-tight font-semibold tracking-tight sm:text-5xl">
            {report.title}
          </h1>
          <p className="mt-4 max-w-4xl text-base leading-7 text-muted-foreground">
            核心议题：{report.core_topic || "暂无"}
          </p>
          <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock3 className="size-3.5" />
            生成时间：{formatDateTime(report.generated_at)}
          </p>
        </div>

        <Button
          size="lg"
          className="h-11 rounded-full px-5"
          disabled={sending}
          onClick={sendReport}
          aria-label={
            report.email_sent ? "重新发送这一天日报" : "发送这一天日报"
          }
        >
          {sending ? (
            <LoaderCircle className="animate-spin" />
          ) : report.email_sent ? (
            <RefreshCw />
          ) : (
            <Send />
          )}
          {sending
            ? "正在发送..."
            : report.email_sent
              ? "重新发送这一天日报"
              : "发送这一天日报"}
        </Button>
      </header>

      {sendMessage ? (
        <p className="rounded-xl border border-emerald-600/20 bg-emerald-600/8 px-4 py-3 text-sm text-emerald-700">
          {sendMessage}
        </p>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="rounded-xl border border-destructive/25 bg-destructive/8 px-4 py-3 text-sm text-destructive"
        >
          {error}
        </p>
      ) : null}

      <Card className="border-border/70 bg-card/88">
        <CardHeader>
          <CardTitle className="font-display text-2xl">完整 Markdown 日报</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border bg-background/60 p-5 font-sans text-sm leading-7 text-foreground/80">
            {report.markdown_content}
          </pre>
        </CardContent>
      </Card>

      <section>
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground uppercase">
              Stored stories
            </p>
            <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight">
              当日新闻
            </h2>
          </div>
          <span className="text-sm text-muted-foreground">{news.length} 条</span>
        </div>
        {news.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {news.map((article) => (
              <NewsCard key={article.id} article={article} />
            ))}
          </div>
        ) : (
          <StatusCard message="该日报没有保存新闻条目。" />
        )}
      </section>

      <Card className="border-border/70 bg-card/88">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-display text-2xl">
            <History className="size-5" />
            发送记录
          </CardTitle>
        </CardHeader>
        <CardContent>
          {deliveries.length ? (
            <div className="space-y-3">
              {deliveries.map((delivery) => (
                <div
                  key={delivery.id}
                  className="flex flex-col gap-3 rounded-xl border bg-background/55 p-4 sm:flex-row sm:items-center"
                >
                  <Badge
                    variant={
                      delivery.status === "success"
                        ? "secondary"
                        : "destructive"
                    }
                    className="rounded-full"
                  >
                    {delivery.status === "success" ? "成功" : "失败"}
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">
                      {delivery.delivery_type === "manual"
                        ? "手动发送"
                        : "自动发送"}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      {delivery.message}
                    </p>
                  </div>
                  <time className="text-xs text-muted-foreground">
                    {formatDateTime(delivery.sent_at)}
                  </time>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              这篇日报还没有邮件发送记录。
            </p>
          )}
        </CardContent>
      </Card>
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
    <Card className="mx-auto mt-16 max-w-2xl border-dashed bg-card/70">
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
