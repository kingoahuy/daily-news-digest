export type LanguageMode = "zh" | "en";

export type NewsCategory =
  | "finance"
  | "sports"
  | "politics"
  | "society"
  | "technology";

export type LocalizedText = {
  zh: string;
  en: string;
};

export type NewsArticle = {
  slug: string;
  category: NewsCategory;
  title: LocalizedText;
  summary: LocalizedText;
  fullSummary: LocalizedText;
  whyItMatters: LocalizedText;
  background: LocalizedText;
  beginnerExplanation: LocalizedText;
  source: string;
  publishedAt: string;
  score: number;
  tags: string[];
  relatedLinks: Array<{
    label: LocalizedText;
    url: string;
  }>;
};

export type CategoryMeta = {
  key: NewsCategory;
  label: LocalizedText;
  accent: string;
};
