import { StyleSheet, Text, View } from 'react-native';
import { GuideLink } from '@/components/ui/GuideLink';
import type { Prediction } from '@/store/analysisStore';
import { colors, font, radius, spacing, shadow } from '@/constants/theme';

const DIRECTION_COLORS = {
  BULLISH: colors.green,
  BEARISH: colors.red,
  NEUTRAL: colors.yellow,
};

function formatAnalyzedAt(iso?: string): string | null {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return null;
  }
}

export function PredictionCard({ prediction }: { prediction: Prediction }) {
  const dirColor = DIRECTION_COLORS[prediction.direction] ?? colors.textSecondary;
  const analyzedLabel = formatAnalyzedAt(prediction.analyzed_at);
  const isCached = prediction.analysis_source === 'cached';

  return (
    <View style={[styles.card, shadow.card, { borderLeftColor: dirColor }]}>
      {analyzedLabel ? (
        <Text style={styles.meta}>
          {isCached ? 'Previous analysis' : 'Live analysis'} · {analyzedLabel}
        </Text>
      ) : null}
      <View style={styles.topRow}>
        <Text style={[styles.direction, { color: dirColor }]}>{prediction.direction}</Text>
        <View style={styles.badges}>
          <View style={styles.badge}><Text style={styles.badgeText}>{prediction.conviction}</Text></View>
          <View style={styles.badge}><Text style={styles.badgeText}>{prediction.confidence_pct}%</Text></View>
        </View>
      </View>

      <Text style={styles.horizon}>
        {prediction.horizon_days}-day near-term horizon
        {prediction.agent_fundamental_verdict
          ? ` · AI fundamental: ${String(prediction.agent_fundamental_verdict).replace(/_/g, ' ')}`
          : ''}
      </Text>

      {prediction.valuation_note ? (
        <Text style={styles.valuationNote}>{prediction.valuation_note}</Text>
      ) : null}

      {prediction.conflicts && prediction.conflicts.length > 0 ? (
        <View style={styles.conflictBox}>
          <Text style={styles.conflictTitle}>Mixed signals</Text>
          {prediction.conflicts.map((c, i) => (
            <Text key={i} style={styles.conflictLine}>• {c}</Text>
          ))}
        </View>
      ) : null}

      {prediction.target_price_range[0] != null && (
        <Text style={styles.target}>
          Target ₹{prediction.target_price_range[0]?.toLocaleString('en-IN')} – ₹{prediction.target_price_range[1]?.toLocaleString('en-IN')}
        </Text>
      )}

      <Text style={styles.rationale}>{prediction.rationale}</Text>

      {prediction.key_signals?.length > 0 && (
        <View style={styles.box}>
          <Text style={styles.boxLabel}>Key signals</Text>
          {prediction.key_signals.map((s, i) => (
            <Text key={i} style={styles.boxLine}>• {s}</Text>
          ))}
        </View>
      )}

      {prediction.do_not_trade_if && (
        <View style={styles.warning}>
          <Text style={styles.warningText}>⛔ {prediction.do_not_trade_if}</Text>
        </View>
      )}

      <Text style={styles.disclaimer}>
        StockSage AI provides AI-generated research and tools for informational use. It is not investment advice
        or a recommendation from a SEBI-registered adviser. Past performance does not guarantee future results.
        You are responsible for your own decisions.
      </Text>
      <GuideLink section="ai-prediction" label="What do direction, conviction & confidence mean?" guideVariant="stack" />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    borderLeftWidth: 4,
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  meta: { fontSize: font.xs, color: colors.textMuted, marginBottom: 4 },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  valuationNote: { fontSize: font.sm, color: colors.textSecondary, lineHeight: 20 },
  conflictBox: {
    backgroundColor: colors.yellowDim,
    borderRadius: radius.md,
    padding: spacing.sm,
    borderWidth: 1,
    borderColor: 'rgba(245,158,11,0.25)',
    gap: 4,
  },
  conflictTitle: { fontSize: font.xs, fontWeight: '700', color: colors.yellow, textTransform: 'uppercase' },
  conflictLine: { fontSize: font.sm, color: colors.textSecondary, lineHeight: 18 },
  direction: { fontSize: font.xxl, fontWeight: '800', letterSpacing: -0.5 },
  badges: { gap: 6, alignItems: 'flex-end' },
  badge: { backgroundColor: colors.surface, borderRadius: radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  badgeText: { fontSize: font.xs, fontWeight: '700', color: colors.textPrimary },
  horizon: { fontSize: font.sm, color: colors.textMuted },
  target: { fontSize: font.lg, fontWeight: '700', color: colors.textPrimary },
  rationale: { fontSize: font.md, color: colors.textSecondary, lineHeight: 22 },
  box: { backgroundColor: colors.bg, borderRadius: radius.md, padding: spacing.md, gap: 4 },
  boxLabel: { fontSize: font.xs, fontWeight: '700', color: colors.textMuted, textTransform: 'uppercase', marginBottom: 4 },
  boxLine: { fontSize: font.sm, color: colors.textSecondary },
  warning: { backgroundColor: colors.yellowDim, borderRadius: radius.md, padding: spacing.md, borderWidth: 1, borderColor: 'rgba(245,158,11,0.25)' },
  warningText: { fontSize: font.sm, color: colors.yellow },
  disclaimer: { fontSize: font.xs, color: colors.textMuted, lineHeight: 16, marginTop: spacing.sm },
});
