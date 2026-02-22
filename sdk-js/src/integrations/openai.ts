/**
 * OpenAI auto-instrumentation for the Beacon JS SDK.
 *
 * Patches `Completions.prototype.create` on the `openai` npm package (v4+)
 * to create LLM spans automatically.
 *
 * Mirrors the Python SDK at beacon_sdk/integrations/openai.py.
 */

import { _getTracer } from "../index.js";
import { SpanStatus, SpanType, type Span } from "../models.js";
import { estimateCost } from "../pricing.js";
import type { BeaconTracer } from "../tracer.js";

let _patched = false;
let _originalCreate: ((...args: unknown[]) => unknown) | null = null;
let _completionsProto: { create: (...args: unknown[]) => unknown } | null = null;

// ---------------------------------------------------------------------------
// Types for OpenAI SDK structures (avoids importing the real package)
// ---------------------------------------------------------------------------

interface OpenAIChoice {
  message: {
    content: string | null;
    tool_calls?: Array<{
      id: string;
      function: { name: string; arguments: string };
    }>;
  };
  finish_reason: string | null;
}

interface OpenAIUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

interface OpenAIChatCompletion {
  choices: OpenAIChoice[];
  usage?: OpenAIUsage | null;
  model: string;
}

interface OpenAIStreamDelta {
  content?: string | null;
}

interface OpenAIStreamChoice {
  delta: OpenAIStreamDelta;
  finish_reason: string | null;
}

interface OpenAIStreamChunk {
  choices: OpenAIStreamChoice[];
  usage?: OpenAIUsage | null;
}

// ---------------------------------------------------------------------------
// Stream wrapper
// ---------------------------------------------------------------------------

class OpenAIStreamWrapper {
  private readonly _stream: AsyncIterable<OpenAIStreamChunk>;
  private readonly _span: Span;
  private readonly _tracer: BeaconTracer;
  private readonly _model: string;
  private readonly _chunks: string[] = [];
  private _finishReason: string | null = null;
  private _usage: OpenAIUsage | null = null;
  private _finalized = false;

  constructor(
    stream: AsyncIterable<OpenAIStreamChunk>,
    span: Span,
    tracer: BeaconTracer,
    model: string,
  ) {
    this._stream = stream;
    this._span = span;
    this._tracer = tracer;
    this._model = model;
  }

  [Symbol.asyncIterator](): AsyncIterator<OpenAIStreamChunk> {
    const self = this;
    const iterator = this._stream[Symbol.asyncIterator]();

    return {
      async next(): Promise<IteratorResult<OpenAIStreamChunk>> {
        try {
          const result = await iterator.next();
          if (result.done) {
            self._finalize(SpanStatus.OK);
            return result;
          }
          self._processChunk(result.value);
          return result;
        } catch (err: unknown) {
          self._finalize(
            SpanStatus.ERROR,
            err instanceof Error ? err.message : String(err),
          );
          throw err;
        }
      },
    };
  }

  private _processChunk(chunk: OpenAIStreamChunk): void {
    if (chunk.choices && chunk.choices.length > 0) {
      const choice = chunk.choices[0]!;
      if (choice.delta && choice.delta.content != null) {
        this._chunks.push(choice.delta.content);
      }
      if (choice.finish_reason != null) {
        this._finishReason = choice.finish_reason;
      }
    }
    if (chunk.usage != null) {
      this._usage = chunk.usage;
    }
  }

  private _finalize(
    status: typeof SpanStatus.OK | typeof SpanStatus.ERROR = SpanStatus.OK,
    errorMessage?: string,
  ): void {
    if (this._finalized) return;
    this._finalized = true;

    this._span.setAttribute("llm.completion", this._chunks.join(""));

    if (this._finishReason) {
      this._span.setAttribute("llm.finish_reason", this._finishReason);
    }

    if (this._usage) {
      const inputTokens = this._usage.prompt_tokens ?? 0;
      const outputTokens = this._usage.completion_tokens ?? 0;
      const totalTokens = this._usage.total_tokens ?? 0;
      this._span.setAttribute("llm.tokens.input", inputTokens);
      this._span.setAttribute("llm.tokens.output", outputTokens);
      this._span.setAttribute("llm.tokens.total", totalTokens);
      this._span.setAttribute(
        "llm.cost_usd",
        estimateCost(this._model, inputTokens, outputTokens),
      );
    }

    this._tracer.endSpan(this._span, status, errorMessage);
  }
}

// ---------------------------------------------------------------------------
// Response attribute extraction (non-streaming)
// ---------------------------------------------------------------------------

