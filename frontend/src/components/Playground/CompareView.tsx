import { useState, useRef, useCallback } from "react";
import { Send, Loader2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { usePlaygroundStore } from "@/store/playground";
import { MODELS } from "./ModelSelector";

function formatCost(usd: number): string {
  if (usd < 0.001) return `$${usd.toFixed(5)}`;
  return `$${usd.toFixed(4)}`;
}

export default function CompareView() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const compareModels = usePlaygroundStore((s) => s.compareModels);
  const toggleCompareModel = usePlaygroundStore((s) => s.toggleCompareModel);
  const compareResults = usePlaygroundStore((s) => s.compareResults);
  const isComparing = usePlaygroundStore((s) => s.isComparing);
  const runComparison = usePlaygroundStore((s) => s.runComparison);

  const handleCompare = () => {
    const trimmed = input.trim();
    if (!trimmed || isComparing || compareModels.length < 2) return;
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    runComparison(trimmed);
  };

  const handleTextareaChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      e.target.style.height = "auto";
      e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
    },
    [],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Model selector */}
      <div className="border-b border-border p-4">
        <p className="text-xs text-muted-foreground mb-2">
          Select 2 or more models to compare:
        </p>
        <div className="flex flex-wrap gap-2">
          {MODELS.map((group) =>
            group.models.map((model) => {
              const selected = compareModels.includes(model);
              return (
                <button
                  key={model}
                  type="button"
                  onClick={() => toggleCompareModel(model)}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md border text-xs font-mono transition-colors ${
                    selected
                      ? "border-primary bg-primary/10 text-foreground"
                      : "border-border text-muted-foreground hover:border-primary/50"
                  }`}
                >
                  {selected && <Check size={10} />}
                  {model}
                </button>
              );
            }),
          )}
        </div>
      </div>

      {/* Results area */}
      <div className="flex-1 overflow-y-auto p-4">
        {!compareResults && !isComparing && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-muted-foreground text-sm">
                Send a prompt to compare responses across models.
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                Results appear side-by-side with cost and latency metrics.
              </p>
            </div>
          </div>
        )}

        {isComparing && (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 size={16} className="animate-spin" />
              Comparing {compareModels.length} models...
            </div>
          </div>
        )}

        {compareResults && (
          <div
            className="grid gap-4"
            style={{
              gridTemplateColumns: `repeat(${compareResults.length}, minmax(0, 1fr))`,
            }}
          >
            {compareResults.map((result) => (
              <div
                key={result.model}
                className="bg-card border-[0.5px] border-border rounded-lg overflow-hidden shadow-[0_2px_8px_oklch(0_0_0/0.15)]"
              >
                <div className="bg-secondary px-4 py-3 border-b border-border">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-mono font-medium truncate">
                      {result.model}
                    </span>
                    <Badge variant="outline" className="text-xs ml-2 flex-none">
                      {result.provider}
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

      {/* Composer */}
      <div className="border-t border-border p-3">
        <div className="flex items-end gap-2 bg-card border-[0.5px] border-border rounded-lg p-2 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
          <textarea
            ref={textareaRef}
            className="flex-1 bg-transparent resize-none text-[13px] placeholder:text-muted-foreground/60 focus:outline-none min-h-[36px] max-h-[120px] py-1.5 px-2 leading-relaxed"
            placeholder="Type a prompt to compare..."
            rows={1}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleCompare();
              }
            }}
            disabled={isComparing}
          />
          <Button
            size="icon-sm"
            onClick={handleCompare}
            disabled={isComparing || !input.trim() || compareModels.length < 2}
            className="flex-none rounded-md"
          >
            {isComparing ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </Button>
        </div>
        {compareModels.length < 2 && (
          <p className="text-xs text-destructive mt-1.5 px-1">
            Select at least 2 models to compare.
          </p>
        )}
      </div>
    </div>
  );
}
