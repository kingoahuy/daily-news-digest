import type {
  AnalyticsData,
  ApiComment,
  ApiNews,
  ApiReport,
  DeliveryResult,
  EmailDelivery,
  GenerateTodayResult,
  InteractionState,
  PreferenceProfile,
  ReportSummary,
  SchedulerCheckResult,
  SchedulerStatus,
  SendTodayResult,
  TodayReportStatus,
  UserSettings,
  UserSettingsUpdate,
} from "@/types/api";

const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
const fallbackBases = [
  "http://localhost:8000",
  "http://localhost:8001",
  "http://localhost:8002",
];

let resolvedBasePromise: Promise<string> | null = null;

export class ApiRequestError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

async function resolveApiBase(): Promise<string> {
  if (configuredBase) {
    return configuredBase;
  }
  if (!resolvedBasePromise) {
    resolvedBasePromise = (async () => {
      for (const base of fallbackBases) {
        try {
          const response = await fetch(`${base}/api/health`, {
            cache: "no-store",
          });
          if (response.ok) {
            return base;
          }
        } catch {
          // Try the next local fallback port.
        }
      }
      throw new ApiRequestError(
        "本地后端未启动，请运行 python scripts/start_all.py。",
      );
    })();
  }
  return resolvedBasePromise;
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const base = await resolveApiBase();
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    resolvedBasePromise = null;
    throw new ApiRequestError(
      "本地后端未启动，请运行 python scripts/start_all.py。",
    );
  }

  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = (await response.json()) as {
        detail?: string | Array<{ msg?: string }>;
      };
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        const details = payload.detail
          .map((item) => item.msg)
          .filter((item): item is string => Boolean(item));
        if (details.length) {
          message = details.join("；");
        }
      }
    } catch {
      // Keep the status-based fallback message.
    }
    throw new ApiRequestError(message, response.status);
  }
  return (await response.json()) as T;
}

export const getLatestReport = () =>
  request<ApiReport>("/api/reports/latest");

export const getTodayReportStatus = () =>
  request<TodayReportStatus>("/api/reports/today-status");

export const generateTodayReport = () =>
  request<GenerateTodayResult>("/api/reports/generate-today", {
    method: "POST",
  });

export const sendTodayReport = () =>
  request<SendTodayResult>("/api/reports/send-today", {
    method: "POST",
  });

export const getReports = (filters?: {
  query?: string;
  category?: string;
  dateFrom?: string;
  dateTo?: string;
}) => {
  const params = new URLSearchParams();
  if (filters?.query) {
    params.set("query", filters.query);
  }
  if (filters?.category) {
    params.set("category", filters.category);
  }
  if (filters?.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters?.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  const query = params.toString();
  return request<ReportSummary[]>(`/api/reports${query ? `?${query}` : ""}`);
};

export const getReportByDate = (reportDate: string) =>
  request<ApiReport>(`/api/reports/by-date/${encodeURIComponent(reportDate)}`);

export const getReportNewsByDate = (reportDate: string) =>
  request<ApiNews[]>(
    `/api/reports/by-date/${encodeURIComponent(reportDate)}/news`,
  );

export const getReportNews = (reportId: number) =>
  request<ApiNews[]>(`/api/reports/${reportId}/news`);

export const sendStoredReport = (reportId: number) =>
  request<DeliveryResult>(`/api/reports/${reportId}/send`, {
    method: "POST",
  });

export const getReportDeliveries = (reportId: number) =>
  request<EmailDelivery[]>(`/api/reports/${reportId}/deliveries`);

export const getNews = (newsId: number) =>
  request<ApiNews>(`/api/news/${newsId}`);

export const getInteractions = (newsId: number) =>
  request<InteractionState>(`/api/news/${newsId}/interactions`);

export const toggleLike = (newsId: number) =>
  request<{ active: boolean; interactions: InteractionState }>(
    `/api/news/${newsId}/like`,
    { method: "POST" },
  );

export const toggleFavorite = (newsId: number) =>
  request<{ active: boolean; interactions: InteractionState }>(
    `/api/news/${newsId}/favorite`,
    { method: "POST" },
  );

export const getComments = (newsId: number) =>
  request<ApiComment[]>(`/api/news/${newsId}/comments`);

export const addComment = (newsId: number, content: string) =>
  request<{ id: number; interactions: InteractionState }>(
    `/api/news/${newsId}/comments`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
  );

export const getFavorites = () => request<ApiNews[]>("/api/favorites");

export const getProfile = () =>
  request<PreferenceProfile>("/api/profile");

export const getAnalytics = () =>
  request<AnalyticsData>("/api/analytics");

export const getUserSettings = () =>
  request<UserSettings>("/api/settings");

export const updateUserSettings = (settings: UserSettingsUpdate) =>
  request<UserSettings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });

export const getSchedulerStatus = () =>
  request<SchedulerStatus>("/api/scheduler/status");

export const checkSchedulerOnce = () =>
  request<SchedulerCheckResult>("/api/scheduler/check-once", {
    method: "POST",
  });
