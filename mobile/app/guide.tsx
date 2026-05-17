import { useLocalSearchParams } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { MetricsGuideContent } from '@/components/guide/MetricsGuideContent';
import { HeaderBackButton } from '@/components/ui/HeaderBackButton';
import { colors, spacing } from '@/constants/theme';

/** Stack route when opening guide from analysis (outside tabs). */
export default function GuideStackScreen() {
  const { section } = useLocalSearchParams<{ section?: string }>();
  const sectionId = typeof section === 'string' ? section : undefined;

  return (
    <View style={styles.container}>
      <View style={styles.backRow}>
        <HeaderBackButton />
      </View>
      <MetricsGuideContent sectionId={sectionId} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  backRow: { paddingHorizontal: spacing.md, paddingTop: spacing.sm },
});
