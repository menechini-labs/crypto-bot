import { useCallback, useEffect, useRef, useState } from 'react';

interface EventRecord {
  id: number;
  type: string;
  data: string;
  ts: string;
}

export default function EventConsole() {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(0);

  useEffect(() => {
    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      es = new EventSource('/api/events');
      setConnected(true);

      es.onmessage = (msg) => {
        try {
          const payload = JSON.parse(msg.data);
          idRef.current += 1;
          const rec: EventRecord = {
            id: idRef.current,
            type: payload.type ?? 'unknown',
            data: msg.data,
            ts: new Date().toLocaleTimeString(),
          };
          setEvents((prev) => {
            const next = [...prev, rec];
            return next.length > 200 ? next.slice(-200) : next;
          });
        } catch {
          // ignora JSON invalido
        }
      };

      es.onerror = () => {
        setConnected(false);
        es?.close();
        reconnectTimer = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      es?.close();
      clearTimeout(reconnectTimer);
    };
  }, []);

  const clearLog = useCallback(() => {
    setEvents([]);
    idRef.current = 0;
  }, []);

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events, paused]);

  return (
    <section className="panel evt-console">
      <header className="evt-console__head">
        <div>
          <p className="evt-console__kicker">LIVE EVENT STREAM</p>
          <h2 className="evt-console__title">Event Console</h2>
        </div>
        <div className="evt-console__controls">
          <span className={`evt-console__status evt-console__status--${connected ? 'up' : 'down'}`}>
            <span className="evt-console__dot" />
            {connected ? 'SSE connected' : 'reconnecting…'}
          </span>
          <button type="button" className="evt-console__btn" onClick={() => setPaused((p) => !p)}>
            {paused ? '▶ resume' : '⏸ pause'}
          </button>
          <button type="button" className="evt-console__btn evt-console__btn--clear" onClick={clearLog}>
            ✕ clear
          </button>
        </div>
      </header>

      <div className="evt-console__count">{events.length} events</div>

      <div className="evt-console__log">
        {events.length === 0 && (
          <div className="evt-console__empty">
            <p>Aguardando eventos…</p>
            <p className="muted">
              Eventos aparecerão aqui quando o WebSocket de mercado
              enviar candles, sinais ou outras notificações via EventBus.
            </p>
          </div>
        )}
        {events.map((ev) => (
          <div key={ev.id} className={`evt-console__line evt-console__line--${ev.type}`}>
            <span className="evt-console__ts">{ev.ts}</span>
            <span className={`evt-console__tag evt-console__tag--${ev.type}`}>{ev.type}</span>
            <code className="evt-console__data">{ev.data}</code>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
