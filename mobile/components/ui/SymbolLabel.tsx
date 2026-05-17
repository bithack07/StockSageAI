import { StyleSheet, Text, View } from 'react-native';
import type { SymbolMeta } from '@/lib/symbolDisplay';
import { displaySymbol, displayTitle } from '@/lib/symbolDisplay';
import { colors, font, radius } from '@/constants/theme';

type Props = {
  item: SymbolMeta | string;
  showStoredHint?: boolean;
};

export function SymbolLabel({ item, showStoredHint = false }: Props) {
  if (typeof item === 'string') {
    return <Text style={styles.ticker}>{displaySymbol(item)}</Text>;
  }

  const exchange = item.exchange ?? 'NSE';
  return (
    <View>
      {item.company_name && item.company_name !== item.base_ticker ? (
        <Text style={styles.name} numberOfLines={1}>{item.company_name}</Text>
      ) : null}
      <View style={styles.row}>
        <Text style={styles.ticker}>{item.base_ticker ?? displaySymbol(item)}</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{exchange}</Text>
        </View>
      </View>
      {showStoredHint && item.canonical_symbol && (
        <Text style={styles.hint}>Listed on {exchange} · {item.canonical_symbol}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  name: { fontSize: font.md, fontWeight: '700', color: colors.textPrimary },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 2 },
  ticker: { fontSize: font.sm, fontWeight: '800', color: colors.accent },
  badge: {
    backgroundColor: colors.accentDim,
    borderRadius: radius.sm,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderWidth: 1,
    borderColor: colors.accent,
  },
  badgeText: { fontSize: 10, fontWeight: '700', color: colors.accent },
  hint: { fontSize: font.xs, color: colors.textMuted, marginTop: 2 },
});
