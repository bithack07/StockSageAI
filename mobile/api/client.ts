import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, WS_BASE_URL } from '@/lib/apiConfig';

const API_BASE = API_BASE_URL;
export const WS_BASE = WS_BASE_URL;

/** Encode symbol for URL path (INFY.NS → safe segment for FastAPI) */
export function stockPath(symbol: string): string {
  return encodeURIComponent(decodeURIComponent(symbol.trim()));
}

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT on every request
apiClient.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh token on 401
apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = await AsyncStorage.getItem('refresh_token');
        const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        await AsyncStorage.setItem('access_token', data.access_token);
        await AsyncStorage.setItem('refresh_token', data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(original);
      } catch {
        await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
      }
    }
    return Promise.reject(error);
  },
);

// API functions
export const auth = {
  register: (email: string, password: string) =>
    apiClient.post('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),
};

export const stocks = {
  search: (q: string) => apiClient.get('/stocks/search', { params: { q } }),
  quote: (symbol: string) => apiClient.get(`/stocks/${stockPath(symbol)}/quote`),
  history: (symbol: string, period = '1mo', interval = '1d') =>
    apiClient.get(`/stocks/${stockPath(symbol)}/history`, { params: { period, interval } }),
  latestAnalysis: (symbol: string) =>
    apiClient.get(`/stocks/${stockPath(symbol)}/analysis/latest`),
};

export const portfolio = {
  get: () => apiClient.get('/portfolio'),
  addHolding: (body: { symbol: string; quantity: number; avg_buy_price: number; buy_date?: string }) =>
    apiClient.post('/portfolio', body),
  removeHolding: (holdingId: string) => apiClient.delete(`/portfolio/${holdingId}`),
};

export const watchlist = {
  get: () => apiClient.get('/watchlist'),
  add: (symbol: string) => apiClient.post('/watchlist', { symbol }),
  remove: (id: string) => apiClient.delete(`/watchlist/${id}`),
  refreshPreanalysis: () => apiClient.post('/watchlist/refresh-preanalysis'),
};

export const alerts = {
  list: () => apiClient.get('/alerts'),
  create: (body: { symbol: string; condition: string; threshold?: number }) =>
    apiClient.post('/alerts', body),
  delete: (id: string) => apiClient.delete(`/alerts/${id}`),
};

export const market = {
  overview: (force = false) =>
    apiClient.get('/market/overview', { params: force ? { force: true } : {} }),
};

export const investor = {
  profile: () => apiClient.get('/investor/profile'),
  updateProfile: (body: { net_worth_inr?: number; annual_fd_rate_pct?: number }) =>
    apiClient.patch('/investor/profile', body),
  buffettKit: (symbol: string) => apiClient.get(`/investor/stocks/${stockPath(symbol)}/buffett-kit`),
  portfolioInsights: () => apiClient.get('/investor/portfolio/insights'),
  earningsCalendar: () => apiClient.get('/investor/watchlist/earnings-calendar'),
  saveChecklist: (symbol: string, body: object) =>
    apiClient.put(`/investor/stocks/${stockPath(symbol)}/checklist`, body),
  getThesis: (holdingId: string) => apiClient.get(`/investor/holdings/${holdingId}/thesis`),
  saveThesis: (holdingId: string, body: object) =>
    apiClient.put(`/investor/holdings/${holdingId}/thesis`, body),
};

export const screener = {
  run: (filters: Record<string, number>) =>
    apiClient.get('/screener', { params: filters }),
};

export const analysisHistory = {
  get: (page = 1) => apiClient.get('/analysis/history', { params: { page } }),
};
