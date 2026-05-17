import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { market } from '@/api/client';
import { AnimatedBackground } from '@/components/ui/AnimatedBackground';
import { AppBrandHeader } from '@/components/ui/AppBrandHeader';
import { MarketHeroIllustration } from '@/components/ui/MarketHeroIllustration';
import { GuideLink } from '@/components/ui/GuideLink';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { colors, font, radius, spacing } from '@/constants/theme';

interface IndexData {
  name: string;
  symbol: string;
  price: number | null;
  change_pct: number | null;
  rsi: number | null;
}

function IndexCard({ item }: { item: IndexData }) {
  const pos = (item.change_pct ?? 0) >= 0;
  return (
    <View style={styles.indexCard}>
      <Text style={styles.indexName} numberOfLines={1}>
        {item.name?.replace(/_/g, ' ')}
      </Text>
      <Text style={styles.indexPrice}>
        {item.price != null ? `₹${item.price.toLocaleString('en-IN')}` : '—'}
      </Text>
      <View style={[styles.changeBadge, { backgroundColor: pos ? colors.greenDim : colors.redDim }]}>
        <Text style={[styles.changeText, { color: pos ? colors.green : colors.red }]}>
          {pos ? '+' : ''}{item.change_pct?.toFixed(2) ?? '—'}%
        </Text>
      </View>
      {item.rsi != null && <Text style={styles.rsiTag}>RSI {item.rsi}</Text>}
    </View>
  );
}

function MarketStatusBadge({ status }: { status: string }) {
  const isOpen = status === 'OPEN';
  const isPreopen = status === 'PREOPEN';
  return (
    <View
      style={[
        styles.statusBadge,
        {
          backgroundColor: isOpen
            ? colors.greenDim
            : isPreopen
              ? colors.yellowDim
              : 'rgba(100,116,139,0.15)',
        },
      ]}
    >
      <View
        style={[
          styles.statusDot,
          {
            backgroundColor: isOpen
              ? colors.green
              : isPreopen
                ? colors.yellow
                : colors.textMuted,
          },
        ]}
      />
      <Text
        style={[
          styles.statusText,
          {
            color: isOpen
              ? colors.green
              : isPreopen
                ? colors.yellow
                : colors.textSecondary,
          },
        ]}
      >
        {status}
      </Text>
    </View>
  );
}

const QUICK_SEARCHES = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS'];

export default function DashboardScreen() {
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ['market_overview'],
    queryFn: () => market.overview().then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const contentWidth = Dimensions.get('window').width - spacing.md * 2;
  const heroHeight = Math.round(contentWidth * 0.42);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const { data: fresh } = await market.overview(true);
      queryClient.setQueryData(['market_overview'], fresh);
    } finally {
      setRefreshing(false);
    }
  };

  const indices = useMemo(() => data?.indices ?? [], [data?.indices]);

  return (
    <View style={styles.container}>
      <AnimatedBackground />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: Math.max(insets.bottom, spacing.md) + 80 },
        ]}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.accent} />
        }
      >
        <AppBrandHeader />

        <View style={styles.heroBanner}>
          <MarketHeroIllustration width={contentWidth} height={heroHeight} />
        </View>

        <View style={styles.marketHeader}>
          <View style={styles.marketHeaderText}>
            <Text style={styles.marketTitle}>Market overview</Text>
            <Text style={styles.marketSub}>NSE / BSE · Live indices</Text>
          </View>
          {data?.market_status ? <MarketStatusBadge status={data.market_status} /> : null}
        </View>

        <GuideLink section="indices" label="What do these indices mean?" />

        {isLoading && <ActivityIndicator color={colors.accent} style={styles.loader} />}

        {indices.length > 0 && (
          <View style={styles.section}>
            <SectionHeader title="Indices" />
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.indicesRow}
            >
              {indices.map((item) => (
                <IndexCard key={item.symbol} item={item} />
              ))}
            </ScrollView>
          </View>
        )}

        <View style={styles.section}>
          <SectionHeader title="Quick access" />
          <View style={styles.quickRow}>
            {QUICK_SEARCHES.map((sym) => (
              <TouchableOpacity
                key={sym}
                style={styles.quickChip}
                onPress={() => router.push(`/stock/${sym}`)}
              >
                <Text style={styles.quickChipText}>
                  {sym.replace('.NS', '').replace('.BO', '')}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <Text style={styles.footer}>Data refreshes every 5 min during market hours</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  scroll: { flex: 1 },
  content: { paddingHorizontal: spacing.md, paddingTop: spacing.sm },
  heroBanner: {
    width: '100%',
    marginBottom: spacing.md,
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
  },
  marketHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  marketHeaderText: { flex: 1, paddingRight: spacing.sm },
  marketTitle: {
    fontSize: font.lg,
    fontWeight: '800',
    color: colors.textPrimary,
    letterSpacing: -0.3,
  },
  marketSub: { fontSize: font.xs, color: colors.textMuted, marginTop: 4 },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.full,
    flexShrink: 0,
  },
  statusDot: { width: 6, height: 6, borderRadius: 3, marginRight: 6 },
  statusText: { fontSize: font.xs, fontWeight: '700' },
  loader: { marginVertical: spacing.lg },
  section: { marginTop: spacing.xs },
  indicesRow: { paddingRight: spacing.md },
  indexCard: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    width: 152,
    marginRight: 10,
  },
  indexName: {
    fontSize: font.xs,
    color: colors.textMuted,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  indexPrice: {
    fontSize: font.xl,
    fontWeight: '800',
    color: colors.textPrimary,
    marginTop: 4,
  },
  changeBadge: {
    alignSelf: 'flex-start',
    borderRadius: radius.sm,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginTop: 6,
  },
  changeText: { fontSize: font.xs, fontWeight: '700' },
  rsiTag: { fontSize: font.xs, color: colors.textSecondary, marginTop: 4 },
  quickRow: { flexDirection: 'row', flexWrap: 'wrap' },
  quickChip: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.full,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },
  quickChipText: { fontSize: font.sm, fontWeight: '700', color: colors.accent },
  footer: {
    fontSize: font.xs,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.xl,
    lineHeight: 18,
  },
});
