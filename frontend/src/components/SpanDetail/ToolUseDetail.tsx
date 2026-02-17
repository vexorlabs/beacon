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
        <h4 className="text-xs font-semibold mb-1">Input</h4>
        <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap max-h-[300px] overflow-auto">
          {formatJson(input)}
        </pre>
      </div>

      {/* Output */}
      <div>
        <h4 className="text-xs font-semibold mb-1">Output</h4>
        <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap max-h-[300px] overflow-auto">
          {formatJson(output)}
        </pre>
      </div>
    </div>
  );
}
