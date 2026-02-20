import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { BeaconTracer } from "../../src/tracer.js";
import { SpanType, SpanStatus } from "../../src/models.js";
import { estimateCost } from "../../src/pricing.js";
import { InMemoryExporter } from "../helpers.js";
import {
  _applyResponseAttributes,
  type AnthropicMessage,
} from "../../src/integrations/anthropic.js";

/**
 * We test the core logic (applyResponseAttributes, span creation) directly
 * rather than calling patch() which requires the real @anthropic-ai/sdk.
 */

describe("Anthropic integration", () => {
  let exporter: InMemoryExporter;
  let tracer: BeaconTracer;

  beforeEach(() => {
    exporter = new InMemoryExporter();
    tracer = new BeaconTracer({ exporter, enabled: true });
  });

  afterEach(() => {
    exporter.clear();
  });

  describe("applyResponseAttributes (non-streaming)", () => {
    it("extracts text completion, tokens, and cost", () => {
      const span = tracer.startSpan("anthropic.messages.create", {
        spanType: SpanType.LLM_CALL,
      });

      const response: AnthropicMessage = {
        content: [{ type: "text", text: "Hello from Claude!" }],
        usage: { input_tokens: 15, output_tokens: 8 },
        model: "claude-sonnet-4-20250514",
        stop_reason: "end_turn",
      };

      _applyResponseAttributes(span, response, "claude-sonnet-4-20250514");
      tracer.endSpan(span, SpanStatus.OK);

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.attributes["llm.completion"]).toBe("Hello from Claude!");
      expect(s.attributes["llm.finish_reason"]).toBe("end_turn");
      expect(s.attributes["llm.tokens.input"]).toBe(15);
      expect(s.attributes["llm.tokens.output"]).toBe(8);
      expect(s.attributes["llm.tokens.total"]).toBe(23);
      expect(s.attributes["llm.model"]).toBe("claude-sonnet-4-20250514");
      expect(s.attributes["llm.cost_usd"]).toBe(
        estimateCost("claude-sonnet-4-20250514", 15, 8),
      );
    });

    it("extracts tool_use blocks into llm.tool_calls", () => {
      const span = tracer.startSpan("anthropic.messages.create", {
        spanType: SpanType.LLM_CALL,
      });

      const response: AnthropicMessage = {
        content: [
          {
            type: "tool_use",
            id: "call_001",
            name: "get_weather",
            input: { city: "London" },
          },
          {
            type: "text",
            text: "Let me check the weather.",
          },
        ],
        usage: { input_tokens: 20, output_tokens: 15 },
        model: "claude-sonnet-4-20250514",
        stop_reason: "tool_use",
      };

      _applyResponseAttributes(span, response, "claude-sonnet-4-20250514");
      tracer.endSpan(span, SpanStatus.OK);

      const s = exporter.spans[0]!;
      expect(s.attributes["llm.finish_reason"]).toBe("tool_use");

      const toolCalls = JSON.parse(s.attributes["llm.tool_calls"] as string);
      expect(toolCalls).toHaveLength(1);
      expect(toolCalls[0]).toEqual({
        id: "call_001",
        name: "get_weather",
        input: { city: "London" },
      });

      // Completion is first text block
      expect(s.attributes["llm.completion"]).toBe("Let me check the weather.");
    });

    it("does not set llm.tool_calls when there are no tool_use blocks", () => {
      const span = tracer.startSpan("anthropic.messages.create", {
        spanType: SpanType.LLM_CALL,
      });

      const response: AnthropicMessage = {
        content: [{ type: "text", text: "Just text." }],
        usage: { input_tokens: 5, output_tokens: 3 },
        model: "claude-sonnet-4-20250514",
        stop_reason: "end_turn",
      };

      _applyResponseAttributes(span, response, "claude-sonnet-4-20250514");
      tracer.endSpan(span, SpanStatus.OK);

      const s = exporter.spans[0]!;
      expect(s.attributes["llm.tool_calls"]).toBeUndefined();
    });

    it("handles empty content array", () => {
      const span = tracer.startSpan("anthropic.messages.create", {
        spanType: SpanType.LLM_CALL,
      });

      const response: AnthropicMessage = {
        content: [],
        usage: { input_tokens: 5, output_tokens: 0 },
        model: "claude-sonnet-4-20250514",
        stop_reason: null,
      };

      _applyResponseAttributes(span, response, "claude-sonnet-4-20250514");
      tracer.endSpan(span, SpanStatus.OK);

      const s = exporter.spans[0]!;
      expect(s.attributes["llm.completion"]).toBe("");
    });
  });

  describe("span creation via withSpan", () => {
    it("creates LLM span with Anthropic attributes", () => {
      tracer.withSpan(
        "anthropic.messages.create",
        { spanType: SpanType.LLM_CALL },
        (span) => {
          span.setAttribute("llm.provider", "anthropic");
          span.setAttribute("llm.model", "claude-sonnet-4-20250514");
          span.setAttribute(
            "llm.prompt",
            JSON.stringify([
              { role: "system", content: "You are helpful." },
              { role: "user", content: "Hi" },
            ]),
          );
          span.setAttribute("llm.completion", "Hello!");
          span.setAttribute("llm.tokens.input", 10);
          span.setAttribute("llm.tokens.output", 5);
          span.setAttribute("llm.tokens.total", 15);
        },
      );

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.span_type).toBe("llm_call");
      expect(s.status).toBe("ok");
      expect(s.name).toBe("anthropic.messages.create");
      expect(s.attributes["llm.provider"]).toBe("anthropic");

      // Verify prompt includes system message
      const prompt = JSON.parse(s.attributes["llm.prompt"] as string);
      expect(prompt[0]).toEqual({ role: "system", content: "You are helpful." });
    });

    it("captures errors with error status", () => {
      expect(() =>
        tracer.withSpan(
          "anthropic.messages.create",
          { spanType: SpanType.LLM_CALL },
          () => {
            throw new Error("Anthropic API rate limit exceeded");
          },
        ),
      ).toThrow("Anthropic API rate limit exceeded");

      const s = exporter.spans[0]!;
      expect(s.status).toBe("error");
      expect(s.error_message).toBe("Anthropic API rate limit exceeded");
    });
  });

  describe("streaming simulation", () => {
    it("accumulates text deltas and finalizes span", () => {
      const span = tracer.startSpan("anthropic.messages.create", {
        spanType: SpanType.LLM_CALL,
        attributes: {
          "llm.provider": "anthropic",
          "llm.model": "claude-sonnet-4-20250514",
        },
      });

      // Simulate stream event processing
      const chunks = ["Hello", ", ", "world!"];
      span.setAttribute("llm.completion", chunks.join(""));
      span.setAttribute("llm.tokens.input", 25);
      span.setAttribute("llm.tokens.output", 8);
      span.setAttribute("llm.tokens.total", 33);
      span.setAttribute("llm.finish_reason", "end_turn");
      span.setAttribute(
        "llm.cost_usd",
        estimateCost("claude-sonnet-4-20250514", 25, 8),
      );

      tracer.endSpan(span, SpanStatus.OK);

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.attributes["llm.completion"]).toBe("Hello, world!");
      expect(s.attributes["llm.tokens.input"]).toBe(25);
      expect(s.attributes["llm.tokens.output"]).toBe(8);
      expect(s.attributes["llm.tokens.total"]).toBe(33);
      expect(s.attributes["llm.finish_reason"]).toBe("end_turn");
      expect(s.attributes["llm.cost_usd"]).toBeGreaterThan(0);
    });
  });
});
