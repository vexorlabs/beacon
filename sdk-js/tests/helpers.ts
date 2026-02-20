/**
 * Test helpers for the Beacon JS SDK.
 */

import type { SpanExporter } from "../src/exporter.js";
import type { Span } from "../src/models.js";

export class InMemoryExporter implements SpanExporter {
  spans: Span[] = [];

  export(spans: Span[]): void {
    this.spans.push(...spans);
  }

  clear(): void {
    this.spans = [];
  }
}
