/**
 * Anthropic integration — patches the @anthropic-ai/sdk npm package.
 *
 * Monkey-patches `Messages.prototype.create` so every call automatically
 * creates an `llm_call` span with prompt, completion, token counts, and cost.
 *
 * Supports both non-streaming and streaming responses.
 */

import { _getTracer } from "../index.js";
import { SpanStatus, SpanType, type Span } from "../models.js";
import { estimateCost } from "../pricing.js";
import type { BeaconTracer } from "../tracer.js";

let _patched = false;
let _originalCreate: ((...args: unknown[]) => unknown) | null = null;

// ---------------------------------------------------------------------------
// Types for Anthropic SDK structures
// ---------------------------------------------------------------------------

interface AnthropicTextBlock {
  type: "text";
  text: string;
}

interface AnthropicToolUseBlock {
  type: "tool_use";
  id: string;
  name: string;
  input: Record<string, unknown>;
}

type AnthropicContentBlock = AnthropicTextBlock | AnthropicToolUseBlock;

interface AnthropicUsage {
  input_tokens: number;
  output_tokens: number;
}

interface AnthropicMessage {
  content: AnthropicContentBlock[];
  usage: AnthropicUsage;
  model: string;
  stop_reason: string | null;
}

interface AnthropicMessageStartEvent {
  type: "message_start";
  message: { usage: { input_tokens: number } };
}

interface AnthropicContentBlockDeltaEvent {
  type: "content_block_delta";
  delta: { type: "text_delta"; text: string } | { type: string };
}

interface AnthropicMessageDeltaEvent {
  type: "message_delta";
  delta: { stop_reason: string | null };
  usage: { output_tokens: number };
}

type AnthropicStreamEvent =
  | AnthropicMessageStartEvent
  | AnthropicContentBlockDeltaEvent
  | AnthropicMessageDeltaEvent
  | { type: string };

interface CreateParams {
  model?: string;
  messages?: Array<Record<string, unknown>>;
  system?: string;
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Stream wrapper
// ---------------------------------------------------------------------------

class AnthropicStreamWrapper {
  private readonly _stream: AsyncIterable<AnthropicStreamEvent>;
  private readonly _span: Span;
  private readonly _tracer: BeaconTracer;
  private readonly _model: string;
  private readonly _chunks: string[] = [];
  private _inputTokens = 0;
  private _outputTokens = 0;
  private _finishReason: string | null = null;
  private _finalized = false;

  constructor(
    stream: AsyncIterable<AnthropicStreamEvent>,
    span: Span,
    tracer: BeaconTracer,
    model: string,
  ) {
    this._stream = stream;
    this._span = span;
    this._tracer = tracer;
    this._model = model;
  }

