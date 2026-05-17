import { StyleSheet, Text, View } from 'react-native';
import { colors, font, radius, spacing } from '@/constants/theme';

interface Props {
  icon?: string;
  title: string;
  description?: string;
}

export function EmptyState({ icon = '◌', title, description }: Props) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.icon}>{icon}</Text>
      <Text style={styles.title}>{title}</Text>
      {description ? <Text style={styles.desc}>{description}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  icon: { fontSize: 36, opacity: 0.45, marginBottom: spacing.sm },
  title: { fontSize: font.md, fontWeight: '700', color: colors.textSecondary, textAlign: 'center' },
  desc: { fontSize: font.sm, color: colors.textMuted, textAlign: 'center', marginTop: spacing.xs, lineHeight: 20 },
});
