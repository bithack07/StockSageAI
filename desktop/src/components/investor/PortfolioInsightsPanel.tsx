import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api';

export function PortfolioInsightsPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['portfolio-insights'],
    queryFn: () => apiClient.get('/investor/portfolio/insights').then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const { data: earnings } = useQuery({
    queryKey: ['earnings-calendar'],
    queryFn: () => apiClient.get('/investor/watchlist/earnings-calendar').then((r) => r.data),
    staleTime: 30 * 60_000,
  });

  if (isLoading) return null;
  const hasContent = data?.sectors?.length || data?.warnings?.length || earnings?.events?.length;
  if (!hasContent) return null;

  return (
    <div style={{ marginBottom: 24 }}>
      <p className="section-label">Portfolio concentration · India</p>

      {data.sectors?.length > 0 && (
        <div className="card" style={{ marginBottom: 14 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Sector allocation</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.sectors.map((s: any) => (
              <div key={s.sector} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ flex: 1, height: 8, background: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(s.pct, 100)}%`, height: '100%', background: 'var(--accent)', borderRadius: 4 }} />
                </div>
                <span style={{ fontSize: 12, color: 'var(--text-2)', minWidth: 100 }}>{s.sector}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)' }}>{s.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.warnings?.length > 0 && (
        <div className="card" style={{ marginBottom: 14, borderColor: 'rgba(245,158,11,0.35)' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: 'var(--yellow)' }}>Diversification notes</h3>
          {data.warnings.map((w: string, i: number) => (
            <p key={i} style={{ fontSize: 12, color: 'var(--text-2)', marginBottom: 6 }}>• {w}</p>
          ))}
        </div>
      )}

      {data.holdings_detail?.length > 0 && data.net_worth_inr && (
        <div className="card card-flat" style={{ marginBottom: 14, padding: 12 }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>% of net worth</h3>
          {data.holdings_detail
            .filter((h: any) => h.pct_of_net_worth != null)
            .map((h: any) => (
              <p key={h.symbol} style={{ fontSize: 12, color: 'var(--text-2)' }}>
                {h.symbol}: <strong style={{ color: 'var(--text)' }}>{h.pct_of_net_worth}%</strong> of ₹{Number(data.net_worth_inr).toLocaleString('en-IN')}
              </p>
            ))}
        </div>
      )}

      {earnings?.events?.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Earnings & AR reminders (watchlist)</h3>
          {earnings.events.slice(0, 8).map((ev: any, i: number) => (
            <div key={i} style={{ marginBottom: 10, paddingBottom: 10, borderBottom: i < 7 ? '1px solid var(--border)' : 'none' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{ev.title}</span>
                <span className="badge badge-accent">{ev.event_date}</span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{ev.reminder}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
