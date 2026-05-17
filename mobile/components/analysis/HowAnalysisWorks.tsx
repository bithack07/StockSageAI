import { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { router } from 'expo-router';
import { ANALYSIS_PIPELINE_INTRO, ANALYSIS_PIPELINE_STEPS } from '@/content/howAnalysisWorks';
import { GuideLink } from '@/components/ui/GuideLink';
import { colors, font, radius, spacing } from '@/constants/theme';

export function HowAnalysisWorks() {
  const [open, setOpen] = useState(false);

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <TouchableOpacity onPress={() => setOpen((v) => !v)} style={styles.header} activeOpacity={0.8}>
        <View style={styles.headerText}>
          <Text style={styles.label}>How analysis works</Text>
          <Text style={styles.hint}>
            {open ? 'Step-by-step pipeline' : 'Tap to see how StockSage analyzes this stock'}
          </Text>
        </View>
        <Text style={styles.chevron}>{open ? '▾' : '▸'}</Text>
      </TouchableOpacity>
        <GuideLink section="how-analysis-works" label="Guide" guideVariant="stack" />
      </View>

      {open && (
        <View style={styles.body}>
          <Text style={styles.intro}>{ANALYSIS_PIPELINE_INTRO}</Text>
          {ANALYSIS_PIPELINE_STEPS.map((s) => (
            <View key={s.step} style={styles.stepRow}>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{s.step}</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>{s.title}</Text>
                <Text style={styles.stepSummary}>{s.summary}</Text>
                {s.detail ? <Text style={styles.stepDetail}>{s.detail}</Text> : null}
              </View>
            </View>
          ))}
          <TouchableOpacity
            style={styles.guideBtn}
            onPress={() => router.push('/guide')}
            activeOpacity={0.75}
          >
            <Text style={styles.guideBtnText}>Open full metrics guide</Text>
          </TouchableOpacity>
          <Text style={styles.footerNote}>Use the Activity log below for live progress.</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  headerRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm, zIndex: 1 },
  header: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 48,
  },
  headerText: { flex: 1, paddingRight: spacing.sm },
  label: {
    fontSize: font.xs,
    fontWeight: '800',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  hint: { fontSize: font.sm, color: colors.textSecondary, lineHeight: 20 },
  chevron: { fontSize: 18, color: colors.accent, fontWeight: '700' },
  body: { marginTop: spacing.md, paddingTop: spacing.md, borderTopWidth: 1, borderTopColor: colors.border },
  intro: { fontSize: font.sm, color: colors.textMuted, lineHeight: 20, marginBottom: spacing.md },
  stepRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md },
  badge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.accentDim,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: { fontSize: 12, fontWeight: '800', color: colors.accent },
  stepContent: { flex: 1 },
  stepTitle: { fontSize: font.sm, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 },
  stepSummary: { fontSize: font.sm, color: colors.textSecondary, lineHeight: 20 },
  stepDetail: { fontSize: font.xs, color: colors.textMuted, marginTop: 4, lineHeight: 18 },
  guideBtn: {
    marginTop: spacing.sm,
    backgroundColor: colors.accentDim,
    borderWidth: 1,
    borderColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: 12,
    paddingHorizontal: spacing.md,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  guideBtnText: { fontSize: font.sm, fontWeight: '700', color: colors.accent },
  footerNote: { fontSize: font.xs, color: colors.textMuted, marginTop: spacing.sm },
});
