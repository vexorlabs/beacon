/**
 * observe() higher-order function for wrapping functions in spans.
 *
 * Mirrors Python SDK's @observe decorator but adapted for JavaScript
 * where decorators aren't stable yet.
 *
 * Usage:
 *   const myFn = observe({ name: "my-fn", spanType: "agent_step" }, async () => {
 *     // traced code
 *   });
 *
 *   // Or with just a function (uses function name):
 *   const traced = observe(myNamedFunction);
 */

import type { BeaconTracer } from "./tracer.js";
import { SpanType, type SpanType as SpanTypeT } from "./models.js";

// Module-level reference set by index.ts init()
let _getTracerFn: (() => BeaconTracer | null) | null = null;

/** @internal Called by init() to wire up the tracer reference. */
export function _setTracerGetter(fn: () => BeaconTracer | null): void {
  _getTracerFn = fn;
}

interface ObserveOptions {
  name?: string;
  spanType?: SpanTypeT;
}

// Overload: observe(fn) — wraps a function using its name
export function observe<TArgs extends unknown[], TReturn>(
  fn: (...args: TArgs) => TReturn
): (...args: TArgs) => TReturn;

// Overload: observe(options, fn) — wraps with explicit options
export function observe<TArgs extends unknown[], TReturn>(
  options: ObserveOptions,
  fn: (...args: TArgs) => TReturn
): (...args: TArgs) => TReturn;

export function observe<TArgs extends unknown[], TReturn>(
  fnOrOptions: ((...args: TArgs) => TReturn) | ObserveOptions,
  maybeFn?: (...args: TArgs) => TReturn
): (...args: TArgs) => TReturn {
  let fn: (...args: TArgs) => TReturn;
  let options: ObserveOptions;

  if (typeof fnOrOptions === "function") {
    fn = fnOrOptions;
    options = {};
  } else {
    if (!maybeFn) {
      throw new Error("observe(options, fn): fn is required");
    }
    options = fnOrOptions;
    fn = maybeFn;
  }

  const spanName = options.name ?? (fn.name || "anonymous");
  const spanType = options.spanType ?? SpanType.CUSTOM;

  const wrapped = (...args: TArgs): TReturn => {
    const tracer = _getTracerFn?.();
    if (!tracer) {
      return fn(...args);
    }
    return tracer.withSpan(spanName, { spanType }, () => fn(...args));
  };

  // Preserve function name for debugging
  Object.defineProperty(wrapped, "name", { value: fn.name || spanName });
  return wrapped;
}
