import 'react-native-gesture-handler';
import 'react-native-reanimated';
import { useEffect, useState } from 'react';
import { Stack, router } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useUserStore } from '@/store/userStore';
import { colors } from '@/constants/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60 * 1000, retry: 2 },
  },
});

export default function RootLayout() {
  const loadFromStorage = useUserStore((s) => s.loadFromStorage);
  const isAuthenticated = useUserStore((s) => s.isAuthenticated);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    loadFromStorage().then(() => setReady(true));
  }, []);

  useEffect(() => {
    if (!ready) return;
    if (!isAuthenticated) {
      router.replace('/login');
    }
  }, [ready, isAuthenticated]);

  return (
    <SafeAreaProvider>
    <QueryClientProvider client={queryClient}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.accent,
          headerTitleStyle: { color: colors.textPrimary, fontWeight: '800' },
          contentStyle: { backgroundColor: colors.bg },
          headerShadowVisible: false,
        }}
      >
        <Stack.Screen
          name="(tabs)"
          options={{ headerShown: false, title: 'Home' }}
        />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="guide" options={{ title: 'Metrics guide', headerBackTitle: 'Back' }} />
      </Stack>
    </QueryClientProvider>
    </SafeAreaProvider>
  );
}
