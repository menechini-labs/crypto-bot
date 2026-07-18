import { useState } from "react";
import { apiGet, apiPost } from "./api";
import type { SignalScoreResponse, BlendedScoreResponse } from "./types";

/* Gera uma serie sintetica de closes para teste rapido */
function genSeries(n: number, kind: "uptrend" | "downtrend" | "lateral"): number[] {
  const out: number[] = [];
  let p = 100;
  for (let i = 0; i < n; i++) {
    if (kind === "uptrend") p += 0.5 + Math.sin(i / 5) * 0.2;
    else if (kind === "downtrend") p -= 0.5 + Math.sin(i / 5) * 0.2;
    else p += Math.sin(i / 3) * 1.5;
    out.push(Number(p.toFixed(2)));
  }
  return out;
}

/* Componente de barra segmentada (instrumento) */
function SegmentBar({ label, value }: { label: string; value: number }) {
  const seg = 12;
  const lit = Math.round(Math.max(0, Math.min(1, value)) * seg);
  const tone = value >= 0.66 ? "ok" : value >= 0.4 ? "warn" : "rej";
  return (
    <div className={`seg seg--${tone}`}>
      <span className="seg__label">{label}</span>
      <div className="seg__track">
        {Array.from({ length: seg }).map((_, i) => (
          <span key={i} className={`seg__cell ${i < lit ? "is-on" : ""}`} />
        ))}
      </div>
      <span className="seg__val">{value.toFixed(2)}</span>
    </div>
  );
}

/* Medidor radial SVG do composite */
function Gauge({ value, tone }: { value: number; tone: "ok" | "warn" | "rej" }) {
  const R = 52;
  const C = 2 * Math.PI * R;
  const v = Math.max(0, Math.min(1, value));
  const dash = C * v;
  const color = tone === "ok" ? "#3ddc97" : tone === "warn" ? "#ffb000" : "#ff4d6d";
  return (
    <svg className="gauge" viewBox="0 0 140 140" role="img" aria-label="composite score">
      <circle cx="70" cy="70" r={R} className="gauge__bg" />
      <circle
        cx="70"
        cy="70"
        r={R}
        className="gauge__fg"
        stroke={color}
        strokeDasharray={`${dash} ${C}`}
        transform="rotate(-90 70 70)"
      />
      <text x="70" y="64" className="gauge__num" fill={color}>
        {(v * 100).toFixed(0)}
      </text>
      <text x="70" y="84" className="gauge__unit">
        COMPOSITE
      </text>
    </svg>
  );
}

