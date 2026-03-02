import { useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import LoginGate from './components/LoginGate';
import DashboardPage from './pages/DashboardPage';
import SessionsPage from './pages/SessionsPage';
import FilesPage from './pages/FilesPage';
import { getConfig } from './services/api';

export default function App() {
  const [needsAuth, setNeedsAuth] = useState<boolean | null>(null);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    getConfig()
      .then((cfg) => {
        setNeedsAuth(cfg.needs_auth);
        if (!cfg.needs_auth) {
          setAuthed(true);
        } else {
          // Check if we already have a stored key
          const key = localStorage.getItem('tinylog_admin_key');
          if (key) {
            // Validate the key
            fetch('/api/sessions?page=1&page_size=1', {
              headers: { 'X-Admin-Key': key },
            }).then((res) => {
              if (res.ok) setAuthed(true);
              else localStorage.removeItem('tinylog_admin_key');
            }).catch(() => {
              localStorage.removeItem('tinylog_admin_key');
            });
          }
        }
      })
      .catch(() => {
        // If config fails, assume no auth needed
        setNeedsAuth(false);
        setAuthed(true);
      });
  }, []);

  // Loading state
  if (needsAuth === null) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ backgroundColor: 'var(--bg-base)' }}
      >
        <div className="skeleton h-8 w-32 rounded-md" />
      </div>
    );
  }

  // Auth gate
  if (needsAuth && !authed) {
    return <LoginGate onLogin={() => setAuthed(true)} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout needsAuth={needsAuth} />}>
          <Route index element={<DashboardPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="sessions/:id" element={<SessionsPage />} />
          <Route path="files" element={<FilesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
