/**
 * Trace context propagation using AsyncLocalStorage.
 *
 * Mirrors Python SDK's beacon_sdk/context.py but uses Node.js
 * AsyncLocalStorage instead of ContextVar for automatic async
 * context propagation.
 */

import { AsyncLocalStorage } from "node:async_hooks";
import type { Span } from "./models.js";

export interface TraceContext {
  traceId: string;
  spanId: string;
}

const asyncLocalStorage = new AsyncLocalStorage<TraceContext>();
const activeSpans = new Map<string, Span>();

export function getContext(): TraceContext | undefined {
  return asyncLocalStorage.getStore();
}

export function runWithContext<T>(ctx: TraceContext, fn: () => T): T {
  return asyncLocalStorage.run(ctx, fn);
}

export function registerSpan(span: Span): void {
  activeSpans.set(span.span_id, span);
}

export function unregisterSpan(spanId: string): void {
  activeSpans.delete(spanId);
}

export function getActiveSpan(spanId: string): Span | undefined {
  return activeSpans.get(spanId);
}

export function getCurrentSpan(): Span | undefined {
  const ctx = getContext();
  if (!ctx) return undefined;
  return activeSpans.get(ctx.spanId);
}
