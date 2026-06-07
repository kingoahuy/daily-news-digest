import { notFound } from "next/navigation";

import { ArticleDetail } from "@/components/article-detail";
import { getArticle } from "@/data/mock-data";

export default async function NewsDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getArticle(slug);

  if (!article) {
    notFound();
  }

  return <ArticleDetail article={article} />;
}
