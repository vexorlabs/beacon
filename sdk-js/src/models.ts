/**
 * Core span models mirroring the Python SDK's beacon_sdk/models.py.
 *
 * Attribute naming uses dot notation (e.g. "llm.prompt", "llm.completion")
 * to match the Python SDK and backend schema exactly.
 */

import { randomUUID } from "node:crypto";

export const SpanType = {
  LLM_CALL: "llm_call",
  TOOL_USE: "tool_use",
  AGENT_STEP: "agent_step",
  BROWSER_ACTION: "browser_action",
  FILE_OPERATION: "file_operation",
  SHELL_COMMAND: "shell_command",
  CHAIN: "chain",
  CUSTOM: "custom",
} as const;

export type SpanType = (typeof SpanType)[keyof typeof SpanType];

export const SpanStatus = {
  OK: "ok",
  ERROR: "error",
  UNSET: "unset",
} as const;

export type SpanStatus = (typeof SpanStatus)[keyof typeof SpanStatus];

const TRUNCATION_LIMITS: Record<string, number> = {
  "llm.prompt": 50_000,
  "llm.completion": 50_000,
  "file.content": 2_000,
  "shell.stdout": 4_000,
  "shell.stderr": 4_000,
};

const SCREENSHOT_MAX_BYTES = 500_000;

export interface SpanData {
  span_id: string;
  trace_id: string;
  parent_span_id: string | null;
  span_type: SpanType;
  name: string;
  status: SpanStatus;
  error_message: string | null;
  start_time: number;
  end_time: number | null;
  attributes: Record<string, unknown>;
  sdk_language: string;
}

export class Span {
  readonly span_id: string;
  readonly trace_id: string;
  readonly parent_span_id: string | null;
  span_type: SpanType;
  name: string;
  status: SpanStatus;
  error_message: string | null;
  readonly start_time: number;
  end_time: number | null;
  attributes: Record<string, unknown>;

  constructor(options: {
    span_id?: string;
    trace_id: string;
    parent_span_id?: string | null;
    span_type?: SpanType;
    name: string;
    attributes?: Record<string, unknown>;
  }) {
    this.span_id = options.span_id ?? randomUUID();
    this.trace_id = options.trace_id;
    this.parent_span_id = options.parent_span_id ?? null;
    this.span_type = options.span_type ?? SpanType.CUSTOM;
    this.name = options.name;
    this.status = SpanStatus.UNSET;
    this.error_message = null;
    this.start_time = Date.now() / 1000; // epoch seconds to match Python SDK
    this.end_time = null;
    this.attributes = options.attributes ? { ...options.attributes } : {};
  }

  setAttribute(key: string, value: unknown): void {
    if (typeof value === "string" && key in TRUNCATION_LIMITS) {
      const limit = TRUNCATION_LIMITS[key]!;
      if (value.length > limit) {
        value = value.slice(0, limit) + "[TRUNCATED]";
      }
    }
    if (key === "browser.screenshot" && typeof value === "string") {
      if (value.length > SCREENSHOT_MAX_BYTES) {
        return; // drop oversized screenshots
      }
    }
    this.attributes[key] = value;
  }

  end(status: SpanStatus = SpanStatus.OK, errorMessage?: string): void {
    this.end_time = Date.now() / 1000;
    this.status = status;
    if (errorMessage !== undefined) {
      this.error_message = errorMessage;
    }
  }

  toDict(): SpanData {
    return {
      span_id: this.span_id,
      trace_id: this.trace_id,
      parent_span_id: this.parent_span_id,
      span_type: this.span_type,
      name: this.name,
      status: this.status,
      error_message: this.error_message,
      start_time: this.start_time,
      end_time: this.end_time,
      attributes: this.attributes,
      sdk_language: "javascript",
    };
  }
}
