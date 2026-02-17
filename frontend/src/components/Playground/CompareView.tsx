import { useState } from "react";
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
  const compareModels = usePlaygroundStore((s) => s.compareModels);
  const toggleCompareModel = usePlaygroundStore((s) => s.toggleCompareModel);
  const compareResults = usePlaygroundStore((s) => s.compareResults);
  const isComparing = usePlaygroundStore((s) => s.isComparing);
  const runComparison = usePlaygroundStore((s) => s.runComparison);

  const handleCompare = () => {
    const trimmed = input.trim();
    if (!trimmed || isComparing || compareModels.length < 2) return;
    runComparison(trimmed);
  };

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
                className="border border-border rounded-lg overflow-hidden"
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
                  <p className="text-sm whitespace-pre-wrap">
                    {result.completion}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 bg-background border border-input rounded-md px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Type a prompt to compare..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && !e.shiftKey && handleCompare()
            }
            disabled={isComparing}
          />
          <Button
            onClick={handleCompare}
            disabled={isComparing || !input.trim() || compareModels.length < 2}
          >
            {isComparing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </Button>
        </div>
        {compareModels.length < 2 && (
          <p className="text-xs text-destructive mt-1">
            Select at least 2 models to compare.
          </p>
        )}
      </div>
    </div>
  );
}
