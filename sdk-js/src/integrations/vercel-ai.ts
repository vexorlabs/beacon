/**
 * Vercel AI SDK integration — patches generateText() and streamText().
 *
 * Dynamically imports the "ai" package and monkey-patches the module
 * exports so every call is automatically wrapped in a Beacon LLM span.
 */

import { _getTracer } from "../index.js";
import { SpanType, SpanStatus } from "../models.js";
import { estimateCost } from "../pricing.js";

// ---------------------------------------------------------------------------
// Type definitions for the Vercel AI SDK subset we use
// ---------------------------------------------------------------------------

interface VercelLanguageModel {
  modelId?: string;
  provider?: string;
  config?: { modelId?: string; provider?: string };
}

interface VercelUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens?: number;
}

interface VercelToolCall {
  toolCallId: string;
  toolName: string;
  args: unknown;
}

interface GenerateTextParams {
  model: VercelLanguageModel;
  prompt?: string;
  messages?: unknown[];
  system?: string;
  [key: string]: unknown;
}

interface GenerateTextResult {
  text: string;
  usage: VercelUsage;
  toolCalls: VercelToolCall[];
  finishReason: string;
  [key: string]: unknown;
}

interface StreamTextParams {
  model: VercelLanguageModel;
  prompt?: string;
  messages?: unknown[];
  system?: string;
  [key: string]: unknown;
}

interface StreamTextResult {
  textStream: AsyncIterable<string>;
  text: Promise<string>;
  usage: Promise<VercelUsage>;
  toolCalls: Promise<VercelToolCall[]>;
  finishReason: Promise<string>;
  [key: string]: unknown;
}

type GenerateTextFn = (params: GenerateTextParams) => Promise<GenerateTextResult>;
type StreamTextFn = (params: StreamTextParams) => StreamTextResult;