function applyResponseAttributes(
  span: Span,
  response: OpenAIChatCompletion,
  model: string,
): void {
  if (response.choices && response.choices.length > 0) {
    const choice = response.choices[0]!;
    if (choice.message) {
      span.setAttribute("llm.completion", choice.message.content ?? "");
      if (choice.message.tool_calls && choice.message.tool_calls.length > 0) {
        const toolCalls = choice.message.tool_calls.map((tc) => ({
          id: tc.id,
          function: {
            name: tc.function.name,
            arguments: tc.function.arguments,
          },
        }));
        span.setAttribute("llm.tool_calls", JSON.stringify(toolCalls));
      }
    }
    if (choice.finish_reason != null) {
      span.setAttribute("llm.finish_reason", choice.finish_reason);
    }
  }

  if (response.usage != null) {
    const inputTokens = response.usage.prompt_tokens ?? 0;
    const outputTokens = response.usage.completion_tokens ?? 0;
    const totalTokens = response.usage.total_tokens ?? 0;
    span.setAttribute("llm.tokens.input", inputTokens);
    span.setAttribute("llm.tokens.output", outputTokens);
    span.setAttribute("llm.tokens.total", totalTokens);
    span.setAttribute(
      "llm.cost_usd",
      estimateCost(model, inputTokens, outputTokens),
    );
  }

  if (response.model) {
    span.setAttribute("llm.model", response.model);
  }
}

// ---------------------------------------------------------------------------
// Patch / Unpatch
// ---------------------------------------------------------------------------

interface CreateParams {
  model?: string;
  messages?: unknown[];
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
  [key: string]: unknown;
}

/**
 * Monkey-patch the OpenAI SDK's `Completions.prototype.create` to
 * automatically instrument chat completion calls.
 *
 * Uses dynamic `import()` instead of `require()` so that the patch targets
 * the same module instance regardless of whether the consumer uses CJS or ESM.
 *
 * If the `openai` package is not installed, this silently returns.
 */
export async function patch(): Promise<void> {
  if (_patched) return;

  let CompletionsProto: { create: (...args: unknown[]) => unknown };
  try {
    // Use a variable so TypeScript doesn't try to resolve the module at
    // compile time (openai is an optional peer dependency).
    const modulePath = "openai/resources/chat/completions";
    const mod = (await import(modulePath)) as {
      Completions: { prototype: { create: (...args: unknown[]) => unknown } };
    };
    CompletionsProto = mod.Completions.prototype;
  } catch {
    // openai package not installed — silently skip
    return;
  }

  _completionsProto = CompletionsProto;
  _originalCreate = CompletionsProto.create;
  const originalCreate = _originalCreate;

  CompletionsProto.create = function patchedCreate(
    this: unknown,
    ...args: unknown[]
  ): unknown {
    const body = (args[0] ?? {}) as CreateParams;
    const restArgs = args.slice(1);

    const tracer = _getTracer();
    if (!tracer) {
      return originalCreate.call(this, body, ...restArgs);
    }

    const isStream = body.stream === true;
    const model = typeof body.model === "string" ? body.model : "unknown";

    const span = tracer.startSpan("openai.chat.completions", {
      spanType: SpanType.LLM_CALL,
      attributes: {
        "llm.provider": "openai",
        "llm.model": model,
      },
    });

    span.setAttribute("llm.prompt", JSON.stringify(body.messages ?? []));

    if (body.temperature != null) {
      span.setAttribute("llm.temperature", body.temperature);
    }
    if (body.max_tokens != null) {
      span.setAttribute("llm.max_tokens", body.max_tokens);
    }

    try {
      const result = originalCreate.call(this, body, ...restArgs);

      // The OpenAI v4 SDK always returns a Promise (even for streaming).
      if (result instanceof Promise) {
        return (result as Promise<unknown>).then(
          (response: unknown) => {
            if (isStream) {
              return new OpenAIStreamWrapper(
                response as AsyncIterable<OpenAIStreamChunk>,
                span,
                tracer,
                model,
              );
            }
            applyResponseAttributes(
              span,
              response as OpenAIChatCompletion,
              model,
            );
            tracer.endSpan(span, SpanStatus.OK);
            return response;
          },
          (err: unknown) => {
            tracer.endSpan(
              span,
              SpanStatus.ERROR,
              err instanceof Error ? err.message : String(err),
            );
            throw err;
          },
        );
      }

      // Synchronous path (unlikely with openai v4, but handle it)
      if (isStream) {
        return new OpenAIStreamWrapper(
          result as AsyncIterable<OpenAIStreamChunk>,
          span,
          tracer,
          model,
        );
      }
      applyResponseAttributes(span, result as OpenAIChatCompletion, model);
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

  _patched = true;
}

/**
 * Restore the original `Completions.prototype.create` method.
 */
export function unpatch(): void {
  if (!_patched) return;

  if (_completionsProto && _originalCreate) {
    _completionsProto.create = _originalCreate;
  }

  _completionsProto = null;
  _originalCreate = null;
  _patched = false;
}

export { OpenAIStreamWrapper as _OpenAIStreamWrapper };
export { applyResponseAttributes as _applyResponseAttributes };
export type {
  OpenAIChatCompletion,
  OpenAIStreamChunk,
  OpenAIUsage,
  OpenAIChoice,
  CreateParams,
};
