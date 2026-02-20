import { describe, it, expect, beforeEach } from "vitest";
import { BeaconTracer } from "../src/tracer.js";
import { SpanType, SpanStatus } from "../src/models.js";
import { getContext, runWithContext } from "../src/context.js";
import { InMemoryExporter } from "./helpers.js";

describe("BeaconTracer", () => {
  let exporter: InMemoryExporter;
  let tracer: BeaconTracer;

  beforeEach(() => {
    exporter = new InMemoryExporter();
    tracer = new BeaconTracer({ exporter, enabled: true });
  });

  describe("startSpan", () => {
    it("creates a span with a new trace_id when no context exists", () => {
      const span = tracer.startSpan("test");
      expect(span.trace_id).toBeTruthy();
      expect(span.parent_span_id).toBeNull();
      expect(span.name).toBe("test");
    });

    it("inherits trace_id and parent from context", () => {
      runWithContext({ traceId: "my-trace", spanId: "parent-span" }, () => {
        const span = tracer.startSpan("child");
        expect(span.trace_id).toBe("my-trace");
        expect(span.parent_span_id).toBe("parent-span");
      });
    });

    it("accepts span type and attributes", () => {
      const span = tracer.startSpan("llm-call", {
        spanType: SpanType.LLM_CALL,
        attributes: { "llm.model": "gpt-4o" },
      });
      expect(span.span_type).toBe("llm_call");
      expect(span.attributes["llm.model"]).toBe("gpt-4o");
    });
  });

  describe("endSpan", () => {
    it("exports the span with OK status", () => {
      const span = tracer.startSpan("test");
      tracer.endSpan(span);
      expect(exporter.spans).toHaveLength(1);
      expect(exporter.spans[0]!.status).toBe("ok");
      expect(exporter.spans[0]!.end_time).not.toBeNull();
    });

    it("exports with ERROR status and message", () => {
      const span = tracer.startSpan("test");
      tracer.endSpan(span, SpanStatus.ERROR, "boom");
      expect(exporter.spans[0]!.status).toBe("error");
      expect(exporter.spans[0]!.error_message).toBe("boom");
    });

    it("does not export when disabled", () => {
      const disabledTracer = new BeaconTracer({
        exporter,
        enabled: false,
      });
      const span = disabledTracer.startSpan("test");
      disabledTracer.endSpan(span);
      expect(exporter.spans).toHaveLength(0);
    });
  });

  describe("withSpan", () => {
    it("wraps sync function and exports span", () => {
      const result = tracer.withSpan("sync-fn", {}, (span) => {
        span.setAttribute("key", "value");
        return 42;
      });
      expect(result).toBe(42);
      expect(exporter.spans).toHaveLength(1);
      expect(exporter.spans[0]!.status).toBe("ok");
    });

    it("wraps async function and exports span", async () => {
      const result = await tracer.withSpan("async-fn", {}, async () => {
        await new Promise((r) => setTimeout(r, 5));
        return "done";
      });
      expect(result).toBe("done");
      expect(exporter.spans).toHaveLength(1);
      expect(exporter.spans[0]!.status).toBe("ok");
    });

    it("sets error status on sync throw", () => {
      expect(() =>
        tracer.withSpan("failing", {}, () => {
          throw new Error("sync error");
        })
      ).toThrow("sync error");
      expect(exporter.spans[0]!.status).toBe("error");
      expect(exporter.spans[0]!.error_message).toBe("sync error");
    });

    it("sets error status on async rejection", async () => {
      await expect(
        tracer.withSpan("failing", {}, async () => {
          throw new Error("async error");
        })
      ).rejects.toThrow("async error");
      expect(exporter.spans[0]!.status).toBe("error");
      expect(exporter.spans[0]!.error_message).toBe("async error");
    });

    it("propagates context to nested spans", () => {
      tracer.withSpan("parent", { spanType: SpanType.AGENT_STEP }, (parent) => {
        tracer.withSpan("child", { spanType: SpanType.LLM_CALL }, (child) => {
          expect(child.parent_span_id).toBe(parent.span_id);
          expect(child.trace_id).toBe(parent.trace_id);
        });
      });
      expect(exporter.spans).toHaveLength(2);
    });

    it("propagates context to nested async spans", async () => {
      await tracer.withSpan(
        "parent",
        { spanType: SpanType.AGENT_STEP },
        async (parent) => {
          await tracer.withSpan(
            "child",
            { spanType: SpanType.LLM_CALL },
            async (child) => {
              expect(child.parent_span_id).toBe(parent.span_id);
              expect(child.trace_id).toBe(parent.trace_id);
            }
          );
        }
      );
      expect(exporter.spans).toHaveLength(2);
    });
  });
});
