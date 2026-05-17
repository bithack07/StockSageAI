/** Display helpers for canonical NSE/BSE symbols (matches backend symbols service). */

export type SymbolMeta = {
  symbol?: string;
  canonical_symbol?: string;
  base_ticker?: string;
  exchange?: string;
  company_name?: string;
  short_label?: string;
  label?: string;
};

export function displaySymbol(item: SymbolMeta | string): string {
  if (typeof item === 'string') {
    return item.replace(/\.(NS|BO)$/i, '');
  }
  return item.short_label ?? item.base_ticker ?? item.symbol?.replace(/\.(NS|BO)$/i, '') ?? '—';
}

export function displayTitle(item: SymbolMeta): string {
  return item.label ?? item.company_name ?? displaySymbol(item);
}

export function canonicalForNav(item: SymbolMeta | string): string {
  if (typeof item === 'string') return item;
  return item.canonical_symbol ?? item.symbol ?? '';
}

export function exchangeBadge(item: SymbolMeta | string): string {
  if (typeof item === 'string') {
    return item.endsWith('.BO') ? 'BSE' : 'NSE';
  }
  return item.exchange ?? (item.symbol?.endsWith('.BO') ? 'BSE' : 'NSE');
}
