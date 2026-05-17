import { ActivityIndicator, StyleSheet, Text, TextInput, View } from 'react-native';
import { colors, font, radius, spacing } from '@/constants/theme';

interface Props {
  value: string;
  onChangeText: (t: string) => void;
  placeholder?: string;
  loading?: boolean;
}

export function SearchBar({ value, onChangeText, placeholder = 'Search…', loading }: Props) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.icon}>⌕</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.textMuted}
        autoCapitalize="none"
        autoCorrect={false}
      />
      {loading ? <ActivityIndicator color={colors.accent} style={styles.spinner} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    marginBottom: spacing.md,
  },
  icon: { fontSize: 18, color: colors.textMuted, paddingLeft: spacing.md },
  input: {
    flex: 1,
    paddingVertical: 14,
    paddingHorizontal: spacing.sm,
    color: colors.textPrimary,
    fontSize: font.md,
  },
  spinner: { marginRight: spacing.md },
});
