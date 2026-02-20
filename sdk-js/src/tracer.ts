/**
 * BeaconTracer — core tracing engine.
 *
 * Mirrors Python SDK's beacon_sdk/tracer.py but uses AsyncLocalStorage
 * for context propagation instead of ContextVar tokens.
 */

import { randomUUID } from "node:crypto";
import {
  getContext,
  runWithContext,
  registerSpan,
  unregisterSpan,
  type TraceContext,
} from "./context.js";
import type { SpanExporter } from "./exporter.js";
import { Span, SpanStatus, type SpanType } from "./models.js";

export class BeaconTracer {
  private readonly exporter: SpanExporter | null;
  private readonly enabled: boolean;

  constructor(options: {
    exporter: SpanExporter | null;
    enabled?: boolean;
  }) {
    this.exporter = options.exporter;
    this.enabled = options.enabled ?? true;
  }

  startSpan(
    name: string,
    options?: {
      spanType?: SpanType;
      attributes?: Record<string, unknown>;
    }
  ): Span {
    const currentCtx = getContext();
    const traceId = currentCtx?.traceId ?? randomUUID();
    const parentSpanId = currentCtx?.spanId ?? null;

    const span = new Span({
      trace_id: traceId,
      parent_span_id: parentSpanId,
      span_type: options?.spanType,
      name,
      attributes: options?.attributes,
    });

    registerSpan(span);
    return span;
  }

  endSpan(
    span: Span,
    status: SpanStatus = SpanStatus.OK,
    errorMessage?: string
  ): void {
    try {
      span.end(status, errorMessage);
    } finally {
      unregisterSpan(span.span_id);
    }

    if (this.enabled && this.exporter) {
      try {
        this.exporter.export([span]);
      } catch {
        // Silent failure, matching Python SDK behavior
      }
    }
  }

  /**
   * Run a function within a span context.
   * Handles both sync and async functions with automatic context propagation.
   */
  withSpan<T>(
    name: string,
    options: {
      spanType?: SpanType;
      attributes?: Record<string, unknown>;
    },
    fn: (span: Span) => T
  ): T {
    const span = this.startSpan(name, options);
    const ctx: TraceContext = { traceId: span.trace_id, spanId: span.span_id };

    return runWithContext(ctx, () => {
      try {
        const result = fn(span);
        if (result instanceof Promise) {
          return result
            .then((val: unknown) => {
              this.endSpan(span, SpanStatus.OK);
              return val;
            })
            .catch((err: unknown) => {
              this.endSpan(
                span,
                SpanStatus.ERROR,
                err instanceof Error ? err.message : String(err)
              );
              throw err;
            }) as T;
        }
        this.endSpan(span, SpanStatus.OK);
        return result;
      } catch (err) {
        this.endSpan(
          span,
          SpanStatus.ERROR,
          err instanceof Error ? err.message : String(err)
        );
        throw err;
      }
    });
  }
}
