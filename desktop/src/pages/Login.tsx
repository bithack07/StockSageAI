import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { AnimatedBackground } from '../components/ui/AnimatedBackground';
import { MarketHeroIllustration } from '../components/ui/MarketHeroIllustration';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const FEATURES = [
  { icon: '◈', label: 'Multi-agent AI analysis (Fundamental · Technical · Sentiment)' },
  { icon: '📈', label: 'ML predictions — direction, LSTM & Prophet forecasts' },
  { icon: '⚡', label: 'Real-time streaming insights for NSE / BSE' },
];

export function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError('Enter email and password.'); return; }
    setLoading(true); setError('');
    try {
      const endpoint = isRegister ? '/auth/register' : '/auth/login';
      const { data } = await axios.post(`${API}${endpoint}`, { email: email.trim().toLowerCase(), password });
      setAuth(data.access_token, data.user_id, email.trim().toLowerCase(), data.refresh_token);
      navigate('/', { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? (isRegister ? 'Registration failed.' : 'Invalid credentials.');
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <AnimatedBackground variant="login" />
      <div className="login-layout">
        <div className="login-hero">
          <MarketHeroIllustration className="login-hero-art" />
          <h2 className="login-hero-title">Trade smarter with agentic AI</h2>
          <p className="login-hero-desc">
            StockSage orchestrates specialist agents and ML models to deliver institutional-grade
            analysis for Indian equities — in plain English.
          </p>
          <div className="login-feature-list">
            {FEATURES.map((f) => (
              <div key={f.label} className="login-feature">
                <span className="login-feature-icon">{f.icon}</span>
                {f.label}
              </div>
            ))}
          </div>
        </div>

        <div className="login-card">
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <div className="sidebar-brand-mark" style={{ margin: '0 auto 14px', width: 52, height: 52, fontSize: 24 }}>◈</div>
            <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.5 }}>StockSage AI</h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
              Agentic intelligence for Indian equities
            </p>
          </div>

          <div className="card">
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>
              {isRegister ? 'Create account' : 'Welcome back'}
            </h2>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span className="section-label" style={{ margin: 0 }}>Email</span>
                <input className="input-field" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span className="section-label" style={{ margin: 0 }}>Password</span>
                <input className="input-field" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
              </label>

              {error && (
                <div className="badge badge-red" style={{ padding: '10px 12px', borderRadius: 8, display: 'block', textAlign: 'left' }}>
                  {error}
                </div>
              )}

              <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '13px 20px' }} disabled={loading}>
                {loading ? 'Please wait…' : (isRegister ? 'Create Account' : 'Sign In')}
              </button>
            </form>

            <button
              type="button"
              onClick={() => { setIsRegister((v) => !v); setError(''); }}
              style={{ marginTop: 16, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-2)', fontSize: 13, width: '100%' }}
            >
              {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
