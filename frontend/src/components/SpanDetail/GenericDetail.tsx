import type { Span } from "@/lib/types";

interface GenericDetailProps {
  span: Span;
}

const PREFIXES = ["file.", "shell.", "agent.", "chain."] as const;

function groupAttributes(
  attributes: Record<string, unknown>,
): { label: string; entries: [string, unknown][] }[] {
  const groups: Map<string, [string, unknown][]> = new Map();
  const ungrouped: [string, unknown][] = [];

  for (const [key, value] of Object.entries(attributes)) {
    const prefix = PREFIXES.find((p) => key.startsWith(p));
    if (prefix) {
      const label = prefix.slice(0, -1); // remove trailing dot
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label)!.push([key, value]);
    } else {
      ungrouped.push([key, value]);
    }
  }

  const result: { label: string; entries: [string, unknown][] }[] = [];
  for (const [label, entries] of groups) {
    result.push({ label, entries });
  }
  if (ungrouped.length > 0) {
    result.push({ label: "attributes", entries: ungrouped });
  }
  return result;
}

function formatValue(value: unknown): string {
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

export default function GenericDetail({ span }: GenericDetailProps) {
  const groups = groupAttributes(span.attributes);

  if (groups.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">No attributes</div>
    );
  }

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <div key={group.label}>
          <h4 className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-2 capitalize">
            {group.label}
          </h4>
          <div className="space-y-1">
            {group.entries.map(([key, value]) => (
              <div key={key}>
                <div className="text-xs text-muted-foreground">{key}</div>
                <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap max-h-[200px] overflow-auto border-[0.5px] border-border">
                  {formatValue(value)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
