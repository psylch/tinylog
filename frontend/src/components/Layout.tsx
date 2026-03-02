import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { clearAdminKey } from '../services/api';

const navLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/files', label: 'Files' },
];

export default function Layout({ needsAuth }: { needsAuth: boolean }) {
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="app-container">
      <header className="header-glass">
        <div className="header-content">
          <div className="flex items-center gap-6">
            <NavLink to="/" className="flex items-center gap-2 font-semibold text-sm" style={{ marginRight: '1rem', letterSpacing: '-0.01em' }}>
              <div
                className="flex justify-center items-center"
                style={{
                  width: '28px', height: '28px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--accent)',
                  boxShadow: '0 2px 8px var(--accent-muted)'
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              TinyLog
            </NavLink>
            <nav className="flex items-center gap-1" style={{ display: 'flex' }}>
              {navLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === '/'}
                  className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="btn btn-ghost"
              style={{ padding: '0.4rem', borderRadius: '50%' }}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" />
                  <line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>
            {needsAuth && (
              <button
                onClick={() => {
                  clearAdminKey();
                  window.location.reload();
                }}
                className="btn btn-secondary text-xs"
                style={{ padding: '0.25rem 0.75rem', borderRadius: '6px' }}
              >
                Logout
              </button>
            )}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="btn btn-ghost"
              style={{ padding: '0.4rem', display: 'none' /* Will show via global css if needed, but for simplicity we rely on native flex */ }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                {mobileMenuOpen ? (
                  <>
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </>
                ) : (
                  <>
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="18" x2="21" y2="18" />
                  </>
                )}
              </svg>
            </button>
          </div>
        </div>
        {mobileMenuOpen && (
          <nav style={{ padding: '0 1.5rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
