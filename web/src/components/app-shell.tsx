"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BookOpenText,
  LayoutDashboard,
  Radar,
  Settings,
} from "lucide-react";

import { LanguageToggle } from "@/components/language-toggle";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/", label: "日报", icon: LayoutDashboard },
  { href: "/analytics", label: "分析", icon: BarChart3 },
  { href: "/settings", label: "设置", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="sticky top-0 hidden h-screen border-r border-sidebar-border bg-sidebar/88 p-5 backdrop-blur-xl lg:flex lg:flex-col">
        <Link href="/" className="flex items-center gap-3 px-2 py-3">
          <span className="grid size-10 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
            <Radar className="size-5" />
          </span>
          <span>
            <span className="block font-display text-lg font-semibold">
              News Radar
            </span>
            <span className="text-xs text-muted-foreground">
              Daily intelligence
            </span>
          </span>
        </Link>

        <nav className="mt-8 space-y-1.5">
          {navigation.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/" || pathname.startsWith("/news/")
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                )}
              >
                <Icon className="size-4.5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-2xl border border-sidebar-border bg-background/55 p-4">
          <div className="flex items-center gap-2 text-sm font-medium">
            <BookOpenText className="size-4 text-[#b45309]" />
            前端预览版
          </div>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            当前使用独立 mock 数据，Python 抓取、邮件和 Actions 保持原样。
          </p>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/84 px-4 backdrop-blur-xl sm:px-6 lg:px-10">
          <Link href="/" className="flex items-center gap-2 lg:hidden">
            <span className="grid size-8 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Radar className="size-4" />
            </span>
            <span className="font-display font-semibold">News Radar</span>
          </Link>
          <div className="hidden items-center gap-2 text-xs text-muted-foreground lg:flex">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Static preview · Backend untouched
          </div>
          <LanguageToggle />
        </header>

        <main className="mx-auto w-full max-w-[1480px] px-4 pb-28 pt-6 sm:px-6 lg:px-10 lg:pb-12 lg:pt-9">
          {children}
        </main>
      </div>

      <nav className="fixed inset-x-3 bottom-3 z-40 grid grid-cols-3 rounded-2xl border bg-background/92 p-1.5 shadow-[0_18px_60px_-18px_rgba(42,32,20,0.45)] backdrop-blur-xl lg:hidden">
        {navigation.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/" || pathname.startsWith("/news/")
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-1 rounded-xl px-3 py-2 text-[11px] font-medium",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground",
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
