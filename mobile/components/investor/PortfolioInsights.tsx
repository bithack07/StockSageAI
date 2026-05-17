import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { investor } from '@/api/client';
import { colors, font, radius, spacing } from '@/constants/theme';
import { formatInr } from '@/lib/formatInr';

const PORTFOLIO_TIPS = [
  'Use NSE symbols (e.g. RELIANCE.NS, TCS.NS) — same as Search and Watchlist.',
  'Set net worth in a stock’s Owner Insights to see position size vs your wealth.',
  'Sector warnings appear when one stock or sector is heavily concentrated.',
];

interface HoldingDetail {
  symbol: string;
  sector: string;
  current_value: number;
  pct_of_portfolio: number;
  pct_of_net_worth?: number | null;
}

export function PortfolioInsights() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolio-insights'],
    queryFn: () => investor.portfolioInsights().then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const sectors = data?.sectors ?? [];
  const warnings = data?.warnings ?? [];
  const details: HoldingDetail[] = data?.holdings_detail ?? [];
  const hasInsights = sectors.length > 0 || warnings.length > 0 || details.length > 0;

  return (
    <View style={styles.wrap}>
      <Text style={styles.tip}>{PORTFOLIO_TIPS.join(' ')}</Text>

      {isLoading && (
        <ActivityIndicator color={colors.accent} style={{ marginVertical: spacing.sm }} />
      )}

      {isError && (
        <Text style={styles.error}>Could not load allocation insights. Pull to refresh.</Text>
      )}

      {!isLoading && !isError && hasInsights && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Allocation · India</Text>

          {details.map((d) => (
            <View key={d.symbol} style={styles.detailRow}>
              <View style={styles.detailLeft}>
                <Text style={styles.detailSymbol}>{d.symbol.replace(/\.(NS|BO)$/i, '')}</Text>
                <Text style={styles.detailSector}>{d.sector}</Text>
              </View>
              <View style={styles.detailRight}>
                <Text style={styles.detailValue}>{formatInr(d.current_value)}</Text>
                <Text style={styles.detailPct}>{d.pct_of_portfolio}% of portfolio</Text>
                {d.pct_of_net_worth != null && (
                  <Text style={styles.detailNw}>{d.pct_of_net_worth}% of net worth</Text>
                )}
              </View>
            </View>
          ))}

          {sectors.map((s: { sector: string; pct: number; value_inr?: number }) => (
            <View key={s.sector} style={styles.sectorRow}>
              <Text style={styles.sectorName}>{s.sector}</Text>
              <Text style={styles.sectorPct}>{s.pct}%</Text>
            </View>
          ))}

          {warnings.map((w: string, i: number) => (
            <Text key={i} style={styles.warn}>⚠ {w}</Text>
          ))}
        </View>
      )}

      {!isLoading && !isError && !hasInsights && (
        <Text style={styles.hint}>
          Add holdings below to see sector allocation and diversification tips.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: spacing.md, gap: spacing.sm },
  tip: { fontSize: font.xs, color: colors.textMuted, lineHeight: 18 },
  error: { fontSize: font.xs, color: colors.red },
  hint: { fontSize: font.xs, color: colors.textSecondary, lineHeight: 18 },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: spacing.sm,
  },
  cardTitle: {
    fontSize: font.xs,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 2,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  detailLeft: { flex: 1, paddingRight: spacing.sm },
  detailRight: { alignItems: 'flex-end' },
  detailSymbol: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary },
  detailSector: { fontSize: font.xs, color: colors.textMuted, marginTop: 2 },
  detailValue: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary },
  detailPct: { fontSize: font.xs, color: colors.textSecondary, marginTop: 2 },
  detailNw: { fontSize: font.xs, color: colors.accent, marginTop: 1 },
  sectorRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    padding: spacing.sm,
    borderRadius: radius.md,
  },
  sectorName: { color: colors.textSecondary, fontSize: font.sm },
  sectorPct: { color: colors.textPrimary, fontWeight: '700', fontSize: font.sm },
  warn: { fontSize: font.xs, color: colors.yellow, lineHeight: 18 },
});
