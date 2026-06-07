import { ArticleDetail } from "@/components/article-detail";

export default async function NewsDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const newsId = Number(slug);
  if (!Number.isInteger(newsId) || newsId <= 0) {
    return <ArticleDetail newsId={-1} />;
  }
  return <ArticleDetail newsId={newsId} />;
}
