import { Text, TouchableOpacity, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { openGuide } from '@/lib/openGuide';
import { colors, font, radius, spacing } from '@/constants/theme';

interface Props {
  label?: string;
  /** Section id from content/metricsGuide.ts — scrolls guide to that section */
  section?: string;
  /** Use stack /guide when on analysis screen (keeps back to stock) */
  guideVariant?: 'tab' | 'stack';
}

export function GuideLink({ label = 'What do these mean?', section, guideVariant = 'tab' }: Props) {
  const onPress = () => {
    if (guideVariant === 'stack') {
      router.push(section ? { pathname: '/guide', params: { section } } : '/guide');
    } else {
      openGuide(section);
    }
  };

  return (
    <TouchableOpacity
      onPress={onPress}
      style={styles.wrap}
      activeOpacity={0.75}
      hitSlop={{ top: 8, bottom: 8, left: 4, right: 4 }}
    >
      <Text style={styles.text}>ℹ {label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignSelf: 'flex-start',
    marginVertical: spacing.xs,
    backgroundColor: colors.accentDim,
    borderWidth: 1,
    borderColor: colors.accent,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    minHeight: 40,
    justifyContent: 'center',
  },
  text: { fontSize: font.sm, fontWeight: '700', color: colors.accent },
});
