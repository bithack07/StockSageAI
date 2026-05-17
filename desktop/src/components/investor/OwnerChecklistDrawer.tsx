import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api';
import { GuideLink } from '../ui/GuideLink';

type Props = {
  symbol: string;
  open: boolean;
  onClose: () => void;
};

const ITEMS = [
  { key: 'understand_business', label: 'I understand how this business makes money' },
  { key: 'circle_of_competence', label: 'Within my circle of competence' },
  { key: 'comfortable_10y', label: 'Comfortable holding 10+ years' },
] as const;

export function OwnerChecklistDrawer({ symbol, open, onClose }: Props) {
  const qc = useQueryClient();
  const [checklist, setChecklist] = useState<Record<string, unknown>>({});

  const { data } = useQuery({
    queryKey: ['buffett-kit', symbol],
    queryFn: () => apiClient.get(`/investor/stocks/${symbol}/buffett-kit`).then((r) => r.data),
    enabled: open && !!symbol,
  });

  const cl = data?.owner_checklist;

  useEffect(() => {
    if (!open) return;
    setChecklist({});
  }, [open, symbol]);

  const saveChecklist = useMutation({
    mutationFn: () => apiClient.put(`/investor/stocks/${symbol}/checklist`, checklist),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['buffett-kit', symbol] });
      onClose();
    },
  });

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'center',
      }}
    >
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.55)',
          border: 'none',
          cursor: 'pointer',
        }}
      />
      <div
        className="card"
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: 520,
          maxHeight: '85vh',
          overflow: 'auto',
          margin: 16,
          padding: 20,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 4 }}>Owner checklist</h3>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
          Personal due diligence for {symbol.replace(/\.(NS|BO)$/i, '')}
        </p>
        <GuideLink section="owner-investing" label="What is the owner checklist?" />
        <div style={{ display: 'grid', gap: 10, marginTop: 16 }}>
          {ITEMS.map(({ key, label }) => (
            <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={Boolean(checklist[key] ?? cl?.[key])}
                onChange={(e) => setChecklist((p) => ({ ...p, [key]: e.target.checked }))}
              />
              {label}
            </label>
          ))}
          <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Moat (1–5)
            <input className="input-field" type="number" min={1} max={5} style={{ marginTop: 4 }} defaultValue={cl?.moat_rating ?? ''} onChange={(e) => setChecklist((p) => ({ ...p, moat_rating: parseInt(e.target.value, 10) || null }))} />
          </label>
          <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Management (1–5)
            <input className="input-field" type="number" min={1} max={5} style={{ marginTop: 4 }} defaultValue={cl?.management_rating ?? ''} onChange={(e) => setChecklist((p) => ({ ...p, management_rating: parseInt(e.target.value, 10) || null }))} />
          </label>
          <textarea className="input-field" placeholder="Notes…" rows={3} defaultValue={cl?.notes ?? ''} onChange={(e) => setChecklist((p) => ({ ...p, notes: e.target.value }))} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => saveChecklist.mutate()} disabled={saveChecklist.isPending}>{saveChecklist.isPending ? 'Saving…' : 'Save checklist'}</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    </div>
  );
}
