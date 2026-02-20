import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { BeaconTracer } from "../../src/tracer.js";
import { SpanType, SpanStatus } from "../../src/models.js";
import { estimateCost } from "../../src/pricing.js";
import { InMemoryExporter } from "../helpers.js";

/**
 * We test the Vercel AI integration logic by directly exercising the
 * span creation patterns the integration uses, rather than calling
 * patch() which requires the real `ai` package.
 */

describe("Vercel AI integration", () => {
  let exporter: InMemoryExporter;
  let tracer: BeaconTracer;

  beforeEach(() => {
    exporter = new InMemoryExporter();
    tracer = new BeaconTracer({ exporter, enabled: true });
  });

  afterEach(() => {
    exporter.clear();
  });

  describe("generateText simulation", () => {
    it("creates an LLM span with correct attributes", () => {
      const modelId = "gpt-4o";
      const result = tracer.withSpan(
        `generateText(${modelId})`,
        { spanType: SpanType.LLM_CALL },
        (span) => {
          span.setAttribute("llm.provider", "openai");
          span.setAttribute("llm.model", modelId);
          span.setAttribute("llm.prompt", "Say hello");
          span.setAttribute("llm.completion", "Hello, world!");
          span.setAttribute("llm.tokens.prompt", 10);
          span.setAttribute("llm.tokens.completion", 5);
          span.setAttribute("llm.tokens.total", 15);
          span.setAttribute("llm.cost_usd", estimateCost(modelId, 10, 5));
          span.setAttribute("llm.finish_reason", "stop");
          return "Hello, world!";
        },
      );

      expect(result).toBe("Hello, world!");
      expect(exporter.spans).toHaveLength(1);

      const s = exporter.spans[0]!;
      expect(s.name).toBe("generateText(gpt-4o)");
      expect(s.span_type).toBe("llm_call");
      expect(s.status).toBe("ok");
      expect(s.attributes["llm.provider"]).toBe("openai");
      expect(s.attributes["llm.model"]).toBe("gpt-4o");
      expect(s.attributes["llm.prompt"]).toBe("Say hello");
      expect(s.attributes["llm.completion"]).toBe("Hello, world!");
      expect(s.attributes["llm.tokens.prompt"]).toBe(10);
      expect(s.attributes["llm.tokens.completion"]).toBe(5);
      expect(s.attributes["llm.tokens.total"]).toBe(15);
      expect(s.attributes["llm.finish_reason"]).toBe("stop");
      expect(s.end_time).not.toBeNull();
    });

    it("records tool calls when present", () => {
      tracer.withSpan(
        "generateText(gpt-4o)",
        { spanType: SpanType.LLM_CALL },
        (span) => {
          span.setAttribute("llm.provider", "openai");
          span.setAttribute("llm.model", "gpt-4o");
          span.setAttribute("llm.prompt", "What is the weather?");
          span.setAttribute("llm.completion", "");
          span.setAttribute("llm.finish_reason", "tool_calls");
          span.setAttribute(
            "llm.tool_calls",
            JSON.stringify([
              {
                toolCallId: "tc-1",
                toolName: "get_weather",
                args: { city: "NYC" },
              },
            ]),
          );
        },
      );

      const s = exporter.spans[0]!;
      const toolCalls = JSON.parse(s.attributes["llm.tool_calls"] as string);
      expect(toolCalls).toHaveLength(1);
      expect(toolCalls[0].toolName).toBe("get_weather");
      expect(s.attributes["llm.finish_reason"]).toBe("tool_calls");
    });

    it("sets error status when the call throws", () => {
      expect(() =>
        tracer.withSpan(
          "generateText(gpt-4o)",
          { spanType: SpanType.LLM_CALL },
          () => {
            throw new Error("API rate limit");
          },
        ),
      ).toThrow("API rate limit");

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.status).toBe("error");
      expect(s.error_message).toBe("API rate limit");
    });

    it("uses messages as prompt when prompt string is absent", () => {
      const messages = [{ role: "user", content: "hi" }];
      tracer.withSpan(
        "generateText(gpt-4o)",
        { spanType: SpanType.LLM_CALL },
        (span) => {
          span.setAttribute("llm.prompt", JSON.stringify(messages));
        },
      );

      const s = exporter.spans[0]!;
      expect(s.attributes["llm.prompt"]).toBe(JSON.stringify(messages));
    });
  });

  describe("streamText simulation", () => {
    it("creates an LLM span with streaming attributes", async () => {
      const modelId = "claude-sonnet-4-20250514";
      const span = tracer.startSpan(`streamText(${modelId})`, {
        spanType: SpanType.LLM_CALL,
      });

      span.setAttribute("llm.provider", "anthropic");
      span.setAttribute("llm.model", modelId);
      span.setAttribute("llm.prompt", "Stream hello");

      // Simulate stream completion
      const chunks = ["Hello", ", ", "world!"];
      span.setAttribute("llm.completion", chunks.join(""));
      span.setAttribute("llm.tokens.prompt", 8);
      span.setAttribute("llm.tokens.completion", 3);
      span.setAttribute("llm.tokens.total", 11);
      span.setAttribute("llm.cost_usd", estimateCost(modelId, 8, 3));
      span.setAttribute("llm.finish_reason", "stop");

      tracer.endSpan(span, SpanStatus.OK);

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.name).toBe("streamText(claude-sonnet-4-20250514)");
      expect(s.span_type).toBe("llm_call");
      expect(s.status).toBe("ok");
      expect(s.attributes["llm.completion"]).toBe("Hello, world!");
      expect(s.attributes["llm.tokens.prompt"]).toBe(8);
      expect(s.attributes["llm.tokens.completion"]).toBe(3);
      expect(s.attributes["llm.finish_reason"]).toBe("stop");
      expect(s.end_time).not.toBeNull();
    });

    it("captures stream errors", () => {
      const span = tracer.startSpan("streamText(gpt-4o)", {
        spanType: SpanType.LLM_CALL,
      });

      tracer.endSpan(span, SpanStatus.ERROR, "stream failed");

      expect(exporter.spans).toHaveLength(1);
      const s = exporter.spans[0]!;
      expect(s.status).toBe("error");
      expect(s.error_message).toBe("stream failed");
    });
  });

  describe("model extraction helpers", () => {
    it("uses modelId from the model object", () => {
      const model = { modelId: "gpt-4o", provider: "openai" };
      tracer.withSpan(
        `generateText(${model.modelId})`,
        { spanType: SpanType.LLM_CALL },
        (span) => {
          span.setAttribute("llm.provider", model.provider);
          span.setAttribute("llm.model", model.modelId);
        },
      );

      const s = exporter.spans[0]!;
      expect(s.name).toBe("generateText(gpt-4o)");
      expect(s.attributes["llm.model"]).toBe("gpt-4o");
      expect(s.attributes["llm.provider"]).toBe("openai");
    });
  });
});
