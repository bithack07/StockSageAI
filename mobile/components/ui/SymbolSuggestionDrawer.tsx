import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { stocks } from '@/api/client';
import { canonicalForNav, displaySymbol, displayTitle, type SymbolMeta } from '@/lib/symbolDisplay';
import { colors, font, radius, spacing } from '@/constants/theme';

interface Props {
  query: string;
  visible?: boolean;
  onSelect: (canonicalSymbol: string) => void;
  maxItems?: number;
}

export function SymbolSuggestionDrawer({
  query,
  visible = true,
  onSelect,
  maxItems = 6,
}: Props) {
  const trimmed = query.trim();
  const enabled = visible && trimmed.length >= 2;

  const { data, isFetching } = useQuery({
    queryKey: ['symbol-suggest', trimmed],
    queryFn: () => stocks.search(trimmed).then((r) => r.data as SymbolMeta[]),
    enabled,
    staleTime: 60_000,
  });

  if (!enabled) return null;

  const results = (data ?? []).slice(0, maxItems);

  return (
    <View style={styles.drawer}>
      {isFetching && results.length === 0 ? (
        <ActivityIndicator color={colors.accent} style={styles.loader} />
      ) : null}

      {!isFetching && results.length === 0 ? (
        <Text style={styles.empty}>No matches for “{trimmed}”</Text>
      ) : null}

      {results.map((item, index) => {
        const sym = canonicalForNav(item);
        const title = displayTitle(item);
        const ticker = displaySymbol(item);
        const exchange = item.exchange ?? 'NSE';
        return (
          <TouchableOpacity
            key={sym || `${ticker}-${index}`}
            style={[styles.row, index < results.length - 1 && styles.rowBorder]}
            onPressIn={() => onSelect(sym)}
            activeOpacity={0.65}
          >
            <View style={styles.rowText}>
              <Text style={styles.title} numberOfLines={1}>
                {title}
              </Text>
              <Text style={styles.sub} numberOfLines={1}>
                {ticker} · {exchange}
                {item.canonical_symbol && item.canonical_symbol !== ticker
                  ? ` · ${item.canonical_symbol}`
                  : ''}
              </Text>
            </View>
            <Text style={styles.useBtn}>Use</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  drawer: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    marginTop: spacing.xs,
    marginBottom: spacing.sm,
    overflow: 'hidden',
    maxHeight: 220,
  },
  loader: { paddingVertical: spacing.md },
  empty: {
    fontSize: font.sm,
    color: colors.textMuted,
    padding: spacing.md,
    textAlign: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: spacing.md,
  },
  rowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowText: { flex: 1, paddingRight: spacing.sm },
  title: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary },
  sub: { fontSize: font.xs, color: colors.textMuted, marginTop: 2 },
  useBtn: { fontSize: font.xs, fontWeight: '700', color: colors.accent },
});
