import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { AnalysisFreshness } from '@/lib/analysisHydrate';
import { formatAnalysisAge } from '@/lib/analysisHydrate';
import { colors, font, radius, spacing } from '@/constants/theme';

interface Props {
  loadStatus: 'idle' | 'loading' | 'ready' | 'error';
  isAnalysing: boolean;
  needsRefresh: boolean;
  hasAnalysis: boolean;
  freshness: AnalysisFreshness | null;
  onRefresh: () => void;
}

export function AnalysisStatusBar({
  loadStatus,
  isAnalysing,
  needsRefresh,
  hasAnalysis,
  freshness,
  onRefresh,
}: Props) {
  if (isAnalysing) {
    return (
      <View style={[styles.bar, styles.barAccent]}>
        <ActivityIndicator color={colors.accent} size="small" />
        <Text style={styles.textAccent}>Running multi-agent analysis…</Text>
      </View>
    );
  }

  if (loadStatus === 'loading') {
    return (
      <View style={[styles.bar, styles.barMuted]}>
        <ActivityIndicator color={colors.textMuted} size="small" />
        <Text style={styles.textMuted}>Loading saved analysis…</Text>
      </View>
    );
  }

  if (freshness?.fresh && hasAnalysis) {
    const age = formatAnalysisAge(freshness.ageMinutes);
    const valid =
      freshness.expiresInMinutes != null
        ? ` · valid ~${freshness.expiresInMinutes < 60 ? `${freshness.expiresInMinutes}m` : `${Math.round(freshness.expiresInMinutes / 60)}h`}`
        : '';
    return (
      <View style={[styles.bar, styles.barOk]}>
        <Text style={styles.textOk}>
          Analysis {age}
          {valid}
          {freshness.marketStatus === 'OPEN' ? ' (market open)' : ''}
        </Text>
        <TouchableOpacity onPress={onRefresh} style={styles.linkBtn} hitSlop={8}>
          <Text style={styles.linkText}>Refresh</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (needsRefresh) {
    const label = hasAnalysis
      ? `Saved analysis · ${formatAnalysisAge(freshness?.ageMinutes ?? null)} — refresh for a new verdict`
      : 'No saved analysis yet — run once, then we reuse it until it expires';
    return (
      <View style={[styles.bar, hasAnalysis ? styles.barWarn : styles.barMuted]}>
        <Text style={[styles.textMuted, styles.flex]}>{label}</Text>
        <TouchableOpacity onPress={onRefresh} style={styles.primaryBtn} activeOpacity={0.85}>
          <Text style={styles.primaryBtnText}>{hasAnalysis ? 'Refresh' : 'Run analysis'}</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginTop: spacing.md,
  },
  barOk: { backgroundColor: colors.greenDim },
  barWarn: { backgroundColor: 'rgba(245, 158, 11, 0.12)' },
  barAccent: { backgroundColor: colors.accentDim ?? colors.surface },
  barMuted: { backgroundColor: colors.surface },
  textOk: { flex: 1, fontSize: font.sm, color: colors.green, fontWeight: '600' },
  textAccent: { flex: 1, fontSize: font.sm, color: colors.accent, fontWeight: '600' },
  textMuted: { fontSize: font.sm, color: colors.textMuted, fontWeight: '500' },
  flex: { flex: 1 },
  linkBtn: { paddingVertical: 4, paddingHorizontal: 8 },
  linkText: { fontSize: font.sm, color: colors.green, fontWeight: '700' },
  primaryBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.sm,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  primaryBtnText: { fontSize: font.sm, fontWeight: '700', color: colors.bg },
});
