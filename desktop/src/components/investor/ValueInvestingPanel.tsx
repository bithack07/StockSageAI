import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api';
import { OwnerChecklistDrawer } from './OwnerChecklistDrawer';
import { GuideLink } from '../ui/GuideLink';

type Props = { symbol: string; holdingId?: string; compact?: boolean; thesisOnly?: boolean };

export function ValueInvestingPanel({ symbol, holdingId, compact, thesisOnly }: Props) {
  const qc = useQueryClient();
  const [netWorth, setNetWorth] = useState('');
  const [fdRate, setFdRate] = useState('7');
  const [thesis, setThesis] = useState<Record<string, string>>({});
  const [checklistOpen, setChecklistOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['buffett-kit', symbol],
    queryFn: () => apiClient.get(`/investor/stocks/${symbol}/buffett-kit`).then((r) => r.data),
    enabled: !!symbol && !thesisOnly,
    staleTime: 10 * 60_000,
  });

  const { data: profile } = useQuery({
    queryKey: ['investor-profile'],
    queryFn: () => apiClient.get('/investor/profile').then((r) => r.data),
  });

  const { data: thesisData } = useQuery({
    queryKey: ['thesis', holdingId],
    queryFn: () => apiClient.get(`/investor/holdings/${holdingId}/thesis`).then((r) => r.data),
    enabled: !!holdingId,
  });

  const saveProfile = useMutation({
    mutationFn: () => apiClient.patch('/investor/profile', {
      net_worth_inr: netWorth ? parseFloat(netWorth) : undefined,
      annual_fd_rate_pct: fdRate ? parseFloat(fdRate) : undefined,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['investor-profile', 'buffett-kit', symbol] }),
  });

  const saveThesis = useMutation({
    mutationFn: () => apiClient.put(`/investor/holdings/${holdingId}/thesis`, thesis),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['thesis', holdingId] }),
  });

  if (thesisOnly && holdingId) {
    return (
      <div style={{ padding: '12px 0' }}>
        {[
          { key: 'thesis_text', label: 'Why I bought', rows: 2 },
          { key: 'moat_notes', label: 'Moat', rows: 2 },
          { key: 'management_notes', label: 'Management', rows: 2 },
          { key: 'ten_year_thesis', label: '10-year thesis', rows: 2 },
        ].map(({ key, label, rows }) => (
          <label key={key} style={{ display: 'block', marginBottom: 8 }}>
            <span className="section-label" style={{ margin: '0 0 4px' }}>{label}</span>
            <textarea className="input-field" rows={rows} defaultValue={thesisData?.thesis?.[key] ?? ''} onChange={(e) => setThesis((p) => ({ ...p, [key]: e.target.value }))} />
          </label>
        ))}
        <button type="button" className="btn btn-primary btn-sm" onClick={() => saveThesis.mutate()} disabled={saveThesis.isPending}>Save thesis</button>
      </div>
    );
  }

  if (isLoading) return <div className="card"><p style={{ color: 'var(--text-muted)' }}>Loading owner insights…</p></div>;
  if (!data) return null;

  const v = data.valuation;
  const q = data.quality;
  const b = data.benchmark;
  const cl = data.owner_checklist;

  const verdictColor =
    v?.verdict === 'UNDERVALUED' ? 'var(--green)' :
    v?.verdict === 'OVERVALUED' ? 'var(--red)' : 'var(--yellow)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: compact ? 16 : 24 }}>
      <p className="section-label">Owner investing · India (NSE/BSE)</p>

      {/* Intrinsic value */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Intrinsic value band (INR/share)</h3>
        {v?.fair_value_mid != null ? (
          <>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
              <span style={{ fontSize: 28, fontWeight: 800, color: verdictColor }}>{v.verdict?.replace(/_/g, ' ')}</span>
              {v.margin_of_safety_pct != null && (
                <span className="badge badge-accent">MoS {v.margin_of_safety_pct}%</span>
              )}
            </div>
            <div className="metric-grid" style={{ marginBottom: 0 }}>
              <article className="card metric-card card-flat">
                <span className="metric-label">Low</span>
                <span className="metric-value" style={{ fontSize: 18 }}>₹{v.fair_value_low?.toLocaleString('en-IN')}</span>
              </article>
              <article className="card metric-card card-flat">
                <span className="metric-label">Fair (mid)</span>
                <span className="metric-value" style={{ fontSize: 18 }}>₹{v.fair_value_mid?.toLocaleString('en-IN')}</span>
              </article>
              <article className="card metric-card card-flat">
                <span className="metric-label">High</span>
                <span className="metric-value" style={{ fontSize: 18 }}>₹{v.fair_value_high?.toLocaleString('en-IN')}</span>
              </article>
              <article className="card metric-card card-flat">
                <span className="metric-label">Price</span>
                <span className="metric-value" style={{ fontSize: 18 }}>₹{v.current_price?.toLocaleString('en-IN') ?? '—'}</span>
              </article>
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
              DCF/share: {v.dcf_per_share != null ? `₹${v.dcf_per_share}` : 'n/a'} · Earnings fair: {v.earnings_yield_fair_value != null ? `₹${v.earnings_yield_fair_value}` : 'n/a'} (P/E {v.fair_pe_assumed})
            </p>
          </>
        ) : (
          <p style={{ color: 'var(--text-2)', fontSize: 13 }}>{v?.method_notes?.[0] ?? 'Insufficient data'}</p>
        )}
      </div>

      {/* Quality score */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>Quality score</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12 }}>
          <span style={{ fontSize: 36, fontWeight: 900, color: 'var(--accent)' }}>{q?.quality_score ?? '—'}</span>
          <span className="badge badge-green">Grade {q?.grade ?? '—'}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {q?.components?.map((c: any) => (
            <div key={c.factor} style={{ fontSize: 12, color: 'var(--text-2)', display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <span>{c.factor}</span>
              <span style={{ color: 'var(--text)', fontWeight: 600 }}>{c.score}/100</span>
            </div>
          ))}
        </div>
      </div>

      {/* vs Nifty & FD */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>vs Nifty 50 & FD (1 year)</h3>
        <div className="metric-grid" style={{ marginBottom: 8 }}>
          <article className="card metric-card card-flat">
            <span className="metric-label">Stock</span>
            <span className="metric-value" style={{ fontSize: 16 }}>{b?.stock_return_pct != null ? `${b.stock_return_pct}%` : '—'}</span>
          </article>
          <article className="card metric-card card-flat">
            <span className="metric-label">Nifty 50</span>
            <span className="metric-value" style={{ fontSize: 16 }}>{b?.nifty_50_return_pct != null ? `${b.nifty_50_return_pct}%` : '—'}</span>
          </article>
          <article className="card metric-card card-flat">
            <span className="metric-label">FD (indicative)</span>
            <span className="metric-value" style={{ fontSize: 16 }}>{b?.fd_rate_pct}%</span>
          </article>
        </div>
        {b?.notes?.map((n: string, i: number) => (
          <p key={i} style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 4 }}>• {n}</p>
        ))}
      </div>

      <button
        type="button"
        className="card"
        style={{ width: '100%', textAlign: 'left', cursor: 'pointer', marginBottom: 0 }}
        onClick={() => setChecklistOpen(true)}
      >
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Owner checklist</h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
          {(cl?.understand_business || cl?.circle_of_competence || cl?.comfortable_10y || cl?.moat_rating)
            ? 'Your answers saved · click to review'
            : 'Optional self-assessment · click to open'}
        </p>
      </button>

      <OwnerChecklistDrawer symbol={symbol} open={checklistOpen} onClose={() => setChecklistOpen(false)} />

      {/* Net worth for position sizing */}
      <div className="card card-flat">
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Position sizing (India)</h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
          Net worth in INR — used to show % of wealth per holding on Portfolio.
          {profile?.net_worth_inr != null && ` Current: ₹${Number(profile.net_worth_inr).toLocaleString('en-IN')}`}
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input className="input-field" placeholder="Net worth ₹" defaultValue={profile?.net_worth_inr ?? ''} onChange={(e) => setNetWorth(e.target.value)} style={{ flex: 1, minWidth: 120 }} />
          <input className="input-field" placeholder="FD rate %" defaultValue={profile?.annual_fd_rate_pct ?? 7} onChange={(e) => setFdRate(e.target.value)} style={{ width: 90 }} />
          <button type="button" className="btn btn-primary btn-sm" onClick={() => saveProfile.mutate()}>Save</button>
        </div>
      </div>

      {/* Thesis */}
      {holdingId && (
        <div className="card">
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Investment thesis</h3>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>Why you bought — revisit after every result season.</p>
          <GuideLink section="owner-investing" label="What is an investment thesis?" />
          {[
            { key: 'thesis_text', label: 'Why I bought', rows: 2 },
            { key: 'moat_notes', label: 'Competitive moat', rows: 2 },
            { key: 'management_notes', label: 'Management & governance', rows: 2 },
            { key: 'ten_year_thesis', label: '10-year thesis', rows: 3 },
          ].map(({ key, label, rows }) => (
            <label key={key} style={{ display: 'block', marginBottom: 10 }}>
              <span className="section-label" style={{ margin: '0 0 4px' }}>{label}</span>
              <textarea
                className="input-field"
                rows={rows}
                defaultValue={thesisData?.thesis?.[key] ?? ''}
                onChange={(e) => setThesis((p) => ({ ...p, [key]: e.target.value }))}
              />
            </label>
          ))}
          <button type="button" className="btn btn-primary btn-sm" onClick={() => saveThesis.mutate()} disabled={saveThesis.isPending}>
            Save thesis
          </button>
        </div>
      )}
    </div>
  );
}
