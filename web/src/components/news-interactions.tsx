"use client";

import { useState } from "react";
import {
  Bookmark,
  ExternalLink,
  Heart,
  LoaderCircle,
  MessageCircle,
  Send,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  addComment,
  getComments,
  toggleFavorite,
  toggleLike,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ApiComment, InteractionState } from "@/types/api";

export function NewsInteractions({
  newsId,
  url,
  initialState,
  compact = false,
  onStateChange,
}: {
  newsId: number;
  url: string;
  initialState: InteractionState;
  compact?: boolean;
  onStateChange?: (state: InteractionState) => void;
}) {
  const [state, setState] = useState(initialState);
  const [comments, setComments] = useState<ApiComment[]>([]);
  const [commentOpen, setCommentOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState<"like" | "favorite" | "comment" | null>(
    null,
  );
  const [error, setError] = useState("");

  const updateState = (next: InteractionState) => {
    setState(next);
    onStateChange?.(next);
  };

  const loadComments = async () => {
    setError("");
    try {
      setComments(await getComments(newsId));
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "评论读取失败。",
      );
    }
  };

  const toggleComments = async () => {
    const next = !commentOpen;
    setCommentOpen(next);
    if (next) {
      await loadComments();
    }
  };

  const submitComment = async () => {
    const content = comment.trim();
    if (!content) {
      return;
    }
    setBusy("comment");
    setError("");
    try {
      const result = await addComment(newsId, content);
      updateState(result.interactions);
      setComment("");
      await loadComments();
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "评论保存失败。",
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="w-full">
      <div className="flex flex-wrap items-center gap-1.5">
        <Button
          variant={state.liked ? "default" : "ghost"}
          size="sm"
          aria-label={state.liked ? "取消点赞" : "点赞"}
          aria-pressed={state.liked}
          disabled={busy !== null}
          onClick={async () => {
            setBusy("like");
            setError("");
            try {
              updateState((await toggleLike(newsId)).interactions);
            } catch (requestError) {
              setError(
                requestError instanceof Error
                  ? requestError.message
                  : "点赞操作失败。",
              );
            } finally {
              setBusy(null);
            }
          }}
        >
          {busy === "like" ? (
            <LoaderCircle className="size-3.5 animate-spin" />
          ) : (
            <Heart className={cn("size-3.5", state.liked && "fill-current")} />
          )}
          {!compact && (state.liked ? "已赞" : "点赞")}
        </Button>
        <Button
          variant={state.favorited ? "default" : "ghost"}
          size="sm"
          aria-label={state.favorited ? "取消收藏" : "收藏"}
          aria-pressed={state.favorited}
          disabled={busy !== null}
          onClick={async () => {
            setBusy("favorite");
            setError("");
            try {
              updateState((await toggleFavorite(newsId)).interactions);
            } catch (requestError) {
              setError(
                requestError instanceof Error
                  ? requestError.message
                  : "收藏操作失败。",
              );
            } finally {
              setBusy(null);
            }
          }}
        >
          {busy === "favorite" ? (
            <LoaderCircle className="size-3.5 animate-spin" />
          ) : (
            <Bookmark
              className={cn("size-3.5", state.favorited && "fill-current")}
            />
          )}
          {!compact && (state.favorited ? "已收藏" : "收藏")}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          aria-label={`评论，当前 ${state.comment_count} 条`}
          aria-expanded={commentOpen}
          onClick={toggleComments}
        >
          <MessageCircle className="size-3.5" />
          {state.comment_count}
        </Button>
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="ml-auto inline-flex h-7 items-center gap-1 rounded-lg px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <ExternalLink className="size-3.5" />
          原文
        </a>
      </div>

      {commentOpen ? (
        <div className="mt-3 rounded-xl border bg-background/70 p-3">
          <div className="flex gap-2">
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="写下你的看法..."
              maxLength={2000}
              rows={compact ? 2 : 3}
              className="min-h-16 flex-1 resize-y rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/15"
            />
            <Button
              size="icon"
              aria-label="提交评论"
              disabled={!comment.trim() || busy !== null}
              onClick={submitComment}
            >
              {busy === "comment" ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <Send />
              )}
            </Button>
          </div>
          {comments.length ? (
            <div className="mt-3 space-y-2">
              {comments.map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg bg-muted/65 px-3 py-2 text-xs leading-5"
                >
                  <p>{item.content}</p>
                  <time className="mt-1 block text-[10px] text-muted-foreground">
                    {formatDateTime(item.created_at)}
                  </time>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-xs text-muted-foreground">
              还没有评论，写下第一条看法。
            </p>
          )}
        </div>
      ) : null}

      {error ? (
        <p className="mt-2 text-xs text-destructive">{error}</p>
      ) : null}
    </div>
  );
}

function formatDateTime(value: string) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("zh-CN", { hour12: false });
}
