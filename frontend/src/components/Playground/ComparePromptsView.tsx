import { useState, useRef, useCallback } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import ModelSelector from "./ModelSelector";
import { usePlaygroundStore } from "@/store/playground";

function formatCost(usd: number): string {
  if (usd < 0.001) return `$${usd.toFixed(5)}`;
  return `$${usd.toFixed(4)}`;
}

export default function ComparePromptsView() {
  const [promptA, setPromptA] = useState("");
  const [promptB, setPromptB] = useState("");
  const textareaARef = useRef<HTMLTextAreaElement>(null);
  const textareaBRef = useRef<HTMLTextAreaElement>(null);

  const promptCompareModel = usePlaygroundStore((s) => s.promptCompareModel);
  const setPromptCompareModel = usePlaygroundStore((s) => s.setPromptCompareModel);
  const promptCompareResults = usePlaygroundStore((s) => s.promptCompareResults);
  const isComparingPrompts = usePlaygroundStore((s) => s.isComparingPrompts);
  const runPromptComparison = usePlaygroundStore((s) => s.runPromptComparison);

  const canRun = promptA.trim() && promptB.trim() && !isComparingPrompts;

  const handleRun = () => {
    if (!canRun) return;
    void runPromptComparison([promptA.trim(), promptB.trim()]);
  };

  const handleTextareaChange = useCallback(
    (
      e: React.ChangeEvent<HTMLTextAreaElement>,
      setter: (v: string) => void,
    ) => {
      setter(e.target.value);
      e.target.style.height = "auto";
      e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
    },
    [],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Model selector */}
      <div className="border-b border-border p-4">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Model:</span>
          <ModelSelector
            value={promptCompareModel}
            onChange={setPromptCompareModel}
            disabled={isComparingPrompts}
          />
        </div>
      </div>

      {/* Results area */}
      <div className="flex-1 overflow-y-auto p-4">
        {!promptCompareResults && !isComparingPrompts && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-muted-foreground text-sm">
                Enter two different prompts to compare responses.
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                Same model, different prompts — see how wording affects the
                output.
              </p>
            </div>
          </div>
        )}

        {isComparingPrompts && (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 size={16} className="animate-spin" />
              Running A/B test with {promptCompareModel}...
            </div>
          </div>
        )}

        {promptCompareResults && (
          <div className="grid grid-cols-2 gap-4">
            {promptCompareResults.map((result, i) => (
              <div
                key={i}
                className="bg-card border-[0.5px] border-border rounded-lg overflow-hidden shadow-[0_2px_8px_oklch(0_0_0/0.15)]"
              >
                <div className="bg-secondary px-4 py-3 border-b border-border">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">
                      Prompt {String.fromCharCode(65 + i)}
                    </span>
                    <Badge variant="outline" className="text-xs ml-2 flex-none font-mono">
                      {promptCompareModel}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>
                      {result.metrics.input_tokens + result.metrics.output_tokens}{" "}
                      tok
                    </span>
                    <span>{formatCost(result.metrics.cost_usd)}</span>
                    <span>
                      {(result.metrics.latency_ms / 1000).toFixed(1)}s
                    </span>
                  </div>
                </div>
                <div className="px-4 py-2 border-b border-border/60 bg-muted/30">
                  <p className="text-[11px] text-muted-foreground line-clamp-2">
                    {result.prompt}
                  </p>
                </div>
                <div className="p-4">
                  <p className="text-[13px] leading-relaxed whitespace-pre-wrap">
                    {result.completion}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dual prompt composers */}
      <div className="border-t border-border p-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-card border-[0.5px] border-border rounded-lg p-2 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
            <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide px-2 pb-1">
              Prompt A
            </div>
            <textarea
              ref={textareaARef}
              className="w-full bg-transparent resize-none text-[13px] placeholder:text-muted-foreground/60 focus:outline-none min-h-[36px] max-h-[160px] py-1.5 px-2 leading-relaxed"
              placeholder="Enter first prompt..."
              rows={2}
              value={promptA}
              onChange={(e) => handleTextareaChange(e, setPromptA)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.metaKey) {
                  e.preventDefault();
                  handleRun();
                }
              }}
              disabled={isComparingPrompts}
            />
          </div>
          <div className="bg-card border-[0.5px] border-border rounded-lg p-2 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
            <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide px-2 pb-1">
              Prompt B
            </div>
            <textarea
              ref={textareaBRef}
              className="w-full bg-transparent resize-none text-[13px] placeholder:text-muted-foreground/60 focus:outline-none min-h-[36px] max-h-[160px] py-1.5 px-2 leading-relaxed"
              placeholder="Enter second prompt..."
              rows={2}
              value={promptB}
              onChange={(e) => handleTextareaChange(e, setPromptB)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.metaKey) {
                  e.preventDefault();
                  handleRun();
                }
              }}
              disabled={isComparingPrompts}
            />
          </div>
        </div>
        <div className="flex items-center justify-end mt-2">
          <Button
            size="sm"
            onClick={handleRun}
            disabled={!canRun}
            className="gap-1.5"
          >
            {isComparingPrompts ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            Run A/B Test
          </Button>
        </div>
      </div>
    </div>
  );
}
