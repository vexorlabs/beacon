import type { Span } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import ReplayPanel from "./ReplayPanel";

interface LlmCallDetailProps {
  span: Span;
}

function attr(span: Span, key: string): unknown {
  return span.attributes[key];
}

function parseJson(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function formatCost(value: unknown): string {
  if (typeof value !== "number") return "—";
  return `$${value.toFixed(4)}`;
}

function formatNumber(value: unknown): string {
  if (typeof value !== "number") return "—";
  return value.toLocaleString();
}

export default function LlmCallDetail({ span }: LlmCallDetailProps) {
  const provider = attr(span, "llm.provider");
  const model = attr(span, "llm.model");
  const promptRaw = attr(span, "llm.prompt");
  const completion = attr(span, "llm.completion");
  const tokensIn = attr(span, "llm.tokens.input");
  const tokensOut = attr(span, "llm.tokens.output");
  const tokensTotal = attr(span, "llm.tokens.total");
  const costUsd = attr(span, "llm.cost_usd");
  const temperature = attr(span, "llm.temperature");
  const maxTokens = attr(span, "llm.max_tokens");
  const finishReason = attr(span, "llm.finish_reason");

  const messages = parseJson(promptRaw);

  return (
    <div className="space-y-4">
      {/* Model & Provider */}
      <div className="flex items-center gap-2 flex-wrap">
        {typeof provider === "string" && (
          <Badge variant="outline">{provider}</Badge>
        )}
        {typeof model === "string" && <Badge variant="secondary">{model}</Badge>}
      </div>

      {/* Token Stats */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-muted rounded p-2">
          <div className="text-muted-foreground">Input tokens</div>
          <div className="font-medium">{formatNumber(tokensIn)}</div>
        </div>
        <div className="bg-muted rounded p-2">
          <div className="text-muted-foreground">Output tokens</div>
          <div className="font-medium">{formatNumber(tokensOut)}</div>
        </div>
        <div className="bg-muted rounded p-2">
          <div className="text-muted-foreground">Cost</div>
          <div className="font-medium">{formatCost(costUsd)}</div>
        </div>
      </div>

      {/* Prompt */}
      <div>
        <h4 className="text-xs font-semibold mb-1">Prompt</h4>
        {Array.isArray(messages) ? (
          <div className="space-y-2 max-h-[300px] overflow-auto">
            {messages.map((msg: Record<string, unknown>, i: number) => (
              <div key={i} className="bg-muted rounded p-2 text-xs">
                <span className="font-semibold text-muted-foreground">
                  {typeof msg.role === "string" ? msg.role : "unknown"}
                </span>
                <pre className="whitespace-pre-wrap mt-1">
                  {typeof msg.content === "string"
                    ? msg.content
                    : JSON.stringify(msg.content, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        ) : (
          <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap max-h-[300px] overflow-auto">
            {typeof promptRaw === "string"
              ? promptRaw
              : JSON.stringify(promptRaw, null, 2)}
          </pre>
        )}
      </div>

      {/* Completion */}
      <div>
        <h4 className="text-xs font-semibold mb-1">Completion</h4>
        <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap max-h-[300px] overflow-auto">
          {typeof completion === "string"
            ? completion
            : JSON.stringify(completion, null, 2)}
        </pre>
      </div>

      {/* Tool Calls */}
      {(() => {
        const toolCallsRaw = parseJson(attr(span, "llm.tool_calls"));
        if (!Array.isArray(toolCallsRaw) || toolCallsRaw.length === 0)
          return null;
        return (
          <div>
            <h4 className="text-xs font-semibold mb-1">Tool Calls</h4>
            <div className="space-y-2">
              {toolCallsRaw.map(
                (tc: Record<string, unknown>, i: number) => {
                  const name =
                    typeof tc.function === "object" &&
                    tc.function !== null &&
                    "name" in tc.function
                      ? String(
                          (tc.function as Record<string, unknown>).name,
                        )
                      : typeof tc.name === "string"
                        ? tc.name
                        : "unknown";
                  const args =
                    typeof tc.function === "object" &&
                    tc.function !== null &&
                    "arguments" in tc.function
                      ? (tc.function as Record<string, unknown>).arguments
                      : tc.input;
                  const formattedArgs =
                    typeof args === "string"
                      ? (() => {
                          try {
                            return JSON.stringify(
                              JSON.parse(args),
                              null,
                              2,
                            );
                          } catch {
                            return args;
                          }
                        })()
                      : JSON.stringify(args, null, 2);
                  return (
                    <details key={i} className="bg-muted rounded p-2">
                      <summary className="text-xs font-medium cursor-pointer">
                        {name}
                      </summary>
                      <pre className="text-xs whitespace-pre-wrap mt-1 max-h-[200px] overflow-auto">
                        {formattedArgs}
                      </pre>
                    </details>
                  );
                },
              )}
            </div>
          </div>
        );
      })()}

      {/* Parameters */}
      {(temperature !== undefined ||
        maxTokens !== undefined ||
        finishReason !== undefined ||
        tokensTotal !== undefined) && (
        <div>
          <h4 className="text-xs font-semibold mb-1">Parameters</h4>
          <div className="text-xs text-muted-foreground space-y-0.5">
            {temperature !== undefined && (
              <div>Temperature: {String(temperature)}</div>
            )}
            {maxTokens !== undefined && (
              <div>Max tokens: {String(maxTokens)}</div>
            )}
            {finishReason !== undefined && (
              <div>Finish reason: {String(finishReason)}</div>
            )}
            {tokensTotal !== undefined && (
              <div>Total tokens: {formatNumber(tokensTotal)}</div>
            )}
          </div>
        </div>
      )}

      <Separator />
      <ReplayPanel key={span.span_id} span={span} />
    </div>
  );
}