  [Symbol.asyncIterator](): AsyncIterator<AnthropicStreamEvent> {
    const self = this;
    const iterator = this._stream[Symbol.asyncIterator]();

    return {
      async next(): Promise<IteratorResult<AnthropicStreamEvent>> {
        try {
          const result = await iterator.next();
          if (result.done) {
            self._finalize(SpanStatus.OK);
            return result;
          }
          self._processEvent(result.value);
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

  private _processEvent(event: AnthropicStreamEvent): void {
    if (event.type === "message_start") {
      const e = event as AnthropicMessageStartEvent;
      if (e.message?.usage) {
        this._inputTokens = e.message.usage.input_tokens ?? 0;
      }
    } else if (event.type === "content_block_delta") {
      const e = event as AnthropicContentBlockDeltaEvent;
      if ("text" in e.delta) {
        this._chunks.push((e.delta as { type: "text_delta"; text: string }).text);
      }
    } else if (event.type === "message_delta") {
      const e = event as AnthropicMessageDeltaEvent;
      if (e.delta?.stop_reason) {
        this._finishReason = e.delta.stop_reason;
      }
      if (e.usage?.output_tokens !== undefined) {
        this._outputTokens = e.usage.output_tokens;
      }
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

    const totalTokens = this._inputTokens + this._outputTokens;
    this._span.setAttribute("llm.tokens.input", this._inputTokens);
    this._span.setAttribute("llm.tokens.output", this._outputTokens);
    this._span.setAttribute("llm.tokens.total", totalTokens);
    this._span.setAttribute(
      "llm.cost_usd",
      estimateCost(this._model, this._inputTokens, this._outputTokens),
    );

    this._tracer.endSpan(this._span, status, errorMessage);
  }
}

// ---------------------------------------------------------------------------
// Response attribute extraction (non-streaming)
// ---------------------------------------------------------------------------

function applyResponseAttributes(
  span: Span,
  response: AnthropicMessage,
  model: string,
): void {
  // Extract text from first text block
  let completion = "";
  for (const block of response.content) {
    if (block.type === "text") {
      completion = block.text;
      break;
    }
  }
  span.setAttribute("llm.completion", completion);

  // Extract tool calls
  const toolCalls = response.content
    .filter((b): b is AnthropicToolUseBlock => b.type === "tool_use")
    .map((b) => ({ id: b.id, name: b.name, input: b.input }));
  if (toolCalls.length > 0) {
    span.setAttribute("llm.tool_calls", JSON.stringify(toolCalls));
  }

  if (response.stop_reason) {
    span.setAttribute("llm.finish_reason", response.stop_reason);
  }

  if (response.usage) {
    const inputTokens = response.usage.input_tokens ?? 0;
    const outputTokens = response.usage.output_tokens ?? 0;
    span.setAttribute("llm.tokens.input", inputTokens);
    span.setAttribute("llm.tokens.output", outputTokens);
    span.setAttribute("llm.tokens.total", inputTokens + outputTokens);
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
// Prompt building
// ---------------------------------------------------------------------------

function buildPromptJson(params: CreateParams): string {
  const parts: Array<Record<string, unknown>> = [];
  if (params.system !== undefined) {
    parts.push({ role: "system", content: params.system });
  }
  if (params.messages) {
    for (const msg of params.messages) {
      parts.push(msg);
    }
  }
  return JSON.stringify(parts);
}

// ---------------------------------------------------------------------------
// Patch / Unpatch
// ---------------------------------------------------------------------------

/**
 * Monkey-patch the Anthropic SDK's `Messages.prototype.create` to
 * automatically instrument message creation calls.
 *
 * If the `@anthropic-ai/sdk` package is not installed, this silently returns.
 */
export function patch(): void {
  if (_patched) return;

  let MessagesProto: { create: (...args: unknown[]) => unknown };
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require("@anthropic-ai/sdk/resources/messages") as {
      Messages: { prototype: { create: (...args: unknown[]) => unknown } };
    };
    MessagesProto = mod.Messages.prototype;
  } catch {
    // @anthropic-ai/sdk not installed — silently skip
    return;
  }

  _originalCreate = MessagesProto.create;
  const originalCreate = _originalCreate;

  MessagesProto.create = function patchedCreate(
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

    const span = tracer.startSpan("anthropic.messages.create", {
      spanType: SpanType.LLM_CALL,
      attributes: {
        "llm.provider": "anthropic",
        "llm.model": model,
      },
    });

    span.setAttribute("llm.prompt", buildPromptJson(body));

    if (body.temperature != null) {
      span.setAttribute("llm.temperature", body.temperature);
    }
    if (body.max_tokens != null) {
      span.setAttribute("llm.max_tokens", body.max_tokens);
    }

    try {
      const result = originalCreate.call(this, body, ...restArgs);

      if (result instanceof Promise) {
        return (result as Promise<unknown>).then(
          (response: unknown) => {
            if (isStream) {
              return new AnthropicStreamWrapper(
                response as AsyncIterable<AnthropicStreamEvent>,
                span,
                tracer,
                model,
              );
            }
            applyResponseAttributes(span, response as AnthropicMessage, model);
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

      if (isStream) {
        return new AnthropicStreamWrapper(
          result as AsyncIterable<AnthropicStreamEvent>,
          span,
          tracer,
          model,
        );
      }
      applyResponseAttributes(span, result as AnthropicMessage, model);
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
 * Restore the original `Messages.prototype.create` method.
 */
export function unpatch(): void {
  if (!_patched) return;

  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require("@anthropic-ai/sdk/resources/messages") as {
      Messages: { prototype: { create: (...args: unknown[]) => unknown } };
    };
    if (_originalCreate) {
      mod.Messages.prototype.create = _originalCreate;
    }
  } catch {
    // not installed
  }

  _originalCreate = null;
  _patched = false;
}

export { AnthropicStreamWrapper as _AnthropicStreamWrapper };
export { applyResponseAttributes as _applyResponseAttributes };
export type { AnthropicMessage, AnthropicStreamEvent, AnthropicUsage, CreateParams };
