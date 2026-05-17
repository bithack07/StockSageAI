import { useQuery } from '@tanstack/react-query';
import { stocks } from '@/api/client';

export function useQuote(symbol: string | null) {
  return useQuery({
    queryKey: ['quote', symbol],
    queryFn: () => stocks.quote(symbol!).then((r) => r.data),
    enabled: !!symbol,
    refetchInterval: 60_000,  // refresh every 60 seconds
    staleTime: 30_000,
  });
}
