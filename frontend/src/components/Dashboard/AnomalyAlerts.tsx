import { AlertTriangle, CheckCircle, Settings, Loader2 } from "lucide-react";
import type { Anomaly } from "@/lib/types";

const SEVERITY_STYLES: Record<string, string> = {
  high: "text-red-400 bg-red-500/10",
  medium: "text-amber-400 bg-amber-500/10",
  low: "text-muted-foreground bg-muted",
};

export default function AnomalyAlerts({
  anomalies,
  isLoading,
  error,
  onNavigate,
}: {
  anomalies: Anomaly[];
  isLoading: boolean;
  error: string | null;
  onNavigate: (path: string) => void;
}) {
  return (
    <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
      <h3 className="text-xs text-muted-foreground font-medium mb-3">
        Anomaly Detection
      </h3>

      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 size={14} className="animate-spin" />
          Analyzing latest trace...
        </div>
      )}

      {!isLoading && error && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Settings size={14} />
          <span>
            Configure an API key in{" "}
            <button
              type="button"
              onClick={() => onNavigate("/settings")}
              className="text-primary hover:underline"
            >
              Settings
            </button>{" "}
            to enable AI-powered anomaly detection.
          </span>
        </div>
      )}

      {!isLoading && !error && anomalies.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <CheckCircle size={14} />
          No anomalies detected
        </div>
      )}

      {!isLoading && !error && anomalies.length > 0 && (
        <div className="space-y-2">
          {anomalies.map((a) => (
            <button
              key={`${a.trace_id}-${a.span_id}-${a.type}`}
              type="button"
              onClick={() =>
                onNavigate(
                  `/traces/${a.trace_id}${a.span_id ? `/${a.span_id}` : ""}`,
                )
              }
              className="w-full text-left flex items-start gap-2.5 p-2 rounded-md hover:bg-secondary/50 transition-colors"
            >
              <AlertTriangle size={14} className="text-amber-400 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[11px] font-medium px-1.5 py-0.5 rounded-md ${SEVERITY_STYLES[a.severity] ?? SEVERITY_STYLES.low}`}
                  >
                    {a.severity}
                  </span>
                  <span className="text-xs text-muted-foreground">{a.type}</span>
                </div>
                <p className="text-[13px] text-foreground mt-1 leading-relaxed">
                  {a.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
