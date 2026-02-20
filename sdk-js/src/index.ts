/**
 * Beacon JS/TS SDK — public API.
 *
 * Mirrors Python SDK's beacon_sdk/__init__.py.
 *
 * Usage:
 *   import { init, observe } from "beacon-sdk";
 *   init();
 *   const myFn = observe(async () => { ... });
 */

import { BatchExporter, HttpSpanExporter, type FlushableExporter } from "./exporter.js";
import { BeaconTracer } from "./tracer.js";
import { _setTracerGetter } from "./decorators.js";

export { Span, SpanType, SpanStatus, type SpanData } from "./models.js";
export { BeaconTracer } from "./tracer.js";
export { observe } from "./decorators.js";
export { getCurrentSpan } from "./context.js";
export { estimateCost } from "./pricing.js";

const DEFAULT_BACKEND_URL = "http://localhost:7474";

let _tracer: BeaconTracer | null = null;
let _exporter: FlushableExporter | null = null;

export interface InitOptions {
  backendUrl?: string;
  autoPatch?: boolean;
  enabled?: boolean;
  exporter?: "sync" | "batch";
}

export function init(options?: InitOptions): void {
  const enabled =
    options?.enabled ?? process.env["BEACON_ENABLED"] !== "false";

  if (!enabled) {
    _tracer = new BeaconTracer({ exporter: null, enabled: false });
    _setTracerGetter(() => _tracer);
    return;
  }

  const backendUrl =
    options?.backendUrl ??
    process.env["BEACON_BACKEND_URL"] ??
    DEFAULT_BACKEND_URL;

  const exporterMode = options?.exporter ?? "batch";

  if (exporterMode === "sync") {
    const exp = new HttpSpanExporter(backendUrl);
    _tracer = new BeaconTracer({ exporter: exp, enabled: true });
  } else {
    const exp = new BatchExporter({ backendUrl });
    _exporter = exp;
    _tracer = new BeaconTracer({ exporter: exp, enabled: true });
  }

  _setTracerGetter(() => _tracer);

  const autoPatch =
    options?.autoPatch ?? process.env["BEACON_AUTO_PATCH"] !== "false";

  if (autoPatch) {
    applyAutoPatches();
  }
}

export function getTracer(): BeaconTracer | null {
  return _tracer;
}

/**
 * @internal Used by integrations to get the tracer instance.
 */
export function _getTracer(): BeaconTracer | null {
  return _tracer;
}

export async function flush(): Promise<void> {
  if (_exporter) {
    await _exporter.flush();
  }
}

export async function shutdown(): Promise<void> {
  if (_exporter) {
    await _exporter.shutdown();
    _exporter = null;
  }
}

function applyAutoPatches(): void {
  // Try each integration, silently skip if peer dep isn't installed.
  // Dynamic imports ensure no hard dependency on any provider SDK.
  const patches: Array<() => Promise<void>> = [
    () =>
      import("./integrations/openai.js").then(
        (m) => m.patch(),
        () => {}
      ),
    () =>
      import("./integrations/anthropic.js").then(
        (m) => m.patch(),
        () => {}
      ),
    () =>
      import("./integrations/vercel-ai.js").then(
        (m) => m.patch(),
        () => {}
      ),
  ];
  for (const tryPatch of patches) {
    tryPatch().catch(() => {});
  }
}
