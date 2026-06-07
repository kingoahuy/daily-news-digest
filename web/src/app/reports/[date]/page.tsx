import { ReportDetail } from "@/components/report-detail";

export default async function HistoricalReportPage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  return <ReportDetail reportDate={date} />;
}
