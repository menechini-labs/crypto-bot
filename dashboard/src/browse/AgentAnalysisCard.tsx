import type { AnalysisResult } from "./types";

interface Props {
  analysis: AnalysisResult;
}

/**
 * Card de exibição da análise do agente.
 * Mostra assessment, métricas e summary com cor semântica.
 */
export default function AgentAnalysisCard({ analysis }: Props) {
  const colors: Record<string, string> = {
    ok: "var(--green)",
    warn: "var(--orange, #f59e0b)",
    alert: "var(--red)",
  };
  const icons: Record<string, string> = {
    ok: "✅",
    warn: "⚠️",
    alert: "⛔",
  };

  return (
    <div
      className="agent-card"
      style={{ borderLeftColor: colors[analysis.assessment] ?? "var(--border)" }}
    >
      <div className="agent-head">
        <span className="agent-icon">{icons[analysis.assessment] ?? "🔍"}</span>
        <span className="agent-label">{analysis.assessment.toUpperCase()}</span>
      </div>
      <p className="agent-summary">{analysis.summary}</p>
      <div className="agent-metrics">
        <div>
          <span className="am-label">Sharpe</span>
          <span className="am-val">{analysis.sharpe.toFixed(2)}</span>
        </div>
        <div>
          <span className="am-label">CAGR</span>
          <span className="am-val">{(analysis.cagr * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="am-label">Max DD</span>
          <span className="am-val">{(analysis.max_dd * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="am-label">Win Rate</span>
          <span className="am-val">{(analysis.win_rate * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
}
