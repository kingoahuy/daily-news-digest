import type { NewsCategory } from "@/types/news";

export type ApiReport = {
  report_id: number;
  report_date: string;
  title: string;
  core_topic: string;
  markdown_content: string;
  generated_at: string;
  email_sent: boolean;
};

export type ReportSummary = {
  report_id: number;
  report_date: string;
  title: string;
  core_topic: string;
  email_sent: boolean;
  generated_at: string;
  news_count: number;
  interaction_count: number;
};

export type EmailDelivery = {
  id: number;
  report_id: number;
  report_date: string;
  delivery_type: "manual" | "scheduled";
  status: "success" | "failed";
  message: string;
  sent_at: string;
};

export type DeliveryResult = {
  delivery_id: number;
  report_id: number;
  report_date: string;
  delivery_type: "manual" | "scheduled";
  status: "success" | "failed";
  message: string;
};

export type TodayReportStatus = {
  today: string;
  has_today_report: boolean;
  latest_report_date: string;
  latest_report_id: number;
  is_showing_stale_report: boolean;
  message: string;
};

export type GenerateTodayResult = {
  status: "exists" | "generated";
  message: string;
  report: ApiReport;
  today_status: TodayReportStatus;
};

export type InteractionState = {
  liked: boolean;
  favorited: boolean;
  comment_count: number;
};

export type Enrichment = {
  whats_new?: string;
  why_it_matters?: string;
  background?: string;
  possible_impact?: string;
  follow_up_points?: string[];
};

export type ApiNews = {
  id: number;
  report_id: number;
  title: string;
  summary: string;
  url: string;
  source: string;
  category: NewsCategory;
  published_at: string;
  score: number;
  ai_score: number;
  ai_reason: string;
  ai_summary: string;
  ai_tags: string[];
  importance_tier: string;
  cluster_title: string;
  enrichment: Enrichment;
  interactions: InteractionState;
  favorited_at?: string;
};

export type ApiComment = {
  id: number;
  content: string;
  created_at: string;
};

export type PreferenceProfile = {
  category_weights: Record<string, number>;
  interaction_category_adjustments: Record<string, number>;
  interaction_keyword_adjustments: Record<string, number>;
  interaction_source_adjustments: Record<string, number>;
  action_category_counts: Record<string, Record<string, number>>;
  comment_topic_counts: Record<string, number>;
  positive_comment_count: number;
  negative_comment_count: number;
  interaction_count: number;
  interaction_summary: {
    like: number;
    favorite: number;
    comment: number;
    total: number;
  };
};

export type AnalyticsData = {
  report_count: number;
  latest_news_count: number;
  category_counts: Record<string, number>;
  source_counts: Record<string, number>;
  trend: Array<{
    date: string;
    important_count: number;
    average_score: number;
  }>;
  interaction_summary: {
    like: number;
    favorite: number;
    comment: number;
    total: number;
  };
};

export type UserSettings = {
  email_enabled: boolean;
  email_send_time: string;
  timezone: string;
  auto_send_local_enabled: boolean;
  send_grace_minutes: number;
  auto_generate_today_on_web_start: boolean;
  low_api_mode: boolean;
  max_total_news: number;
  max_items_per_category: number;
  enable_bilingual_report: boolean;
  enable_enrichment: boolean;
  updated_at: string;
};

export type UserSettingsUpdate = Omit<UserSettings, "updated_at">;

export type SchedulerLatestRun = {
  id: number;
  run_date: string;
  scheduled_time: string;
  actual_time?: string;
  status: "success" | "failed" | "skipped" | "pending";
  message: string;
  created_at: string;
};

export type SchedulerStatus = {
  email_enabled: boolean;
  auto_send_local_enabled: boolean;
  send_grace_minutes: number;
  timezone: string;
  current_time: string;
  scheduled_time: string;
  today: string;
  sent_today: boolean;
  running: boolean;
  pid: number;
  state: string;
  message: string;
  checked_at: string;
  started_at: string;
  log_file: string;
  latest_run: SchedulerLatestRun | null;
  warning: string;
};

export type SchedulerCheckResult = {
  status: "ok";
  output: string;
  scheduler: SchedulerStatus;
};
