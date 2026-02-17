import type { WsEvent } from "./types";

const WS_URL = "ws://localhost:7474/ws/live";
const INITIAL_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

type EventHandler<E extends WsEvent["event"]> = (
  data: Extract<WsEvent, { event: E }>,
) => void;

export class BeaconWebSocket {
  private ws: WebSocket | null = null;
  private reconnectDelay = INITIAL_DELAY_MS;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;
  private handlers: {
    span_created: Array<EventHandler<"span_created">>;
    span_updated: Array<EventHandler<"span_updated">>;
    trace_created: Array<EventHandler<"trace_created">>;
  } = {
    span_created: [],
    span_updated: [],
    trace_created: [],
  };

  connect(): void {
    this.intentionalClose = false;
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      this.reconnectDelay = INITIAL_DELAY_MS;
    };

    this.ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(String(event.data)) as WsEvent;
      const eventHandlers = this.handlers[data.event];
      if (eventHandlers) {
        for (const handler of eventHandlers) {
          (handler as (data: WsEvent) => void)(data);
        }
      }
    };

    this.ws.onclose = () => {
      if (!this.intentionalClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  subscribeToTrace(traceId: string): void {
    this.send({ action: "subscribe_trace", trace_id: traceId });
  }

  unsubscribeTrace(traceId: string): void {
    this.send({ action: "unsubscribe_trace", trace_id: traceId });
  }

  onSpanCreated(handler: EventHandler<"span_created">): () => void {
    this.handlers.span_created.push(handler);
    return () => {
      this.handlers.span_created = this.handlers.span_created.filter(
        (h) => h !== handler,
      );
    };
  }

  onSpanUpdated(handler: EventHandler<"span_updated">): () => void {
    this.handlers.span_updated.push(handler);
    return () => {
      this.handlers.span_updated = this.handlers.span_updated.filter(
        (h) => h !== handler,
      );
    };
  }

  onTraceCreated(handler: EventHandler<"trace_created">): () => void {
    this.handlers.trace_created.push(handler);
    return () => {
      this.handlers.trace_created = this.handlers.trace_created.filter(
        (h) => h !== handler,
      );
    };
  }

  private send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_DELAY_MS);
  }
}
