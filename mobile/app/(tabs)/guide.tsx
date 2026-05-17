import { useLocalSearchParams } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MetricsGuideContent } from '@/components/guide/MetricsGuideContent';
import { colors, font, spacing } from '@/constants/theme';

export default function GuideTabScreen() {
  const { section } = useLocalSearchParams<{ section?: string }>();
  const insets = useSafeAreaInsets();
  const sectionId = typeof section === 'string' ? section : undefined;

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]}>
      <View style={styles.header}>
        <Text style={styles.title}>Metrics guide</Text>
        <Text style={styles.subtitle}>
          What every number, index, and label means — Indian markets (NSE/BSE)
        </Text>
      </View>
      <MetricsGuideContent sectionId={sectionId} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: spacing.md, paddingTop: spacing.sm, paddingBottom: spacing.xs },
  title: { fontSize: font.xl, fontWeight: '800', color: colors.textPrimary },
  subtitle: { fontSize: font.sm, color: colors.textMuted, marginTop: 4, lineHeight: 20 },
});
