import { useCountUp } from "./useCountUp";

interface Props {
  label: string;
  value: string; // formatted display value e.g. "$1,234.56"
  valueRaw?: number; // raw number for count-up animation (optional)
  sub?: string;
  tone?: "pos" | "neg" | "neutral";
}

export default function StatCard({ label, value, valueRaw, sub, tone = "neutral" }: Props) {
  const toneClass = tone === "pos" ? "pos" : tone === "neg" ? "neg" : "";

  // Count-up animation para valores numéricos
  const animated = useCountUp(valueRaw ?? 0, 800, valueRaw !== undefined);
  const displayValue =
    valueRaw !== undefined
      ? value.replace(/[\d,.-]+/, (_match) => {
          // preserva sinal + prefixo $ e formatação
          const fmt = animated.toLocaleString("en-US", {
            maximumFractionDigits: 2,
            minimumFractionDigits: 2,
          });
          const prefix = value.startsWith("$") ? "$" : "";
          const sign = valueRaw >= 0 && value.startsWith("+") ? "+" : "";
          return `${sign}${prefix}${fmt}`;
        })
      : value;

  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className={`value ${toneClass} count-up`} key={valueRaw}>
        {displayValue}
      </div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}
