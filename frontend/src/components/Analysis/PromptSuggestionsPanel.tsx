import { AlertCircle, Lightbulb } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { PromptSuggestionsResponse } from "@/lib/types";

const CATEGORY_STYLES: Record<string, string> = {
  clarity: "text-blue-400 bg-blue-500/10",
  specificity: "text-purple-400 bg-purple-500/10",
  format: "text-amber-400 bg-amber-500/10",
  "few-shot": "text-emerald-400 bg-emerald-500/10",
  structure: "text-cyan-400 bg-cyan-500/10",
};

export default function PromptSuggestionsPanel({
  data,
  isLoading,
  error,
}: {
  data: PromptSuggestionsResponse | null;
  isLoading: boolean;
  error: string | null;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-red-400">
        <AlertCircle size={14} className="shrink-0" />
        <span>{error}</span>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-xs text-muted-foreground font-medium">
        Prompt Suggestions
      </h3>

      {data.suggestions.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <Lightbulb size={14} />
          Prompt looks good - no suggestions
        </div>
      )}

      <div className="space-y-3">
        {data.suggestions.map((suggestion, i) => (
          <div
            key={i}
            className="bg-card border-[0.5px] border-border rounded-md p-3"
          >
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`text-[11px] font-medium px-1.5 py-0.5 rounded-md ${CATEGORY_STYLES[suggestion.category] ?? "text-muted-foreground bg-muted"}`}
              >
                {suggestion.category}
              </span>
            </div>
            <p className="text-[13px] text-foreground leading-relaxed mb-2">
              {suggestion.description}
            </p>
            {suggestion.improved_prompt_snippet && (
              <div className="bg-emerald-500/5 border-[0.5px] border-emerald-500/20 rounded-md p-2">
                <div className="text-[11px] text-emerald-400 font-medium mb-1">
                  Suggested
                </div>
                <pre className="text-[12px] text-foreground font-mono whitespace-pre-wrap leading-relaxed">
                  {suggestion.improved_prompt_snippet}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
