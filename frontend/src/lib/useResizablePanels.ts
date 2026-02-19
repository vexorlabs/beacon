import { useCallback, useEffect, useRef, useState } from "react";

interface ResizablePanels {
  leftWidth: number;
  rightWidth: number;
  leftHandleProps: { onMouseDown: (e: React.MouseEvent) => void };
  rightHandleProps: { onMouseDown: (e: React.MouseEvent) => void };
}

const MIN_WIDTH = 170;
const MAX_LEFT = 480;
const MAX_RIGHT = 600;

export function useResizablePanels(
  initialLeft = 280,
  initialRight = 380,
): ResizablePanels {
  const [leftWidth, setLeftWidth] = useState(initialLeft);
  const [rightWidth, setRightWidth] = useState(initialRight);
  const dragTarget = useRef<"left" | "right" | null>(null);
  const startX = useRef(0);
  const startWidth = useRef(0);
  const handlersRef = useRef<{
    move: (e: MouseEvent) => void;
    up: () => void;
  } | null>(null);

  // Store handlers in a ref to avoid circular dependencies
  useEffect(() => {
    const move = (e: MouseEvent) => {
      if (!dragTarget.current) return;
      const delta = e.clientX - startX.current;
      if (dragTarget.current === "left") {
        const w = Math.max(
          MIN_WIDTH,
          Math.min(MAX_LEFT, startWidth.current + delta),
        );
        setLeftWidth(w);
      } else {
        const w = Math.max(
          MIN_WIDTH,
          Math.min(MAX_RIGHT, startWidth.current - delta),
        );
        setRightWidth(w);
      }
    };

    const up = () => {
      dragTarget.current = null;
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    handlersRef.current = { move, up };

    return () => {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
    };
  }, []);

  const startDrag = useCallback(
    (target: "left" | "right", currentWidth: number) =>
      (e: React.MouseEvent) => {
        e.preventDefault();
        const handlers = handlersRef.current;
        if (!handlers) return;
        dragTarget.current = target;
        startX.current = e.clientX;
        startWidth.current = currentWidth;
        document.body.style.userSelect = "none";
        document.body.style.cursor = "col-resize";
        document.addEventListener("mousemove", handlers.move);
        document.addEventListener("mouseup", handlers.up);
      },
    [],
  );

  return {
    leftWidth,
    rightWidth,
    leftHandleProps: { onMouseDown: startDrag("left", leftWidth) },
    rightHandleProps: { onMouseDown: startDrag("right", rightWidth) },
  };
}
