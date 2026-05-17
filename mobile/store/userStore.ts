import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

function userIdFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.sub ?? null;
  } catch {
    return null;
  }
}

interface UserState {
  userId: string | null;
  email: string | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (userId: string, email: string, accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  loadFromStorage: () => Promise<void>;
}

export const useUserStore = create<UserState>((set) => ({
  userId: null,
  email: null,
  accessToken: null,
  isAuthenticated: false,

  login: async (userId, email, accessToken, refreshToken) => {
    const resolvedUserId = userId || userIdFromToken(accessToken) || '';
    await AsyncStorage.setItem('access_token', accessToken);
    await AsyncStorage.setItem('refresh_token', refreshToken);
    await AsyncStorage.setItem('user_id', resolvedUserId);
    await AsyncStorage.setItem('user_email', email);
    set({ userId: resolvedUserId, email, accessToken, isAuthenticated: true });
  },

  logout: async () => {
    await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user_id', 'user_email']);
    set({ userId: null, email: null, accessToken: null, isAuthenticated: false });
  },

  loadFromStorage: async () => {
    const accessToken = await AsyncStorage.getItem('access_token');
    const storedUserId = await AsyncStorage.getItem('user_id');
    const userId = storedUserId || (accessToken ? userIdFromToken(accessToken) : null);
    const email = await AsyncStorage.getItem('user_email');
    if (accessToken && userId) {
      set({ accessToken, userId, email, isAuthenticated: true });
    }
  },
}));
