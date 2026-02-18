import type { Span } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

interface ToolUseDetailProps {
  span: Span;
}

function formatJson(value: unknown): string {
  if (typeof value === "string") {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  if (value === undefined || value === null) return "—";
  return JSON.stringify(value, null, 2);
}

export default function ToolUseDetail({ span }: ToolUseDetailProps) {
  const toolName = span.attributes["tool.name"];
  const framework = span.attributes["tool.framework"];
  const input = span.attributes["tool.input"];
  const output = span.attributes["tool.output"];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        {typeof toolName === "string" && (
          <span className="text-sm font-medium">{toolName}</span>
        )}
        {typeof framework === "string" && (
          <Badge variant="outline">{framework}</Badge>
        )}
      </div>

      {/* Input */}
      <div>
        <h4 className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
          Input
        </h4>
        <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap max-h-[300px] overflow-auto border-[0.5px] border-border">
          {formatJson(input)}
        </pre>
      </div>

      {/* Output */}
      <div>
        <h4 className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
          Output
        </h4>
        <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap max-h-[300px] overflow-auto border-[0.5px] border-border">
          {formatJson(output)}
        </pre>
      </div>
    </div>
  );
}
