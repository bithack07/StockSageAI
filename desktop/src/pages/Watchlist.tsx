import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { SymbolLabel } from '../components/ui/SymbolLabel';
import { canonicalForNav } from '../utils/symbolDisplay';

const DIR_STYLE: Record<string, string> = {
  BULLISH: 'badge-green',
  BEARISH: 'badge-red',
  NEUTRAL: 'badge-yellow',
};

export function Watchlist() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [sym, setSym] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => apiClient.get('/watchlist').then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: () => apiClient.post('/watchlist', { symbol: sym.trim() }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['watchlist'] }); setSym(''); },
  });

  const refreshMutation = useMutation({
    mutationFn: () => apiClient.post('/watchlist/refresh-preanalysis'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/watchlist/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const items = data ?? [];

  return (
    <div className="page page-narrow">
      <PageHeader
        title="Watchlist"
        subtitle="Favorites with pre-computed AI analysis — one symbol per company (NSE .NS)"
        action={
          items.length > 0 ? (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
            >
              {refreshMutation.isPending ? 'Refreshing…' : 'Refresh all AI'}
            </button>
          ) : undefined
        }
      />

      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.5 }}>
        Tip: type <strong>INFY</strong> or <strong>INFY.NS</strong> — both map to Infosys on NSE. We store one canonical ticker to avoid duplicates.
      </p>

      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input
          className="input-field"
          value={sym}
          onChange={(e) => setSym(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sym.trim() && addMutation.mutate()}
          placeholder="Company or symbol (e.g. Infosys, INFY)"
          style={{ flex: 1 }}
        />
        <button type="button" className="btn btn-primary" onClick={() => addMutation.mutate()} disabled={!sym.trim() || addMutation.isPending}>
          + Add
        </button>
      </div>

      {isLoading && <LoadingState />}

      {items.length > 0 && (
        <div className="card card-flat" style={{ padding: 0 }}>
          {items.map((item: any) => {
            const preview = item.preview;
            const dir = preview?.direction;
            return (
              <div key={item.id} className="list-row">
                <button
                  type="button"
                  className="list-row-btn"
                  style={{ flex: 1, alignItems: 'flex-start' }}
                  onClick={() => navigate(`/stock/${canonicalForNav(item)}`)}
                >
                  <SymbolLabel item={item} />
                  <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    {item.price != null && (
                      <span style={{ fontSize: 13, fontWeight: 600 }}>₹{Number(item.price).toLocaleString('en-IN')}</span>
                    )}
                    {dir && (
                      <span className={DIR_STYLE[dir] ?? 'badge'} style={{ fontSize: 11 }}>
                        {dir} · {preview.confidence_pct ?? '—'}%
                      </span>
                    )}
                    {preview?.status === 'pending' && (
                      <span className="badge badge-accent" style={{ fontSize: 10 }}>Analysis queued…</span>
                    )}
                    {preview?.analyzed_at && (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        Updated {new Date(preview.analyzed_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                      </span>
                    )}
                  </div>
                </button>
                <button type="button" className="btn btn-ghost btn-sm btn-danger" style={{ marginRight: 12 }} onClick={() => removeMutation.mutate(item.id)}>
                  Remove
                </button>
              </div>
            );
          })}
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <EmptyState icon="◉" title="Watchlist is empty" description="Add favorites — we pre-run AI analysis so results are ready when you open a stock." />
      )}
    </div>
  );
}
