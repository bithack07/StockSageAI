import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';

const CONDITIONS = ['price_above', 'price_below', 'rsi_above', 'rsi_below', 'macd_crossover'];

export function Alerts() {
  const qc = useQueryClient();
  const [form, setForm] = useState({ symbol: '', condition: 'price_above', threshold: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => apiClient.get('/alerts').then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () => apiClient.post('/alerts', {
      symbol: form.symbol.toUpperCase(),
      condition: form.condition,
      threshold: parseFloat(form.threshold) || undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['alerts'] }); setForm({ symbol: '', condition: 'price_above', threshold: '' }); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/alerts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });

  const alerts = data ?? [];

  return (
    <div className="page page-narrow">
      <PageHeader title="Alerts" subtitle="Price and indicator notifications" />

      <div className="card" style={{ marginBottom: 24 }}>
        <p className="section-label">New alert</p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input className="input-field" value={form.symbol} onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value }))} placeholder="Symbol" style={{ flex: 1, minWidth: 120 }} />
          <select className="input-field" value={form.condition} onChange={(e) => setForm((f) => ({ ...f, condition: e.target.value }))} style={{ flex: 1, minWidth: 150 }}>
            {CONDITIONS.map((c) => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
          </select>
          <input className="input-field" value={form.threshold} onChange={(e) => setForm((f) => ({ ...f, threshold: e.target.value }))} placeholder="Threshold" type="number" style={{ width: 110 }} />
          <button type="button" className="btn btn-primary" onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !form.symbol}>
            Create
          </button>
        </div>
      </div>

      {isLoading && <LoadingState />}

      {alerts.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {alerts.map((a: any) => (
            <article key={a.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', opacity: a.is_active ? 1 : 0.5 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 700, fontSize: 16 }}>{a.symbol}</span>
                <span className="badge badge-accent">{a.condition.replace(/_/g, ' ')}</span>
                {a.threshold != null && <span style={{ color: 'var(--text-2)' }}>@ ₹{a.threshold}</span>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className={`status-dot status-dot--${a.is_active ? 'open' : 'closed'}`} />
                {a.is_active && (
                  <button type="button" className="btn btn-ghost btn-sm btn-danger" onClick={() => deleteMutation.mutate(a.id)}>Delete</button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {!isLoading && alerts.length === 0 && (
        <EmptyState icon="◬" title="No alerts" description="Create alerts to get notified when price or RSI conditions are met." />
      )}
    </div>
  );
}
