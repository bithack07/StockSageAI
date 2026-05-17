import axios from 'axios';

export const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000';

export const apiClient = axios.create({ baseURL: API, timeout: 30000 });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('ss_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem('ss_refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem('ss_token', data.access_token);
          localStorage.setItem('ss_refresh_token', data.refresh_token);
          if (data.user_id) localStorage.setItem('ss_user_id', data.user_id);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient(original);
        } catch {
          localStorage.removeItem('ss_token');
          localStorage.removeItem('ss_refresh_token');
        }
      }
      localStorage.removeItem('ss_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);
