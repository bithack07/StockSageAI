import { useState } from 'react';
import { FlatList, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { stocks, watchlist } from '@/api/client';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { SymbolLabel } from '@/components/ui/SymbolLabel';
import { WatchlistAddButton } from '@/components/watchlist/WatchlistAddButton';
import { canonicalForNav, type SymbolMeta } from '@/lib/symbolDisplay';
import { colors, spacing } from '@/constants/theme';

export default function SearchScreen() {
  const [query, setQuery] = useState('');

  const { data, isFetching } = useQuery({
    queryKey: ['search', query],
    queryFn: () => stocks.search(query).then((r) => r.data as SymbolMeta[]),
    enabled: query.length >= 2,
    staleTime: 60_000,
  });

  const { data: watchlistData } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => watchlist.get().then((r) => r.data),
    staleTime: 30_000,
  });

  const results = data ?? [];
  const watchlistItems = watchlistData ?? [];

  return (
    <View style={styles.container}>
      <SearchBar
        value={query}
        onChangeText={setQuery}
        placeholder="Search company or symbol…"
        loading={isFetching}
      />

      {query.length < 2 && (
        <EmptyState
          icon="⌕"
          title="Search equities"
          description="Try Infosys, INFY, or RELIANCE — duplicates like INFY vs INFY.NS are merged."
        />
      )}

      {query.length >= 2 && !isFetching && results.length === 0 && (
        <EmptyState icon="—" title="No results" description={`Nothing matched "${query}".`} />
      )}

      <FlatList
        data={results}
        keyExtractor={(item) => item.canonical_symbol ?? item.symbol ?? ''}
        renderItem={({ item }) => {
          const navSymbol = canonicalForNav(item);
          return (
            <View style={styles.row}>
              <TouchableOpacity
                style={styles.rowMain}
                onPress={() => router.push(`/stock/${navSymbol}`)}
                activeOpacity={0.7}
              >
                <SymbolLabel item={item} />
              </TouchableOpacity>
              <WatchlistAddButton symbol={navSymbol} watchlistItems={watchlistItems} />
            </View>
          );
        }}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        contentContainerStyle={{ paddingBottom: 32 }}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg, padding: spacing.md },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 4,
    gap: spacing.sm,
  },
  rowMain: { flex: 1 },
  separator: { height: 1, backgroundColor: colors.border },
});
