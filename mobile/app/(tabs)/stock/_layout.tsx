import { Platform } from 'react-native';
import { Stack } from 'expo-router';
import { HeaderBackButton } from '@/components/ui/HeaderBackButton';
import { colors } from '@/constants/theme';

export default function StockStackLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.accent,
        headerTitleStyle: { color: colors.textPrimary, fontWeight: '800' },
        contentStyle: { backgroundColor: colors.bg },
        headerShadowVisible: false,
        headerBackVisible: false,
        ...(Platform.OS === 'ios' ? { headerBackButtonDisplayMode: 'minimal' as const } : {}),
      }}
    >
      <Stack.Screen
        name="[symbol]"
        options={{
          title: 'Analysis',
          headerLeft: () => <HeaderBackButton />,
        }}
      />
    </Stack>
  );
}
