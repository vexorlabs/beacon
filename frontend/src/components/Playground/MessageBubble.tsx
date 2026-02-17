import { User, Bot } from "lucide-react";
import type { PlaygroundChatMetrics } from "@/lib/types";

interface Props {
  role: string;
  content: string;
  metrics?: PlaygroundChatMetrics;
}

function formatCost(usd: number): string {
  if (usd < 0.001) return `$${usd.toFixed(5)}`;
  return `$${usd.toFixed(4)}`;
}

export default function MessageBubble({ role, content, metrics }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="flex-none w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
          <Bot size={14} className="text-primary" />
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-secondary"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{content}</p>
        {metrics && (
          <div className="flex items-center gap-3 mt-2 pt-2 border-t border-border/30 text-xs text-muted-foreground">
            <span>{metrics.input_tokens + metrics.output_tokens} tok</span>
            <span>{formatCost(metrics.cost_usd)}</span>
            <span>{(metrics.latency_ms / 1000).toFixed(1)}s</span>
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex-none w-7 h-7 rounded-full bg-primary flex items-center justify-center mt-0.5">
          <User size={14} className="text-primary-foreground" />
        </div>
      )}
    </div>
  );
}
