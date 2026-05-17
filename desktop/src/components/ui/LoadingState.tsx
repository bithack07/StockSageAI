export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="loading-center">
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
        <div className="spinner" />
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
      </div>
    </div>
  );
}

export function MetricSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="metric-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card metric-card">
          <div className="skeleton" style={{ height: 12, width: '50%', marginBottom: 10 }} />
          <div className="skeleton" style={{ height: 28, width: '70%' }} />
        </div>
      ))}
    </div>
  );
}