interface AiModule {
  generateText: GenerateTextFn;
  streamText: StreamTextFn;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractModelId(model: VercelLanguageModel): string {
  return model.modelId ?? model.config?.modelId ?? "unknown";
}

function extractProvider(model: VercelLanguageModel): string {
  if (model.provider) return model.provider;
  if (model.config?.provider) return model.config.provider;
  return "vercel-ai";
}

function buildPromptString(params: GenerateTextParams | StreamTextParams): string {
  if (typeof params.prompt === "string") return params.prompt;
  if (params.messages) return JSON.stringify(params.messages);
  if (typeof params.system === "string") return params.system;
  return "";
}

// ---------------------------------------------------------------------------
// Patched functions
// ---------------------------------------------------------------------------

function patchGenerateText(original: GenerateTextFn): GenerateTextFn {
  return async function patchedGenerateText(
    params: GenerateTextParams,
  ): Promise<GenerateTextResult> {
    const tracer = _getTracer();
    if (!tracer) {
      return original(params);
    }

    const modelId = extractModelId(params.model);
    const span = tracer.startSpan(`generateText(${modelId})`, {
      spanType: SpanType.LLM_CALL,
    });

    span.setAttribute("llm.provider", extractProvider(params.model));
    span.setAttribute("llm.model", modelId);
    span.setAttribute("llm.prompt", buildPromptString(params));

    try {
      const result = await original(params);

      span.setAttribute("llm.completion", result.text);
      span.setAttribute("llm.tokens.prompt", result.usage.promptTokens);
      span.setAttribute("llm.tokens.completion", result.usage.completionTokens);
      span.setAttribute(
        "llm.tokens.total",
        result.usage.totalTokens ??
          result.usage.promptTokens + result.usage.completionTokens,
      );
      span.setAttribute(
        "llm.cost_usd",
        estimateCost(modelId, result.usage.promptTokens, result.usage.completionTokens),
      );
      span.setAttribute("llm.finish_reason", result.finishReason);

      if (result.toolCalls && result.toolCalls.length > 0) {
        span.setAttribute("llm.tool_calls", JSON.stringify(result.toolCalls));
      }

      tracer.endSpan(span, SpanStatus.OK);
      return result;
    } catch (err: unknown) {
      tracer.endSpan(
        span,
        SpanStatus.ERROR,
        err instanceof Error ? err.message : String(err),
      );
      throw err;
    }
  };
}

function patchStreamText(original: StreamTextFn): StreamTextFn {
  return function patchedStreamText(params: StreamTextParams): StreamTextResult {
    const maybeTracer = _getTracer();
    if (!maybeTracer) {
      return original(params);
    }
    const tracer = maybeTracer;

    const modelId = extractModelId(params.model);
    const span = tracer.startSpan(`streamText(${modelId})`, {
      spanType: SpanType.LLM_CALL,
    });

    span.setAttribute("llm.provider", extractProvider(params.model));
    span.setAttribute("llm.model", modelId);
    span.setAttribute("llm.prompt", buildPromptString(params));

    let streamResult: StreamTextResult;
    try {
      streamResult = original(params);
    } catch (err: unknown) {
      tracer.endSpan(
        span,
        SpanStatus.ERROR,
        err instanceof Error ? err.message : String(err),
      );
      throw err;
    }

    let spanEnded = false;

    function endSpanOnce(
      status: typeof SpanStatus.OK | typeof SpanStatus.ERROR,
      errorMessage?: string,
    ): void {
      if (spanEnded) return;
      spanEnded = true;
      tracer.endSpan(span, status, errorMessage);
    }

    // Finalize when all promises resolve
    const finalize = Promise.all([
      streamResult.text,
      streamResult.usage,
      streamResult.toolCalls,
      streamResult.finishReason,
    ])
      .then(([text, usage, toolCalls, finishReason]) => {
        span.setAttribute("llm.completion", text);
        span.setAttribute("llm.tokens.prompt", usage.promptTokens);
        span.setAttribute("llm.tokens.completion", usage.completionTokens);
        span.setAttribute(
          "llm.tokens.total",
          usage.totalTokens ?? usage.promptTokens + usage.completionTokens,
        );
        span.setAttribute(
          "llm.cost_usd",
          estimateCost(modelId, usage.promptTokens, usage.completionTokens),
        );
        span.setAttribute("llm.finish_reason", finishReason);

        if (toolCalls && toolCalls.length > 0) {
          span.setAttribute("llm.tool_calls", JSON.stringify(toolCalls));
        }

        endSpanOnce(SpanStatus.OK);
      })
      .catch((err: unknown) => {
        endSpanOnce(
          SpanStatus.ERROR,
          err instanceof Error ? err.message : String(err),
        );
      });

    // Wrap textStream to ensure span finalization
    const originalTextStream = streamResult.textStream;

    async function* wrappedTextStream(): AsyncGenerator<string, void, undefined> {
      try {
        for await (const chunk of originalTextStream) {
          yield chunk;
        }
      } catch (err: unknown) {
        endSpanOnce(
          SpanStatus.ERROR,
          err instanceof Error ? err.message : String(err),
        );
        throw err;
      }
      await finalize;
    }

    const proxy: StreamTextResult = Object.create(
      streamResult,
    ) as StreamTextResult;
    Object.defineProperty(proxy, "textStream", {
      value: wrappedTextStream(),
      enumerable: true,
      configurable: true,
    });

    return proxy;
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Patch `generateText` and `streamText` from the Vercel AI SDK (`ai` package).
 *
 * Uses dynamic `import()` instead of `require()` so that the patch targets
 * the same module instance regardless of whether the consumer uses CJS or ESM.
 *
 * If the package is not installed, this silently returns.
 */
export async function patch(): Promise<void> {
  let aiModule: AiModule;
  try {
    // Use a variable so TypeScript doesn't try to resolve the module at
    // compile time (ai is an optional peer dependency).
    const modulePath = "ai";
    aiModule = (await import(modulePath)) as AiModule;
  } catch {
    // "ai" package is not installed — nothing to patch.
    return;
  }

  if (typeof aiModule.generateText === "function") {
    const original = aiModule.generateText;
    aiModule.generateText = patchGenerateText(original);
  }

  if (typeof aiModule.streamText === "function") {
    const original = aiModule.streamText;
    aiModule.streamText = patchStreamText(original);
  }
}
