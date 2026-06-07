import { cn } from "@/lib/utils";

export function ScoreBadge({
  score,
  large = false,
}: {
  score: number;
  large?: boolean;
}) {
  const color =
    score >= 8.5
      ? "bg-[#2f6f5e] text-white"
      : score >= 7.5
        ? "bg-[#d99a35] text-[#2b2117]"
        : "bg-secondary text-secondary-foreground";

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-baseline justify-center rounded-full font-semibold tabular-nums",
        color,
        large ? "min-w-20 px-4 py-2 text-xl" : "min-w-12 px-2.5 py-1 text-xs",
      )}
      aria-label={`importance score ${score}`}
    >
      {score.toFixed(1)}
      <span className={cn("ml-0.5 opacity-70", large ? "text-xs" : "text-[9px]")}>
        /10
      </span>
    </span>
  );
}
