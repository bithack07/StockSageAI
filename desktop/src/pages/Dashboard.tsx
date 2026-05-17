import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState, MetricSkeleton } from '../components/ui/LoadingState';
import { MarketHeroIllustration } from '../components/ui/MarketHeroIllustration';
import { GuideLink } from '../components/ui/GuideLink';

const QUICK = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS'];

export function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ['market_overview'],
    queryFn: () => apiClient.get('/market/overview').then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const { data: fresh } = await apiClient.get('/market/overview', { params: { force: true } });
      queryClient.setQueryData(['market_overview'], fresh);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="page page-wide">
      <section className="dashboard-hero" aria-hidden={false}>
        <div className="dashboard-hero-text">
          <p className="section-label" style={{ marginBottom: 8 }}>StockSage AI</p>
          <h2 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, marginBottom: 8 }}>
            Your market command center
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-2)', maxWidth: 420 }}>
            Live indices, multi-agent analysis, and ML-powered forecasts for NSE & BSE.
          </p>
        </div>
        <MarketHeroIllustration className="dashboard-hero-art" />
      </section>

      <PageHeader
        title="Market Overview"
        subtitle="Live Nifty indices · refreshes every 5 minutes"
        action={
          data?.market_status && (
            <span className={`badge ${data.market_status === 'OPEN' ? 'badge-green' : data.market_status === 'PREOPEN' ? 'badge-yellow' : 'badge-accent'}`}>
              <span className={`status-dot status-dot--${data.market_status === 'OPEN' ? 'open' : 'closed'}`} />
              NSE {data.market_status}{data.session ? ` · ${data.session}` : ''}
            </span>
          )
        }
      />

      <div style={{ marginBottom: 16 }}>
        <GuideLink section="indices" label="What do these indices mean?" />
      </div>

      {isLoading && <MetricSkeleton count={4} />}
      {isError && (
        <EmptyState
          icon="⚠"
          title="Could not load market data"
          description="Check that the backend is running, then try again."
        />
      )}

      {data?.indices && (
        <>
          <p className="section-label">Indices</p>
          <div className="metric-grid">
            {data.indices.map((idx: any) => {
              const pos = (idx.change_pct ?? 0) >= 0;
              return (
                <article key={idx.symbol} className="card metric-card">
                  <span className="metric-label">{idx.name?.replace(/_/g, ' ')}</span>
                  <span className="metric-value">
                    {idx.price != null ? `₹${idx.price.toLocaleString('en-IN')}` : '—'}
                  </span>
                  <span className={pos ? 'badge badge-green' : 'badge badge-red'}>
                    {pos ? '+' : ''}{idx.change_pct?.toFixed(2) ?? '—'}%
                  </span>
                  {idx.rsi != null && <span className="metric-sub">RSI {idx.rsi}</span>}
                </article>
              );
            })}
          </div>
        </>
      )}

      <p className="section-label">Quick analysis</p>
      <div className="chip-row" style={{ marginBottom: 32 }}>
        {QUICK.map((sym) => (
          <button key={sym} type="button" className="chip" onClick={() => navigate(`/stock/${sym}`)}>
            {sym.replace('.NS', '')}
          </button>
        ))}
      </div>

      {!isLoading && !isError && (
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing…' : 'Refresh data'}
        </button>
      )}
    </div>
  );
}
