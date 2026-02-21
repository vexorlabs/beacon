import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import type { Anomaly } from "@/lib/types";

const SEVERITY_STYLES: Record<string, string> = {
  high: "text-red-400 bg-red-500/10 border-red-500/20",
  medium: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  low: "text-muted-foreground bg-muted border-border",
};

export default function AnomalyBanner({
  anomalies,
  onSpanClick,
}: {
  anomalies: Anomaly[];
  onSpanClick?: (spanId: string) => void;
}) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || anomalies.length === 0) return null;

  const highestSeverity = anomalies.some((a) => a.severity === "high")
    ? "high"
    : anomalies.some((a) => a.severity === "medium")
      ? "medium"
      : "low";

  const style =
    SEVERITY_STYLES[highestSeverity] ?? SEVERITY_STYLES.low;

  return (
    <div
      className={`flex items-start gap-2.5 p-3 rounded-lg border-[0.5px] ${style}`}
    >
      <AlertTriangle size={14} className="mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-medium mb-1">
          {anomalies.length} anomal{anomalies.length === 1 ? "y" : "ies"}{" "}
          detected
        </div>
        <div className="space-y-1">
          {anomalies.map((a, i) => (
            <button
              key={i}
              type="button"
              className="block text-left text-[13px] leading-relaxed opacity-90 hover:opacity-100 transition-opacity cursor-pointer"
              onClick={() => a.span_id && onSpanClick?.(a.span_id)}
            >
              {a.description}
            </button>
          ))}
        </div>
      </div>
      <button
        type="button"
        aria-label="Dismiss anomalies"
        onClick={() => setDismissed(true)}
        className="text-current opacity-50 hover:opacity-100 transition-opacity cursor-pointer shrink-0"
      >
        <X size={14} />
      </button>
    </div>
  );
}
