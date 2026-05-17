import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { SymbolLabel } from '../components/ui/SymbolLabel';
import { canonicalForNav } from '../utils/symbolDisplay';

export function Search() {
  const [q, setQ] = useState('');
  const navigate = useNavigate();

  const { data, isFetching, isError } = useQuery({
    queryKey: ['search', q],
    queryFn: () => apiClient.get('/stocks/search', { params: { q } }).then((r) => r.data),
    enabled: q.length >= 2,
    staleTime: 60_000,
  });

  const results = data ?? [];

  return (
    <div className="page page-narrow">
      <PageHeader title="Search" subtitle="One result per company — INFY and INFY.NS merged" />

      <div className="search-wrap">
        <span className="search-icon">⌕</span>
        <input
          className="input-field"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Company or symbol (e.g. Infosys, INFY)"
          autoFocus
        />
      </div>

      {isFetching && <LoadingState label="Searching…" />}

      {q.length >= 2 && !isFetching && results.length === 0 && !isError && (
        <EmptyState icon="⌕" title="No matches" description={`No stocks found for "${q}".`} />
      )}

      {results.length > 0 && (
        <div className="card card-flat" style={{ padding: 0, overflow: 'hidden' }}>
          {results.map((item: any) => (
            <button
              key={item.canonical_symbol ?? item.symbol}
              type="button"
              className="list-row-btn"
              onClick={() => navigate(`/stock/${canonicalForNav(item)}`)}
            >
              <SymbolLabel item={item} size="sm" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
