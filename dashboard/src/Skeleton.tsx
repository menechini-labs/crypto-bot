/**
 * Skeleton screens — shimmer placeholders for loading states.
 * Substitui "Carregando..." textual por feedback visual moderno.
 */

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  style?: React.CSSProperties;
}

export function Skeleton({ width = "100%", height = 16, borderRadius = 6, style }: SkeletonProps) {
  return (
    <div
      className="skeleton"
      style={{
        width,
        height,
        borderRadius,
        ...style,
      }}
      aria-hidden="true"
    />
  );
}

/** Card skeleton — placeholder para StatCard */
export function StatCardSkeleton() {
  return (
    <div className="card skeleton-card">
      <div className="label">
        <Skeleton width={60} height={10} />
      </div>
      <div className="value" style={{ marginTop: 8 }}>
        <Skeleton width={100} height={28} />
      </div>
      <div className="sub" style={{ marginTop: 8 }}>
        <Skeleton width={50} height={8} />
      </div>
    </div>
  );
}

/** Panel skeleton — placeholder para um painel inteiro */
const SKELETON_WIDTHS = ["85%","60%","78%","92%","55%","68%","80%"];

export function PanelSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="panel skeleton-panel">
      <h2>
        <Skeleton width={120} height={10} />
      </h2>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          width={SKELETON_WIDTHS[i % SKELETON_WIDTHS.length]}
          height={12}
          style={{ marginBottom: 10 }}
        />
      ))}
      <Skeleton width="100%" height={180} borderRadius={8} style={{ marginTop: 8 }} />
    </div>
  );
}
