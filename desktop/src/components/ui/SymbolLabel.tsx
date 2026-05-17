import type { SymbolMeta } from '../../utils/symbolDisplay';
import { displaySymbol, exchangeBadge } from '../../utils/symbolDisplay';

type Props = {
  item: SymbolMeta | string;
  showName?: boolean;
  size?: 'sm' | 'md';
};

export function SymbolLabel({ item, showName = true, size = 'md' }: Props) {
  const exchange = typeof item === 'string' ? exchangeBadge({ symbol: item } as SymbolMeta) : exchangeBadge(item);
  const short = displaySymbol(item);
  const company = typeof item !== 'string' ? item.company_name : null;
  const canon = typeof item !== 'string' ? (item.canonical_symbol ?? item.symbol) : item;

  return (
    <div>
      {showName && company && company !== short ? (
        <div style={{ fontSize: size === 'md' ? 15 : 13, fontWeight: 700, color: 'var(--text)' }}>
          {company}
        </div>
      ) : null}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: showName && company ? 4 : 0 }}>
        <span style={{ fontSize: size === 'md' ? 14 : 12, fontWeight: 700, color: 'var(--accent)' }}>{short}</span>
        <span className="badge badge-accent" style={{ fontSize: 10, padding: '2px 8px' }}>{exchange}</span>
      </div>
      {typeof item !== 'string' && canon && (
        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 0' }}>
          Same company on {exchange} — data tied to {canon}
        </p>
      )}
    </div>
  );
}
