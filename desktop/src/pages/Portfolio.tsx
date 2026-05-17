import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { PortfolioInsightsPanel } from '../components/investor/PortfolioInsightsPanel';
import { ValueInvestingPanel } from '../components/investor/ValueInvestingPanel';
import { GuideLink } from '../components/ui/GuideLink';

const FIELDS = ['symbol', 'quantity', 'avg_buy_price'] as const;

export function Portfolio() {
  const qc = useQueryClient();
  const [form, setForm] = useState({ symbol: '', quantity: '', avg_buy_price: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => apiClient.get('/portfolio').then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const addMutation = useMutation({
    mutationFn: () => apiClient.post('/portfolio', {
      symbol: form.symbol.toUpperCase(),
      quantity: parseFloat(form.quantity),
      avg_buy_price: parseFloat(form.avg_buy_price),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['portfolio'] }); setForm({ symbol: '', quantity: '', avg_buy_price: '' }); },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/portfolio/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portfolio'] }),
  });

  const holdings = data?.holdings ?? [];
  const pnlPos = (data?.total_pnl ?? 0) >= 0;

  return (
    <div className="page">
      <PageHeader title="Portfolio" subtitle="Track holdings, allocation, and P&L" />

      <div style={{ marginBottom: 16 }}>
        <GuideLink section="portfolio" label="What do P&L and allocation mean?" />
      </div>

      <PortfolioInsightsPanel />

      {data && (
        <div className="metric-grid">
          <article className="card metric-card">
            <span className="metric-label">Invested</span>
            <span className="metric-value">₹{(data.total_invested ?? 0).toLocaleString('en-IN')}</span>
          </article>
          <article className="card metric-card">
            <span className="metric-label">Current value</span>
            <span className="metric-value">₹{(data.total_current_value ?? 0).toLocaleString('en-IN')}</span>
          </article>
          <article className="card metric-card">
            <span className="metric-label">Total P&L</span>
            <span className="metric-value" style={{ color: pnlPos ? 'var(--green)' : 'var(--red)' }}>
              {pnlPos ? '+' : ''}₹{(data.total_pnl ?? 0).toFixed(2)}
            </span>
            <span className={pnlPos ? 'badge badge-green' : 'badge badge-red'}>
              {(data.total_pnl_pct ?? 0).toFixed(2)}%
            </span>
          </article>
        </div>
      )}

      <div className="card" style={{ marginBottom: 24 }}>
        <p className="section-label">Add holding</p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {FIELDS.map((f) => (
            <input
              key={f}
              className="input-field"
              placeholder={f.replace(/_/g, ' ')}
              value={(form as any)[f]}
              onChange={(e) => setForm((p) => ({ ...p, [f]: e.target.value }))}
              style={{ flex: '1 1 140px' }}
            />
          ))}
          <button type="button" className="btn btn-primary" onClick={() => addMutation.mutate()} disabled={addMutation.isPending || !form.symbol}>
            {addMutation.isPending ? '…' : '+ Add'}
          </button>
        </div>
      </div>

      {isLoading && <LoadingState />}

      {holdings.length > 0 && (
        <div className="card card-flat" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                {['Symbol', 'Qty', 'Avg', 'Current', 'P&L', ''].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {holdings.map((h: any) => (
                <tr key={h.id}>
                  <td className="cell-primary">
                    <Link to={`/stock/${encodeURIComponent(h.symbol)}`} style={{ color: 'var(--accent)' }}>{h.symbol}</Link>
                  </td>
                  <td>{h.quantity}</td>
                  <td>₹{h.avg_buy_price}</td>
                  <td style={{ color: 'var(--text)' }}>₹{h.current_price}</td>
                  <td style={{ fontWeight: 700, color: h.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    {h.pnl >= 0 ? '+' : ''}₹{h.pnl.toFixed(2)} ({h.pnl_pct.toFixed(2)}%)
                  </td>
                  <td>
                    <button type="button" className="btn btn-ghost btn-sm btn-danger" onClick={() => removeMutation.mutate(h.id)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {holdings.length > 0 && (
        <>
          <p className="section-label" style={{ marginTop: 24 }}>Investment theses</p>
          <GuideLink section="owner-investing" label="What is an investment thesis?" />
          {holdings.map((h: any) => (
            <details key={h.id} className="card" style={{ marginBottom: 10 }}>
              <summary style={{ cursor: 'pointer', fontWeight: 700, color: 'var(--text)' }}>{h.symbol}</summary>
              <ValueInvestingPanel symbol={h.symbol} holdingId={h.id} thesisOnly />
            </details>
          ))}
        </>
      )}

      {!isLoading && holdings.length === 0 && (
        <EmptyState icon="◑" title="No holdings yet" description="Add your first position above to track performance." />
      )}
    </div>
  );
}
