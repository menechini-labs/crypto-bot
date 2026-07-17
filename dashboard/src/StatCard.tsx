interface Props {
  label: string;
  value: string;
  sub?: string;
  tone?: "pos" | "neg" | "neutral";
}

export default function StatCard({ label, value, sub, tone = "neutral" }: Props) {
  const toneClass = tone === "pos" ? "pos" : tone === "neg" ? "neg" : "";
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className={`value ${toneClass}`}>{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}
