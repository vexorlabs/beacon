import { describe, it, expect, afterEach } from "vitest";
import {
  getContext,
  runWithContext,
  registerSpan,
  unregisterSpan,
  getActiveSpan,
  getCurrentSpan,
} from "../src/context.js";
import { Span } from "../src/models.js";

describe("context", () => {
  it("returns undefined when no context is set", () => {
    expect(getContext()).toBeUndefined();
  });

  it("provides context within runWithContext", () => {
    const ctx = { traceId: "t1", spanId: "s1" };
    runWithContext(ctx, () => {
      expect(getContext()).toEqual(ctx);
    });
  });

  it("restores undefined after runWithContext exits", () => {
    runWithContext({ traceId: "t1", spanId: "s1" }, () => {});
    expect(getContext()).toBeUndefined();
  });

  it("supports nested contexts", () => {
    const outer = { traceId: "t1", spanId: "s1" };
    const inner = { traceId: "t1", spanId: "s2" };

    runWithContext(outer, () => {
      expect(getContext()?.spanId).toBe("s1");
      runWithContext(inner, () => {
        expect(getContext()?.spanId).toBe("s2");
      });
      expect(getContext()?.spanId).toBe("s1");
    });
  });

  it("isolates async chains", async () => {
    const results: string[] = [];

    const task1 = new Promise<void>((resolve) => {
      runWithContext({ traceId: "t1", spanId: "task1" }, () => {
        setTimeout(() => {
          results.push(getContext()?.spanId ?? "none");
          resolve();
        }, 10);
      });
    });

    const task2 = new Promise<void>((resolve) => {
      runWithContext({ traceId: "t2", spanId: "task2" }, () => {
        setTimeout(() => {
          results.push(getContext()?.spanId ?? "none");
          resolve();
        }, 5);
      });
    });

    await Promise.all([task1, task2]);
    expect(results).toContain("task1");
    expect(results).toContain("task2");
  });
});

describe("span registry", () => {
  afterEach(() => {
    // Clean up
    unregisterSpan("test-span-id");
  });

  it("registers and retrieves spans", () => {
    const span = new Span({ trace_id: "t1", name: "test", span_id: "test-span-id" });
    registerSpan(span);
    expect(getActiveSpan("test-span-id")).toBe(span);
  });

  it("unregisters spans", () => {
    const span = new Span({ trace_id: "t1", name: "test", span_id: "test-span-id" });
    registerSpan(span);
    unregisterSpan("test-span-id");
    expect(getActiveSpan("test-span-id")).toBeUndefined();
  });

  it("getCurrentSpan returns active span from context", () => {
    const span = new Span({ trace_id: "t1", name: "test", span_id: "s1" });
    registerSpan(span);
    runWithContext({ traceId: "t1", spanId: "s1" }, () => {
      expect(getCurrentSpan()).toBe(span);
    });
    unregisterSpan("s1");
  });

  it("getCurrentSpan returns undefined without context", () => {
    expect(getCurrentSpan()).toBeUndefined();
  });
});
