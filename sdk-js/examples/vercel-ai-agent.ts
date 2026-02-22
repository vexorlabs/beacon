/**
 * Beacon JS SDK — Vercel AI SDK Example
 *
 * Demonstrates using Beacon with the Vercel AI SDK's generateText() and
 * streamText() functions. Beacon auto-patches both automatically.
 *
 * Requires:
 *   npm install beacon-sdk ai @ai-sdk/openai
 *
 * Usage:
 *   1. Start Beacon backend: make dev
 *   2. Set your OpenAI API key: export OPENAI_API_KEY=sk-...
 *   3. Run: npx tsx sdk-js/examples/vercel-ai-agent.ts
 *   4. Open http://localhost:5173 to see traces
 *
 * Span tree produced:
 *   writing_assistant (agent_step)
 *     ├── generateText(gpt-4o) (llm_call, auto-patched)
 *     ├── format_outline (tool_use)
 *     └── streamText(gpt-4o) (llm_call, auto-patched, streaming)
 */

import { init, observe, getCurrentSpan, shutdown } from "beacon-sdk";
import { SpanType } from "beacon-sdk";
import { generateText, streamText } from "ai";
import { openai } from "@ai-sdk/openai";

// Initialize Beacon — auto-patches Vercel AI SDK automatically
init();

// --- Tool functions ---

const formatOutline = observe(
  { name: "format_outline", spanType: SpanType.TOOL_USE },
  (outline: string): string => {
    const span = getCurrentSpan();
    if (span) {
      span.setAttribute("tool.name", "format_outline");
      span.setAttribute("tool.input", JSON.stringify({ length: outline.length }));
    }

    const formatted = outline
      .split("\n")
      .filter((line) => line.trim())
      .map((line, i) => `${i + 1}. ${line.trim()}`)
      .join("\n");

    if (span) {
      span.setAttribute("tool.output", formatted);
    }
    return formatted;
  },
);

// --- Agent function ---

const writingAssistant = observe(
  { name: "writing_assistant", spanType: SpanType.AGENT_STEP },
  async (topic: string): Promise<string> => {
    // Step 1: Generate an outline using generateText()
    const outlineResult = await generateText({
      model: openai("gpt-4o"),
      system: "You are a writing assistant. Create concise outlines.",
      prompt: `Create a 5-point outline for an article about: ${topic}`,
    });

    // Step 2: Format the outline
    const formattedOutline = formatOutline(outlineResult.text);
    console.log("Outline:\n", formattedOutline, "\n");

    // Step 3: Stream the full article using streamText()
    const articleResult = streamText({
      model: openai("gpt-4o"),
      system: "You are a writing assistant. Write clear, engaging articles.",
      prompt: `Write a short article based on this outline:\n\n${formattedOutline}`,
    });

    // Consume the stream and print chunks as they arrive
    let fullText = "";
    for await (const chunk of articleResult.textStream) {
      process.stdout.write(chunk);
      fullText += chunk;
    }
    console.log("\n");

    return fullText;
  },
);

// --- Main ---

async function main(): Promise<void> {
  const article = await writingAssistant(
    "the impact of open-source AI on software development",
  );
  console.log(`Article complete (${article.length} chars)`);
  await shutdown();
}

main().catch(console.error);
