import { useEffect, useRef } from "react";

interface Props {
  points: number[];
  width?: number;
  height?: number;
}

/**
 * Gráfico de área SVG puro (sem libs).
 * Recebe a série de equity e anima o traço (draw-in).
 * Aplica classe dinâmica para cor da linha (positiva/negativa).
 *
 * A animação usa getTotalLength() para calcular o comprimento real do path,
 * evitando o bug de stroke-dasharray fixo que quebrava com muitos pontos.
 */
export default function EquityChart({ points, width = 1000, height = 220 }: Props) {
  const pathRef = useRef<SVGPathElement>(null);

  if (points.length < 2) {
    return <p className="empty">Sem dados de equity ainda.</p>;
  }

  const pad = 20;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const stepX = (width - pad * 2) / (points.length - 1);

  const coords = points.map((p, i) => {
    const x = pad + i * stepX;
    const y = pad + (1 - (p - min) / span) * (height - pad * 2);
    return { x, y };
  });

  const lastPnl = points[points.length - 1] - points[0];
  const lineClass = lastPnl >= 0 ? "line line-positive" : "line line-negative";

  const linePath = coords
    .map(({ x, y }, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

  const areaPath =
    `M${coords[0].x.toFixed(1)},${(height - pad).toFixed(1)} ` +
    coords.map(({ x, y }) => `L${x.toFixed(1)},${y.toFixed(1)}`).join(" ") +
    ` L${coords[coords.length - 1].x.toFixed(1)},${(height - pad).toFixed(1)} Z`;

  // Animação draw-in: calcula comprimento real do path no DOM e anima
  useEffect(() => {
    const el = pathRef.current;
    // getTotalLength() não existe em jsdom (testes), então guardamos
    if (!el || typeof el.getTotalLength !== "function") return;
    const len = el.getTotalLength();
    el.style.strokeDasharray = String(len);
    el.style.strokeDashoffset = String(len);
    el.style.transition = `stroke-dashoffset 1.4s ease-out 0.4s`;
    // RAF garante que o estado inicial renderizou antes de disparar
    requestAnimationFrame(() => {
      el.style.strokeDashoffset = "0";
    });
  }, [points]);

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Evolução da equity"
    >
      <title>Evolução da equity</title>
      <defs>
        <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line className="axis" x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} />
      <path className="area" d={areaPath} />
      <path ref={pathRef} className={lineClass} d={linePath} />
    </svg>
  );
}
