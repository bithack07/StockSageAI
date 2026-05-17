import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { Search } from './pages/Search';
import { StockDetail } from './pages/StockDetail';
import { Portfolio } from './pages/Portfolio';
import { Watchlist } from './pages/Watchlist';
import { Alerts } from './pages/Alerts';
import { Guide } from './pages/Guide';
import { Login } from './pages/Login';
import { useAuthStore } from './store/authStore';
import { AnimatedBackground } from './components/ui/AnimatedBackground';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60_000, retry: 2 } },
});

const NAV_LINKS = [
  { to: '/', label: 'Dashboard', icon: '▦' },
  { to: '/search', label: 'Search', icon: '⌕' },
  { to: '/portfolio', label: 'Portfolio', icon: '◑' },
  { to: '/watchlist', label: 'Watchlist', icon: '◉' },
  { to: '/alerts', label: 'Alerts', icon: '◬' },
  { to: '/guide', label: 'Guide', icon: '◎' },
];

function Sidebar() {
  const { email, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">◈</div>
        <div>
          <div className="sidebar-brand-text">StockSage</div>
          <div className="sidebar-brand-sub">AI · NSE/BSE</div>
        </div>
      </div>

      <div style={{ flex: 1 }}>
        <div className="section-label" style={{ padding: '0 10px' }}>Menu</div>
        {NAV_LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span className="nav-link-icon">{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-user">{email ?? ''}</div>
        <button
          type="button"
          onClick={() => { logout(); navigate('/login'); }}
          className="btn btn-ghost btn-sm"
          style={{ width: '100%' }}
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}

function AppShell() {
  const { token, loadFromStorage } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthed = Boolean(token || localStorage.getItem('ss_token'));

  useEffect(() => { loadFromStorage(); }, []);

  useEffect(() => {
    if (!isAuthed) {
      navigate('/login', { replace: true });
      return;
    }
    if (location.pathname === '/login') navigate('/', { replace: true });
  }, [isAuthed, location.pathname, navigate]);

  if (!isAuthed) return <Login />;

  return (
    <div className="app-shell">
      <AnimatedBackground variant="app" />
      <Sidebar />
      <main className="app-main app-content-layer">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<Search />} />
          <Route path="/stock/:symbol" element={<StockDetail />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/guide" element={<Guide />} />
          <Route path="/login" element={<Login />} />
        </Routes>
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
