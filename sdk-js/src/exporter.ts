/**
 * Span exporters for sending trace data to the Beacon backend.
 *
 * Mirrors Python SDK's beacon_sdk/exporters.py.
 *
 * - HttpSpanExporter: fire-and-forget sync exporter
 * - BatchExporter: batches spans and flushes periodically (default)
 */

import type { Span } from "./models.js";

export interface SpanExporter {
  export(spans: Span[]): void;
}

export interface FlushableExporter extends SpanExporter {
  flush(): Promise<void>;
  shutdown(): Promise<void>;
}

const HTTP_TIMEOUT_MS = 5_000;
const DEFAULT_BATCH_SIZE = 50;
const DEFAULT_FLUSH_INTERVAL_MS = 1_000;

export class HttpSpanExporter implements SpanExporter {
  private readonly endpoint: string;

  constructor(backendUrl: string) {
    this.endpoint = `${backendUrl.replace(/\/+$/, "")}/v1/spans`;
  }

  export(spans: Span[]): void {
    const payload = { spans: spans.map((s) => s.toDict()) };
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);

    fetch(this.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
      .catch(() => {
        // Silent failure, matching Python SDK behavior
      })
      .finally(() => clearTimeout(timeoutId));
  }
}

export class BatchExporter implements FlushableExporter {
  private readonly endpoint: string;
  private readonly batchSize: number;
  private readonly flushIntervalMs: number;
  private queue: Span[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private shuttingDown = false;

  constructor(options: {
    backendUrl: string;
    batchSize?: number;
    flushIntervalMs?: number;
  }) {
    this.endpoint = `${options.backendUrl.replace(/\/+$/, "")}/v1/spans`;
    this.batchSize = options.batchSize ?? DEFAULT_BATCH_SIZE;
    this.flushIntervalMs = options.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS;
    this.startTimer();
  }

  export(spans: Span[]): void {
    if (this.shuttingDown) return;
    this.queue.push(...spans);
    if (this.queue.length >= this.batchSize) {
      void this.drainAndSend();
    }
  }

  async flush(): Promise<void> {
    await this.drainAndSend();
  }

  async shutdown(): Promise<void> {
    this.shuttingDown = true;
    this.stopTimer();
    await this.drainAndSend();
  }

  private startTimer(): void {
    this.timer = setInterval(() => {
      void this.drainAndSend();
    }, this.flushIntervalMs);
    // Unref so the timer doesn't keep the process alive
    if (this.timer && typeof this.timer === "object" && "unref" in this.timer) {
      (this.timer as NodeJS.Timeout).unref();
    }
  }

  private stopTimer(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  private async drainAndSend(): Promise<void> {
    if (this.queue.length === 0) return;
    const batch = this.queue.splice(0);
    await this.sendBatch(batch);
  }

  private async sendBatch(batch: Span[]): Promise<void> {
    const payload = { spans: batch.map((s) => s.toDict()) };
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);

    try {
      await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } catch {
      // Silent failure
    } finally {
      clearTimeout(timeoutId);
    }
  }
}
