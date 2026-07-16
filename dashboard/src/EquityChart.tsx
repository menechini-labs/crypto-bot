interface Props {
  points: number[];
  width?: number;
  height?: number;
}

// Grafico de area SVG puro (sem libs). Recebe a serie de equity.
export default function EquityChart({ points, width = 1000, height = 220 }: Props) {
  if (points.length < 2) {
    return <p className="empty">Sem dados de equity ainda.</p>;
  }

  const pad = 16;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const stepX = (width - pad * 2) / (points.length - 1);

  const coords = points.map((p, i) => {
    const x = pad + i * stepX;
    const y = pad + (1 - (p - min) / span) * (height - pad * 2);
    return [x, y] as const;
  });

  const linePath = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

  const areaPath =
    `M${coords[0][0].toFixed(1)},${(height - pad).toFixed(1)} ` +
    coords.map(([x, y]) => `L${x.toFixed(1)},${y.toFixed(1)}`).join(" ") +
    ` L${coords[coords.length - 1][0].toFixed(1)},${(height - pad).toFixed(1)} Z`;

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#00d2ff" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#00d2ff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line className="axis" x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} />
      <path className="area" d={areaPath} />
      <path className="line" d={linePath} />
    </svg>
  );
}
