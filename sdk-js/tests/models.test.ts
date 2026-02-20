import { describe, it, expect, beforeEach } from "vitest";
import { Span, SpanType, SpanStatus } from "../src/models.js";

describe("SpanType", () => {
  it("has correct enum values", () => {
    expect(SpanType.LLM_CALL).toBe("llm_call");
    expect(SpanType.TOOL_USE).toBe("tool_use");
    expect(SpanType.AGENT_STEP).toBe("agent_step");
    expect(SpanType.CUSTOM).toBe("custom");
  });
});

describe("SpanStatus", () => {
  it("has correct enum values", () => {
    expect(SpanStatus.OK).toBe("ok");
    expect(SpanStatus.ERROR).toBe("error");
    expect(SpanStatus.UNSET).toBe("unset");
  });
});

describe("Span", () => {
  let span: Span;

  beforeEach(() => {
    span = new Span({
      trace_id: "trace-123",
      name: "test-span",
    });
  });

  it("generates a UUID span_id by default", () => {
    expect(span.span_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
    );
  });

  it("defaults to CUSTOM span_type", () => {
    expect(span.span_type).toBe(SpanType.CUSTOM);
  });

  it("defaults to UNSET status", () => {
    expect(span.status).toBe(SpanStatus.UNSET);
  });

  it("stores start_time as epoch seconds", () => {
    const now = Date.now() / 1000;
    expect(span.start_time).toBeCloseTo(now, 0);
  });

  it("has null end_time before end() is called", () => {
    expect(span.end_time).toBeNull();
  });

  it("accepts custom span_type", () => {
    const llmSpan = new Span({
      trace_id: "t1",
      name: "llm",
      span_type: SpanType.LLM_CALL,
    });
    expect(llmSpan.span_type).toBe("llm_call");
  });

  it("accepts parent_span_id", () => {
    const child = new Span({
      trace_id: "t1",
      name: "child",
      parent_span_id: "parent-123",
    });
    expect(child.parent_span_id).toBe("parent-123");
  });

  describe("setAttribute", () => {
    it("sets simple attributes", () => {
      span.setAttribute("llm.model", "gpt-4o");
      expect(span.attributes["llm.model"]).toBe("gpt-4o");
    });

    it("truncates long string values for known keys", () => {
      const longPrompt = "x".repeat(60_000);
      span.setAttribute("llm.prompt", longPrompt);
      const val = span.attributes["llm.prompt"] as string;
      expect(val.length).toBe(50_000 + "[TRUNCATED]".length);
      expect(val.endsWith("[TRUNCATED]")).toBe(true);
    });

    it("does not truncate short values", () => {
      span.setAttribute("llm.prompt", "short");
      expect(span.attributes["llm.prompt"]).toBe("short");
    });

    it("does not truncate unknown keys", () => {
      const longValue = "x".repeat(100_000);
      span.setAttribute("custom.key", longValue);
      expect((span.attributes["custom.key"] as string).length).toBe(100_000);
    });

    it("drops oversized screenshots", () => {
      const bigScreenshot = "x".repeat(600_000);
      span.setAttribute("browser.screenshot", bigScreenshot);
      expect(span.attributes["browser.screenshot"]).toBeUndefined();
    });

    it("keeps small screenshots", () => {
      span.setAttribute("browser.screenshot", "small");
      expect(span.attributes["browser.screenshot"]).toBe("small");
    });
  });

  describe("end", () => {
    it("sets end_time and status to OK by default", () => {
      span.end();
      expect(span.end_time).toBeGreaterThan(0);
      expect(span.status).toBe(SpanStatus.OK);
    });

    it("sets error status and message", () => {
      span.end(SpanStatus.ERROR, "something broke");
      expect(span.status).toBe(SpanStatus.ERROR);
      expect(span.error_message).toBe("something broke");
    });
  });

  describe("toDict", () => {
    it("returns SpanData shape matching backend schema", () => {
      span.setAttribute("llm.model", "gpt-4o");
      span.end();

      const data = span.toDict();
      expect(data.span_id).toBe(span.span_id);
      expect(data.trace_id).toBe("trace-123");
      expect(data.parent_span_id).toBeNull();
      expect(data.span_type).toBe("custom");
      expect(data.name).toBe("test-span");
      expect(data.status).toBe("ok");
      expect(data.error_message).toBeNull();
      expect(data.start_time).toBeGreaterThan(0);
      expect(data.end_time).toBeGreaterThan(0);
      expect(data.attributes).toEqual({ "llm.model": "gpt-4o" });
      expect(data.sdk_language).toBe("javascript");
    });

    it("always sets sdk_language to javascript", () => {
      expect(span.toDict().sdk_language).toBe("javascript");
    });
  });
});
