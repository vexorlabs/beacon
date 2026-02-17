import type { Span } from "@/lib/types";

interface BrowserDetailProps {
  span: Span;
}

export default function BrowserDetail({ span }: BrowserDetailProps) {
  const action = span.attributes["browser.action"];
  const url = span.attributes["browser.url"];
  const selector = span.attributes["browser.selector"];
  const value = span.attributes["browser.value"];
  const pageTitle = span.attributes["browser.page_title"];

  return (
    <div className="space-y-4">
      {/* Action */}
      {typeof action === "string" && (
        <div className="text-sm font-medium">{action}</div>
      )}

      {/* URL */}
      {typeof url === "string" && (
        <div>
          <h4 className="text-xs font-semibold mb-1">URL</h4>
          {url.startsWith("http://") || url.startsWith("https://") ? (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-500 hover:underline break-all"
            >
              {url}
            </a>
          ) : (
            <span className="text-xs text-muted-foreground break-all">
              {url}
            </span>
          )}
        </div>
      )}

      {/* Page Title */}
      {typeof pageTitle === "string" && (
        <div className="text-xs text-muted-foreground">{pageTitle}</div>
      )}

      {/* Selector */}
      {typeof selector === "string" && (
        <div>
          <h4 className="text-xs font-semibold mb-1">Selector</h4>
          <code className="text-xs bg-muted rounded px-1.5 py-0.5">
            {selector}
          </code>
        </div>
      )}

      {/* Value */}
      {typeof value === "string" && (
        <div>
          <h4 className="text-xs font-semibold mb-1">Value</h4>
          <pre className="text-xs bg-muted rounded p-2 whitespace-pre-wrap">
            {value}
          </pre>
        </div>
      )}

      {/* Screenshot placeholder */}
      <div className="text-xs text-muted-foreground italic">
        Screenshot display coming in Phase 4
      </div>
    </div>
  );
}
