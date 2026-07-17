interface Props {
  points: number[];
  width?: number;
  height?: number;
}

/**
 * Mini sparkline inline SVG (260x56) – estilo StrategyFactory.
 * Usa cor verde/vermelho baseado no último ponto vs primeiro.
 */
export default function Sparkline({ points, width = 260, height = 56 }: Props) {
  if (points.length < 2) {
    return <span className="spark__skel" />;
  }

  const pad = 4;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const n = points.length - 1;
  const endUp = points[points.length - 1] >= points[0];
  const stroke = endUp ? "#22c55e" : "#ef4444";

  const path = points
    .map((p, i) => {
      const x = pad + (i / n) * (width - pad * 2);
      const y = pad + (1 - (p - min) / range) * (height - pad * 2);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      className="spark"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      role="img"
      aria-label="Equity preview"
    >
      <title>Equity preview</title>
      <path d={path} fill="none" stroke={stroke} strokeWidth={1.5} strokeLinecap="round" />
    </svg>
  );
}