export default function ScorePanel() {
  const [closes, setCloses] = useState<string>("");
  const [signal, setSignal] = useState<"buy" | "sell" | "hold">("buy");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SignalScoreResponse | null>(null);
  const [blended, setBlended] = useState<BlendedScoreResponse | null>(null);
  const [reveal, setReveal] = useState(false);

  async function runScore() {
    setLoading(true);
    setError(null);
    setReveal(false);
    try {
      const parsed = closes
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n));
      if (parsed.length < 20) {
        setError("Informe ao menos 20 valores de closes separados por vírgula.");
        setLoading(false);
        return;
      }
      const j = await apiPost<SignalScoreResponse>("/api/score", {
        closes: parsed,
        signal,
        has_position: false,
      });
      setResult(j);
      requestAnimationFrame(() => setReveal(true));
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro");
    } finally {
      setLoading(false);
    }
  }

  async function runBlended() {
    setLoading(true);
    setError(null);
    setReveal(false);
    try {
      const parsed = closes
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n));
      if (parsed.length < 20) {
        setError("Informe ao menos 20 valores de closes separados por vírgula.");
        setLoading(false);
        return;
      }
      const j = await apiPost<BlendedScoreResponse>('/api/score/blended', {
        closes: parsed,
        signal,
        has_position: false,
      });
      setBlended(j);
      requestAnimationFrame(() => setReveal(true));
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro");
    } finally {
      setLoading(false);
    }
  }

  async function runLLM() {
    setLoading(true);
    setError(null);
    setReveal(false);
    try {
      const parsed = closes
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n));
      if (parsed.length < 20) {
        setError("Informe ao menos 20 valores de closes separados por vírgula.");
        setLoading(false);
        return;
      }
      const j = await apiPost<SignalScoreResponse & { llm_enabled: boolean }>("/api/llm-signal", {
        closes: parsed,
        has_position: false,
        signal,
      });
      setResult(j);
      setSignal(j.signal as "buy" | "sell" | "hold");
      requestAnimationFrame(() => setReveal(true));
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro");
    } finally {
      setLoading(false);
    }
  }

  const comp = result?.score?.details?.components;
  const conf = result?.score?.confidence ?? 0;
  const risk = result?.score?.risk_score ?? 0;
  const composite = result?.score?.composite ?? 0;
  const tone: "ok" | "warn" | "rej" = composite >= 0.66 ? "ok" : composite >= 0.4 ? "warn" : "rej";
  const verdict = conf >= 0.4 && risk >= 0.5 ? "EXECUTAR" : "REJEITAR";

  async function fetchReal() {
    setLoading(true);
    setError(null);
    try {
      const j = await apiGet<{ closes: number[] }>(
        "/api/market/closes?symbol=BTCUSDT&timeframe=1h&limit=100",
      );
      if (Array.isArray(j.closes) && j.closes.length >= 20) {
        setCloses(j.closes.join(","));
      } else {
        setError("Sem dados de mercado disponiveis.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "erro ao buscar mercado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel sig">
      <header className="sig__head">
        <div>
          <p className="sig__kicker">SIGNAL SCORING ENGINE</p>
          <h2 className="sig__title">Leitura de Sinal</h2>
        </div>
        <div className={`sig__badge sig__badge--${signal}`}>{signal.toUpperCase()}</div>
      </header>

      <p className="sig__hint">
        Cole uma série de closes (CSV) ou busque dados reais da Binance. O motor aplica{" "}
        <code>score_signal</code> + <code>should_execute</code> (confiança ≥ 0.40, risco ≥ 0.50).
      </p>

      <p className="sig__hint sig__hint--real">
        <button type="button" className="sig__real" onClick={fetchReal} disabled={loading}>
          ⬇ BTCUSDT real (1h, 100 closes)
        </button>
      </p>

      <div className="sig__grid">
        {/* coluna de controle */}
        <div className="sig__ctrl">
          <div className="sig__row">
            <label className="sig__lbl">SINAL</label>
            <select
              className="sig__select"
              value={signal}
              onChange={(e) => setSignal(e.target.value as "buy" | "sell" | "hold")}
            >
              <option value="buy">BUY</option>
              <option value="sell">SELL</option>
              <option value="hold">HOLD</option>
            </select>
          </div>
          <div className="sig__gen">
            <button type="button" onClick={() => setCloses(genSeries(60, "uptrend").join(","))}>
              ▲ uptrend
            </button>
            <button type="button" onClick={() => setCloses(genSeries(60, "lateral").join(","))}>
              ▬ lateral
            </button>
            <button type="button" onClick={() => setCloses(genSeries(60, "downtrend").join(","))}>
              ▼ downtrend
            </button>
            <button type="button" className="sig__llm" onClick={runLLM} disabled={loading}>
              ⟁ LLM
            </button>
            <button type="button" className="sig__blended" onClick={runBlended} disabled={loading}>
              ⚖ BLENDED
            </button>
          </div>
          <textarea
            className="sig__ta"
            rows={4}
            placeholder="100,101,102,103,... (>= 20 valores)"
            value={closes}
            onChange={(e) => setCloses(e.target.value)}
          />
          <button type="button" className="sig__run" onClick={runScore} disabled={loading}>
            {loading ? "CALCULANDO…" : "◆ CALCULAR SCORE"}
          </button>
          {error && <p className="sig__err">{error}</p>}
        </div>

        {/* coluna de leitura */}
        <div className={`sig__read ${reveal ? "is-reveal" : ""}`}>
          {blended && !result && (
            <div className="sig__blended-result">
              <h3 className="sig__blended-title">⚖ Blended Score c/ Template Risk</h3>
              <div className="sig__blended-metrics">
                <div>
                  <small>Signal</small>
                  <b>{blended.signal.toUpperCase()}</b>
                </div>
                <div>
                  <small>Score raw</small>
                  <b>{(blended.score?.composite ?? 0 * 100).toFixed(0)}%</b>
                </div>
                <div>
                  <small>Blended</small>
                  <b>{(blended.blended?.composite ?? 0 * 100).toFixed(0)}%</b>
                </div>
                <div>
                  <small>Template Risk</small>
                  <b>{(blended.template_risk?.overall_risk ?? 0 * 100).toFixed(0)}%</b>
                </div>
              </div>
              <p className="sig__explain">{blended.explanation}</p>
            </div>
          )}
          {!result && !blended && (
            <div className="sig__empty">
              <span className="sig__empty-tick">+</span>
              <p>Aguardando sinal…</p>
            </div>
          )}
          {result && (
            <>
              <div className="sig__top">
                <Gauge value={composite} tone={tone} />
                <div className="sig__verdict">
                  <span
                    className={`sig__stamp sig__stamp--${verdict === "EXECUTAR" ? "go" : "no"}`}
                  >
                    {verdict}
                  </span>
                  <div className="sig__metrics">
                    <div>
                      <small>CONFIANÇA</small>
                      <b>{(conf * 100).toFixed(0)}%</b>
                    </div>
                    <div>
                      <small>RISCO</small>
                      <b>{(risk * 100).toFixed(0)}%</b>
                    </div>
                    <div>
                      <small>REGIME</small>
                      <b>{result.score.details.regime}</b>
                    </div>
                  </div>
                </div>
              </div>

              {comp && (
                <div className="sig__bars">
                  <SegmentBar label="trend" value={comp.trend} />
                  <SegmentBar label="momentum" value={comp.momentum} />
                  <SegmentBar label="volatility" value={comp.volatility} />
                  <SegmentBar label="risk/rew" value={comp.risk_reward} />
                  <SegmentBar label="regime" value={comp.regime} />
                </div>
              )}

              <p className="sig__explain">{result.explanation}</p>
              {!result.llm_enabled && (
                <p className="sig__note">
                  LLM desativado (sem ENABLE_LLM / LLM_API_KEY) — fallback hold.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
