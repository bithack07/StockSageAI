import { useEffect, useRef } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { METRICS_GUIDE_SECTIONS } from '@/content/metricsGuide';
import { colors, font, radius, spacing } from '@/constants/theme';

interface Props {
  sectionId?: string | null;
  showToc?: boolean;
  onSectionPositions?: (positions: Record<string, number>) => void;
}

export function MetricsGuideContent({ sectionId, showToc = true }: Props) {
  const scrollRef = useRef<ScrollView>(null);
  const sectionOffsets = useRef<Record<string, number>>({});
  useEffect(() => {
    if (!sectionId) return;
    let attempts = 0;
    const timer = setInterval(() => {
      const y = sectionOffsets.current[sectionId];
      attempts += 1;
      if (y != null || attempts > 12) {
        clearInterval(timer);
        if (y != null) scrollRef.current?.scrollTo({ y: Math.max(0, y - 12), animated: true });
      }
    }, 80);
    return () => clearInterval(timer);
  }, [sectionId]);

  const jumpTo = (id: string) => {
    const y = sectionOffsets.current[id];
    if (y != null) scrollRef.current?.scrollTo({ y: Math.max(0, y - 12), animated: true });
  };

  return (
    <ScrollView
      ref={scrollRef}
      style={styles.scroll}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {showToc && (
        <View style={styles.toc}>
          <Text style={styles.tocTitle}>Jump to a section</Text>
          <View style={styles.tocChips}>
            {METRICS_GUIDE_SECTIONS.map((s) => (
              <TouchableOpacity
                key={s.id}
                style={[styles.chip, sectionId === s.id && styles.chipActive]}
                onPress={() => jumpTo(s.id)}
              >
                <Text style={[styles.chipText, sectionId === s.id && styles.chipTextActive]}>
                  {s.title.split('(')[0].trim()}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {METRICS_GUIDE_SECTIONS.map((section) => (
        <View
          key={section.id}
          style={[styles.section, sectionId === section.id && styles.sectionHighlight]}
          onLayout={(e) => {
            sectionOffsets.current[section.id] = e.nativeEvent.layout.y;
          }}
        >
          <Text style={styles.sectionTitle}>{section.title}</Text>
          {section.intro ? <Text style={styles.intro}>{section.intro}</Text> : null}
          {section.items.map((item) => (
            <View key={item.term} style={styles.item}>
              <Text style={styles.term}>{item.term}</Text>
              <Text style={styles.explanation}>{item.explanation}</Text>
              {item.example ? <Text style={styles.example}>Example: {item.example}</Text> : null}
            </View>
          ))}
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  toc: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tocTitle: { fontSize: font.sm, fontWeight: '700', color: colors.textSecondary, marginBottom: spacing.sm },
  tocChips: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.full,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
    marginBottom: 8,
  },
  chipActive: { backgroundColor: colors.accentDim, borderColor: colors.accent },
  chipText: { fontSize: font.xs, fontWeight: '600', color: colors.textSecondary },
  chipTextActive: { color: colors.accent },
  section: {
    marginBottom: spacing.lg,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionHighlight: { borderColor: colors.accent, borderWidth: 2 },
  sectionTitle: { fontSize: font.lg, fontWeight: '800', color: colors.textPrimary, marginBottom: spacing.sm },
  intro: { fontSize: font.sm, color: colors.textMuted, marginBottom: spacing.md, lineHeight: 20 },
  item: { marginBottom: spacing.md, borderLeftWidth: 2, borderLeftColor: colors.accent, paddingLeft: spacing.sm },
  term: { fontSize: font.sm, fontWeight: '700', color: colors.accent, marginBottom: 4 },
  explanation: { fontSize: font.sm, color: colors.textSecondary, lineHeight: 20 },
  example: { fontSize: font.xs, color: colors.textMuted, marginTop: 4, fontStyle: 'italic' },
});
