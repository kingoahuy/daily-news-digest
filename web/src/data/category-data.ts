import type { CategoryMeta, NewsCategory } from "@/types/news";

export const categories: CategoryMeta[] = [
  {
    key: "technology",
    label: { zh: "科技", en: "Technology" },
    accent: "bg-[#d97706]",
  },
  {
    key: "finance",
    label: { zh: "财经", en: "Finance" },
    accent: "bg-[#0f766e]",
  },
  {
    key: "sports",
    label: { zh: "体育", en: "Sports" },
    accent: "bg-[#2563eb]",
  },
  {
    key: "politics",
    label: { zh: "政治", en: "Politics" },
    accent: "bg-[#7c3aed]",
  },
  {
    key: "society",
    label: { zh: "社会", en: "Society" },
    accent: "bg-[#be123c]",
  },
];

export const categoryMap = Object.fromEntries(
  categories.map((category) => [category.key, category]),
) as Record<NewsCategory, CategoryMeta>;
