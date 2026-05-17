import { Platform } from 'react-native';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '@/constants/theme';

const TABS = [
  { name: 'index', title: 'Home', icon: 'home' },
  { name: 'search', title: 'Search', icon: 'search' },
  { name: 'portfolio', title: 'Portfolio', icon: 'pie-chart' },
  { name: 'watchlist', title: 'Watchlist', icon: 'bookmark' },
  { name: 'alerts', title: 'Alerts', icon: 'notifications' },
  { name: 'guide', title: 'Guide', icon: 'book' },
] as const;

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  const tabBarBottom = Math.max(insets.bottom, Platform.OS === 'android' ? 10 : 8);

  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 56 + tabBarBottom,
          paddingBottom: tabBarBottom,
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 10, fontWeight: '700', letterSpacing: 0.2 },
        headerStyle: { backgroundColor: colors.bg },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
        headerTitleStyle: { fontWeight: '800', fontSize: 17, letterSpacing: -0.3 },
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      {TABS.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: tab.name === 'index' ? 'StockSage AI' : tab.title,
            tabBarLabel: tab.title,
            headerTitleAlign: tab.name === 'index' ? 'left' : 'center',
            tabBarIcon: ({ color, size, focused }) => (
              <Ionicons
                name={(focused ? tab.icon : `${tab.icon}-outline`) as keyof typeof Ionicons.glyphMap}
                size={size}
                color={color}
              />
            ),
          }}
        />
      ))}
      <Tabs.Screen
        name="stock"
        options={{
          href: null,
          headerShown: false,
        }}
      />
    </Tabs>
  );
}
