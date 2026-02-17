import { useState } from "react";
import type { Span } from "@/lib/types";
import { useTraceStore } from "@/store/trace";
import { Button } from "@/components/ui/button";
import PromptEditor from "./PromptEditor";

interface ReplayPanelProps {
  span: Span;
}

function formatPrompt(value: unknown): string {
  if (typeof value !== "string") return "[]";
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

export default function ReplayPanel({ span }: ReplayPanelProps) {
  const runReplay = useTraceStore((s) => s.runReplay);
  const clearReplay = useTraceStore((s) => s.clearReplay);
  const replayResult = useTraceStore((s) => s.replayResult);
  const isReplaying = useTraceStore((s) => s.isReplaying);

  const rawPrompt = span.attributes["llm.prompt"];
  const [editedPrompt, setEditedPrompt] = useState(formatPrompt(rawPrompt));

  const handleReplay = () => {
    runReplay(span.span_id, { "llm.prompt": editedPrompt });
  };

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold">Replay</h4>

      {/* Prompt Editor */}
      <div className="rounded overflow-hidden border border-border">
        <PromptEditor initialValue={editedPrompt} onChange={setEditedPrompt} />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={handleReplay} disabled={isReplaying}>
          {isReplaying ? "Replaying..." : "Replay"}
        </Button>
        {replayResult && (
          <Button size="sm" variant="ghost" onClick={clearReplay}>
            Clear
          </Button>
        )}
      </div>

      {/* Diff View */}
      {replayResult && (
        <div className="space-y-2">
          {!replayResult.diff.changed ? (
            <div className="text-xs text-muted-foreground">
              No changes in output.
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs font-semibold mb-1">Original</div>
                <pre className="text-xs bg-red-950/20 border border-red-900/30 rounded p-2 whitespace-pre-wrap max-h-[200px] overflow-auto">
                  {replayResult.diff.old_completion}
                </pre>
              </div>
              <div>
                <div className="text-xs font-semibold mb-1">Replayed</div>
                <pre className="text-xs bg-green-950/20 border border-green-900/30 rounded p-2 whitespace-pre-wrap max-h-[200px] overflow-auto">
                  {replayResult.diff.new_completion}
                </pre>
              </div>
            </div>
          )}

          {/* Token/cost comparison */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-muted rounded p-2">
              <div className="text-muted-foreground">New tokens (in/out)</div>
              <div className="font-medium">
                {replayResult.new_output["llm.tokens.input"]} /{" "}
                {replayResult.new_output["llm.tokens.output"]}
              </div>
            </div>
            <div className="bg-muted rounded p-2">
              <div className="text-muted-foreground">New cost</div>
              <div className="font-medium">
                ${replayResult.new_output["llm.cost_usd"].toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
