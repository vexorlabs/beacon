import { useEffect, useState } from "react";
import { countTokens } from "@/lib/tokenizer";

/**
 * Returns a debounced token count for the given text.
 */
export function useTokenCount(text: string, debounceMs = 300): number {
  const [count, setCount] = useState(() => countTokens(text));

  useEffect(() => {
    const timer = setTimeout(() => {
      setCount(countTokens(text));
    }, debounceMs);
    return () => clearTimeout(timer);
  }, [text, debounceMs]);

  return count;
}
