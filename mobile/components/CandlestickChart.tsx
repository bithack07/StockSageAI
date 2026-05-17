import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAssets } from 'expo-asset';
import { ActivityIndicator, Platform, StyleSheet, Text, View } from 'react-native';
import { stocks } from '@/api/client';
import { colors, font, radius, spacing } from '@/constants/theme';
import { buildCandlestickHtml, normalizeCandles } from '@/components/chart/buildCandlestickHtml';
import { ChartFrame } from '@/components/chart/ChartFrame';

const CHART_HEIGHT = 236;
const CHART_LIB = require('../assets/chart/lightweight-charts.standalone.bundle');

interface Props {
  symbol: string;
  period?: string;
}

export function CandlestickChart({ symbol, period = '3mo' }: Props) {
  const [libAssets] = useAssets([CHART_LIB]);
  const libUri = libAssets?.[0]?.localUri ?? undefined;
  const [inlineLib, setInlineLib] = useState<string | undefined>();
  const [libLoadFailed, setLibLoadFailed] = useState(false);

  useEffect(() => {
    if (Platform.OS === 'web' || !libUri) return;
    let cancelled = false;
    setLibLoadFailed(false);
    (async () => {
      try {
        const res = await fetch(libUri);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const js = await res.text();
        if (!cancelled) setInlineLib(js);
      } catch {
        if (!cancelled) {
          setInlineLib(undefined);
          setLibLoadFailed(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [libUri]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['history', symbol, period],
    queryFn: () => stocks.history(symbol, period, '1d').then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const candles = useMemo(() => normalizeCandles((data ?? []) as Record<string, unknown>[]), [data]);

  const assetSettled = Boolean(libAssets?.[0]);
  const libReady =
    Platform.OS === 'web' ||
    !!inlineLib ||
    libLoadFailed ||
    (assetSettled && !libUri);
  const html = useMemo(() => {
    if (!candles.length || !libReady) return null;
    return buildCandlestickHtml(candles, CHART_HEIGHT, {
      inlineScript: inlineLib,
      scriptSrc: libUri,
    });
  }, [candles, inlineLib, libUri, libReady]);

  if (isLoading || (candles.length > 0 && !html)) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  if (isError || !candles.length || !html) {
    const detail =
      isError && error && typeof error === 'object' && 'message' in error
        ? String((error as { message?: string }).message)
        : null;
    return (
      <View style={[styles.container, styles.centered]}>
        <Text style={styles.placeholder}>Chart data unavailable</Text>
        {detail ? <Text style={styles.hint}>{detail}</Text> : null}
        <Text style={styles.hint}>Check backend is running and symbol is valid (e.g. INFY.NS)</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.caption}>Price chart</Text>
      <View style={styles.chartWrap}>
        <ChartFrame html={html} height={CHART_HEIGHT} />
      </View>
      <View style={styles.legend}>
        <View style={styles.legendLeft}>
          <View style={styles.legendItem}>
            <View style={[styles.legendSwatch, styles.legendUp]} />
            <Text style={styles.legendText}>Up day</Text>
          </View>
          <View style={[styles.legendItem, styles.legendItemSpaced]}>
            <View style={[styles.legendSwatch, styles.legendDown]} />
            <Text style={styles.legendText}>Down day</Text>
          </View>
        </View>
        <Text style={styles.legendAxis}>Date axis below</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.md,
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  centered: {
    height: CHART_HEIGHT,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.md,
  },
  caption: {
    fontSize: font.xs,
    color: colors.textMuted,
    paddingHorizontal: spacing.sm,
    paddingTop: spacing.xs,
  },
  placeholder: { fontSize: font.sm, color: colors.textMuted, textAlign: 'center' },
  hint: { fontSize: font.xs, color: colors.textMuted, textAlign: 'center', marginTop: 4 },
  chartWrap: {
    height: CHART_HEIGHT,
    width: '100%',
    overflow: 'hidden',
    zIndex: 0,
  },
  legend: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  legendLeft: { flexDirection: 'row', alignItems: 'center', flexShrink: 1 },
  legendItem: { flexDirection: 'row', alignItems: 'center' },
  legendItemSpaced: { marginLeft: spacing.md },
  legendSwatch: { width: 10, height: 10, borderRadius: 2, marginRight: 6 },
  legendUp: { backgroundColor: '#22c55e' },
  legendDown: { backgroundColor: '#ef4444' },
  legendText: { fontSize: font.xs, color: colors.textSecondary, fontWeight: '600' },
  legendAxis: { fontSize: font.xs, color: colors.textMuted, flexShrink: 0, marginLeft: spacing.sm },
});
