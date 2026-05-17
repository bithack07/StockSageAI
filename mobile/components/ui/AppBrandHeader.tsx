import { StyleSheet, Text, View } from 'react-native';
import { colors, font, radius, spacing } from '@/constants/theme';

interface Props {
  compact?: boolean;
}

export function AppBrandHeader({ compact = false }: Props) {
  return (
    <View style={[styles.row, compact && styles.rowCompact]}>
      <View style={[styles.logoMark, compact && styles.logoMarkCompact]}>
        <Text style={[styles.logoIcon, compact && styles.logoIconCompact]}>◈</Text>
      </View>
      <View style={styles.textBlock}>
        <Text style={[styles.appName, compact && styles.appNameCompact]}>StockSage AI</Text>
        <Text style={styles.tagline}>Agentic intelligence for Indian equities</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  rowCompact: { marginBottom: spacing.sm },
  logoMark: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    backgroundColor: colors.accentDim,
    borderWidth: 1,
    borderColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  logoMarkCompact: { width: 36, height: 36 },
  logoIcon: { fontSize: 22, color: colors.accent },
  logoIconCompact: { fontSize: 18 },
  textBlock: { flex: 1, flexShrink: 1 },
  appName: {
    fontSize: font.xxl,
    fontWeight: '800',
    color: colors.textPrimary,
    letterSpacing: -0.5,
  },
  appNameCompact: { fontSize: font.xl },
  tagline: {
    fontSize: font.sm,
    color: colors.textSecondary,
    marginTop: 2,
    lineHeight: 20,
  },
});
