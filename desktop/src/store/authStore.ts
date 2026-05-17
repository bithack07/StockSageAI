import { create } from 'zustand';

function userIdFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.sub ?? null;
  } catch {
    return null;
  }
}

interface AuthState {
  token: string | null;
  userId: string | null;
  email: string | null;
  setAuth: (token: string, userId: string, email: string, refreshToken?: string) => void;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userId: null,
  email: null,

  setAuth: (token, userId, email, refreshToken) => {
    const resolvedUserId = userId || userIdFromToken(token) || '';
    localStorage.setItem('ss_token', token);
    localStorage.setItem('ss_user_id', resolvedUserId);
    localStorage.setItem('ss_email', email);
    if (refreshToken) localStorage.setItem('ss_refresh_token', refreshToken);
    set({ token, userId: resolvedUserId, email });
  },

  logout: () => {
    localStorage.removeItem('ss_token');
    localStorage.removeItem('ss_refresh_token');
    localStorage.removeItem('ss_user_id');
    localStorage.removeItem('ss_email');
    set({ token: null, userId: null, email: null });
  },

  loadFromStorage: () => {
    const token = localStorage.getItem('ss_token');
    if (!token) return;
    const userId = localStorage.getItem('ss_user_id') || userIdFromToken(token);
    const email = localStorage.getItem('ss_email');
    if (userId) set({ token, userId, email });
  },
}));
