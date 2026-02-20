import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { BeaconTracer } from "../../src/tracer.js";
import { SpanType, SpanStatus } from "../../src/models.js";
import { estimateCost } from "../../src/pricing.js";
import { InMemoryExporter } from "../helpers.js";
import {
  _applyResponseAttributes,
  type OpenAIChatCompletion,
} from "../../src/integrations/openai.js";

/**
 * We test the core logic (applyResponseAttributes, stream wrapper) directly
 * rather than calling patch() which requires the real openai package.
 * This mirrors how the Python SDK tests work — mock the SDK structures.
 */

describe("OpenAI integration", () => {
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
    it("extracts completion, tokens, and cost from a standard response", () => {
      const span = tracer.startSpan("openai.chat.completions", {
        spanType: SpanType.LLM_CALL,
      });

      const response: OpenAIChatCompletion = {
        choices: [
          {
            message: { content: "Hello, world!" },
            finish_reason: "stop",
          },
        ],
        usage: {
          prompt_tokens: 10,
          completion_tokens: 5,
          total_tokens: 15,
        },
        model: "gpt-4o",
      };

      _applyResponseAttributes(span, response, "gpt-4o");
      tracer.endSpan(span, SpanStatus.OK);

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.attributes["llm.completion"]).toBe("Hello, world!");
      expect(s.attributes["llm.finish_reason"]).toBe("stop");
      expect(s.attributes["llm.tokens.input"]).toBe(10);
      expect(s.attributes["llm.tokens.output"]).toBe(5);
      expect(s.attributes["llm.tokens.total"]).toBe(15);
      expect(s.attributes["llm.model"]).toBe("gpt-4o");
      expect(s.attributes["llm.cost_usd"]).toBe(
        estimateCost("gpt-4o", 10, 5),
      );
    });

    it("extracts tool calls from the response", () => {
      const span = tracer.startSpan("openai.chat.completions", {
        spanType: SpanType.LLM_CALL,
      });

      const response: OpenAIChatCompletion = {
        choices: [
          {
            message: {
              content: null,
              tool_calls: [
                {
                  id: "call_1",
                  function: {
                    name: "get_weather",
                    arguments: '{"city":"NYC"}',
                  },
                },
              ],
            },
            finish_reason: "tool_calls",
          },
        ],
        usage: { prompt_tokens: 20, completion_tokens: 10, total_tokens: 30 },
        model: "gpt-4o",
      };

      _applyResponseAttributes(span, response, "gpt-4o");
      tracer.endSpan(span, SpanStatus.OK);

      const s = exporter.spans[0]!;
      expect(s.attributes["llm.completion"]).toBe("");
      expect(s.attributes["llm.finish_reason"]).toBe("tool_calls");

      const toolCalls = JSON.parse(s.attributes["llm.tool_calls"] as string);
      expect(toolCalls).toHaveLength(1);
      expect(toolCalls[0].function.name).toBe("get_weather");
    });

    it("handles empty choices gracefully", () => {
      const span = tracer.startSpan("openai.chat.completions", {
        spanType: SpanType.LLM_CALL,
      });

      const response: OpenAIChatCompletion = {
        choices: [],
        usage: null,
        model: "gpt-4o",
      };

      _applyResponseAttributes(span, response, "gpt-4o");
      tracer.endSpan(span, SpanStatus.OK);

      const s = exporter.spans[0]!;
      expect(s.attributes["llm.model"]).toBe("gpt-4o");
    });
  });

  describe("span creation via withSpan", () => {
    it("creates LLM span with correct attributes for a simulated call", () => {
      const result = tracer.withSpan(
        "openai.chat.completions",
        { spanType: SpanType.LLM_CALL },
        (span) => {
          span.setAttribute("llm.provider", "openai");
          span.setAttribute("llm.model", "gpt-4o");
          span.setAttribute(
            "llm.prompt",
            JSON.stringify([{ role: "user", content: "Hi" }]),
          );
          span.setAttribute("llm.completion", "Hello!");
          span.setAttribute("llm.tokens.input", 5);
          span.setAttribute("llm.tokens.output", 3);
          span.setAttribute("llm.tokens.total", 8);
          span.setAttribute("llm.cost_usd", estimateCost("gpt-4o", 5, 3));
          return "Hello!";
        },
      );

      expect(result).toBe("Hello!");
      expect(exporter.spans).toHaveLength(1);

      const s = exporter.spans[0]!;
      expect(s.span_type).toBe("llm_call");
      expect(s.status).toBe("ok");
      expect(s.name).toBe("openai.chat.completions");
      expect(s.attributes["llm.provider"]).toBe("openai");
      expect(s.attributes["llm.model"]).toBe("gpt-4o");
    });

    it("captures errors with error status", () => {
      expect(() =>
        tracer.withSpan(
          "openai.chat.completions",
          { spanType: SpanType.LLM_CALL },
          () => {
            throw new Error("API rate limit exceeded");
          },
        ),
      ).toThrow("API rate limit exceeded");

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.status).toBe("error");
      expect(s.error_message).toBe("API rate limit exceeded");
    });
  });
});
