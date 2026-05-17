import { useEffect, useLayoutEffect } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useSmartAnalysis } from '@/hooks/useSmartAnalysis';
import { useAnalysisStore } from '@/store/analysisStore';
import { AnalysisStatusBar } from '@/components/analysis/AnalysisStatusBar';
import { useQuote } from '@/hooks/useQuote';
import { AgentStream } from '@/components/AgentStream';
import { PredictionCard } from '@/components/PredictionCard';
import { CandlestickChart } from '@/components/CandlestickChart';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { GuideLink } from '@/components/ui/GuideLink';
import { HoldingThesisCard } from '@/components/investor/HoldingThesisCard';
import { OwnerInsights } from '@/components/investor/OwnerInsights';
import { useHoldingForSymbol } from '@/hooks/useHoldingForSymbol';
import { SymbolLabel } from '@/components/ui/SymbolLabel';
import { HowAnalysisWorks } from '@/components/analysis/HowAnalysisWorks';
import { displaySymbol } from '@/lib/symbolDisplay';
import { colors, font, radius, spacing } from '@/constants/theme';

export default function StockDetailScreen() {
  const { symbol } = useLocalSearchParams<{ symbol: string }>();
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();
  const tabBarHeight = useBottomTabBarHeight();
  const { data: quote } = useQuote(symbol ?? null);
  const { prediction, agentOutputs, error, resetAnalysis, analysisFreshness, loadStatus } =
    useAnalysisStore();
  const { runAnalysis, needsRefresh, isAnalysing, hasAnalysis } = useSmartAnalysis(symbol ?? null);
  const holding = useHoldingForSymbol(symbol ?? null);
  const fundVerdict = agentOutputs.fundamental?.valuation_verdict as string | undefined;

  useEffect(() => () => { resetAnalysis(); }, [symbol]);

  useLayoutEffect(() => {
    const label =
      quote?.base_ticker ??
      quote?.short_label ??
      (symbol ? displaySymbol(symbol) : null) ??
      'Analysis';
    navigation.setOptions({
      title: label,
      headerBackVisible: false,
    });
  }, [navigation, symbol, quote?.base_ticker, quote?.short_label]);

  const pos = (quote?.change_pct ?? 0) >= 0;
  const scrollBottomPad = Math.max(tabBarHeight, insets.bottom) + spacing.lg;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? tabBarHeight + 56 : 0}
    >
      <ScrollView
        style={styles.container}
        contentContainerStyle={[styles.content, { paddingBottom: scrollBottomPad }]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        nestedScrollEnabled
      >
        <View style={styles.headerCard}>
          {quote?.company_name || quote?.base_ticker ? (
            <SymbolLabel item={quote} showStoredHint />
          ) : (
            <Text style={styles.symbol}>{symbol}</Text>
          )}
          {quote?.price != null && (
            <Text style={styles.price}>₹{quote.price.toLocaleString('en-IN')}</Text>
          )}
          {quote?.change_pct != null && (
            <View style={[styles.changeBadge, { backgroundColor: pos ? colors.greenDim : colors.redDim }]}>
              <Text style={[styles.change, { color: pos ? colors.green : colors.red }]}>
                {pos ? '+' : ''}{quote.change_pct.toFixed(2)}%
              </Text>
            </View>
          )}
          <AnalysisStatusBar
            loadStatus={loadStatus}
            isAnalysing={isAnalysing}
            needsRefresh={needsRefresh}
            hasAnalysis={hasAnalysis}
            freshness={analysisFreshness}
            onRefresh={runAnalysis}
          />
        </View>

        <GuideLink section="how-analysis-works" label="How analysis works" />

        <CandlestickChart symbol={symbol!} />

        {fundVerdict ? (
          <View style={styles.aiFundBanner}>
            <Text style={styles.aiFundLabel}>AI fundamental agent (this run)</Text>
            <Text style={styles.aiFundVerdict}>{String(fundVerdict).replace(/_/g, ' ')}</Text>
          </View>
        ) : null}

      {symbol && <OwnerInsights symbol={symbol} />}

      {holding && (
        <HoldingThesisCard
          holdingId={holding.id}
          symbol={holding.symbol}
          collapsed={false}
          collapsible={false}
        />
      )}

      <HowAnalysisWorks />

        <SectionHeader title="Agent analysis" />
        <GuideLink section="ai-agents" label="What do the agents mean?" />
        <View style={styles.section}>
          <AgentStream />
        </View>

        {prediction && (
          <>
            <SectionHeader title="AI prediction" />
            <PredictionCard prediction={prediction} />
          </>
        )}

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingBottom: spacing.xl },
  headerCard: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  symbol: { fontSize: font.xxl, fontWeight: '800', color: colors.textPrimary, letterSpacing: -0.5 },
  price: { fontSize: font.xxxl, fontWeight: '800', color: colors.textPrimary, marginTop: spacing.xs },
  changeBadge: {
    alignSelf: 'flex-start',
    borderRadius: radius.sm,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginTop: spacing.sm,
  },
  change: { fontSize: font.md, fontWeight: '700' },
  aiFundBanner: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
    marginBottom: spacing.sm,
  },
  aiFundLabel: { fontSize: font.xs, color: colors.textMuted, fontWeight: '600' },
  aiFundVerdict: { fontSize: font.md, fontWeight: '800', color: colors.textPrimary, marginTop: 2 },
  section: { marginBottom: spacing.md },
  errorBox: {
    marginTop: spacing.md,
    backgroundColor: colors.redDim,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.red,
  },
  errorText: { color: colors.red, fontSize: font.sm },
});
