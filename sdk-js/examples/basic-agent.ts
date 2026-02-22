/**
 * Beacon JS SDK — Basic Agent Example
 *
 * Simple Node.js agent that uses OpenAI for chat completions with automatic
 * tracing via Beacon's auto-patching. No manual span creation needed.
 *
 * Requires:
 *   npm install beacon-sdk openai
 *
 * Usage:
 *   1. Start Beacon backend: make dev
 *   2. Set your OpenAI API key: export OPENAI_API_KEY=sk-...
 *   3. Run: npx tsx sdk-js/examples/basic-agent.ts
 *   4. Open http://localhost:5173 to see traces
 *
 * Span tree produced:
 *   research_agent (agent_step)
 *     ├── openai.chat.completions (llm_call, auto-patched)
 *     ├── summarize_results (tool_use)
 *     └── openai.chat.completions (llm_call, auto-patched)
 */

import { init, observe, flush, getCurrentSpan, shutdown } from "beacon-sdk";
import { SpanType } from "beacon-sdk";
import OpenAI from "openai";

// Initialize Beacon — auto-patches OpenAI automatically
init();

const client = new OpenAI();

// --- Tool functions ---

const summarizeResults = observe(
  { name: "summarize_results", spanType: SpanType.TOOL_USE },
  (results: string): string => {
    const span = getCurrentSpan();
    if (span) {
      span.setAttribute("tool.name", "summarize_results");
      span.setAttribute("tool.input", JSON.stringify({ length: results.length }));
      span.setAttribute("tool.output", `Summarized ${results.length} chars`);
    }
    // Simulate summarization
    return results.slice(0, 200) + "...";
  },
);

// --- Agent function ---

const researchAgent = observe(
  { name: "research_agent", spanType: SpanType.AGENT_STEP },
  async (question: string): Promise<string> => {
    // Step 1: Ask the model to research
    const planResponse = await client.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: "You are a research assistant. Answer concisely.",
        },
        { role: "user", content: question },
      ],
      temperature: 0.3,
    });

    const research = planResponse.choices[0]?.message.content ?? "";

    // Step 2: Summarize
    const summary = summarizeResults(research);

    // Step 3: Generate final answer
    const finalResponse = await client.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: "Provide a clear, final answer based on the research summary.",
        },
        { role: "user", content: `Based on this research: ${summary}` },
      ],
      temperature: 0.2,
    });

    return finalResponse.choices[0]?.message.content ?? "";
  },
);

// --- Main ---

async function main(): Promise<void> {
  const answer = await researchAgent("What caused the 2008 financial crisis?");
  console.log("Agent answer:", answer);
  await shutdown();
}

main().catch(console.error);
