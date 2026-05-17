import { useQuery } from '@tanstack/react-query';
import { portfolio } from '@/api/client';
import { symbolsMatch } from '@/lib/matchSymbol';

interface Holding {
  id: string;
  symbol: string;
}

interface PortfolioData {
  holdings?: Holding[];
}

/** Portfolio holding for a stock symbol, if the user owns it. */
export function useHoldingForSymbol(symbol: string | null | undefined) {
  const { data } = useQuery({
    queryKey: ['portfolio'],
    queryFn: () => portfolio.get().then((r) => r.data as PortfolioData),
    staleTime: 5 * 60_000,
  });

  if (!symbol) return null;
  return (data?.holdings ?? []).find((h) => symbolsMatch(h.symbol, symbol)) ?? null;
}
