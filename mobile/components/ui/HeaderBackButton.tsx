import { Platform, StyleSheet, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { colors, font, spacing } from '@/constants/theme';

interface Props {
  label?: string;
}

export function HeaderBackButton({ label = 'Back' }: Props) {
  return (
    <TouchableOpacity
      onPress={() => router.back()}
      style={styles.btn}
      hitSlop={{ top: 12, bottom: 12, left: 8, right: 12 }}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Ionicons name={Platform.OS === 'ios' ? 'chevron-back' : 'arrow-back'} size={22} color={colors.accent} />
      <Text style={styles.label}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingRight: spacing.sm,
    minHeight: 44,
    minWidth: 44,
  },
  label: {
    fontSize: font.md,
    fontWeight: '600',
    color: colors.accent,
    marginLeft: Platform.OS === 'ios' ? -4 : 2,
  },
});
