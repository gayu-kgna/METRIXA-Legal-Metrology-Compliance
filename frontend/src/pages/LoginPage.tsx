import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldCheck, Lock, User, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  const [username, setUsername] = useState('inspector@metrixa.gov.in');
  const [password, setPassword] = useState('Inspector@123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already authenticated, redirect
  React.useEffect(() => {
    if (isAuthenticated) {
      const origin = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(origin, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please provide both username and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login(username, password);
      const origin = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(origin, { replace: true });
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoCredentials = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'var(--bg-canvas)',
      padding: 20,
    }}>
      <div className="card" style={{
        maxWidth: 440,
        width: '100%',
        padding: 36,
        backgroundColor: 'var(--bg-surface-primary)',
        borderColor: 'var(--border-subtle)',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.8)',
      }}>
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: 'linear-gradient(135deg, var(--primary-500) 0%, var(--accent-cyan) 100%)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-cyan-glow)',
            marginBottom: 16,
          }}>
            <ShieldCheck size={28} color="#FFFFFF" />
          </div>

          <h1 style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '1.6rem',
            fontWeight: 700,
            letterSpacing: '0.04em',
            marginBottom: 4,
          }}>
            METRIXA
          </h1>
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: '0.85rem',
            letterSpacing: '0.02em',
          }}>
            Legal Metrology Statutory Inspection Platform
          </p>
          <div style={{
            display: 'inline-block',
            marginTop: 8,
            fontSize: '0.72rem',
            fontFamily: 'var(--font-mono)',
            padding: '2px 8px',
            backgroundColor: 'rgba(99, 102, 241, 0.15)',
            color: 'var(--accent-cyan)',
            borderRadius: 4,
            border: '1px solid rgba(99, 102, 241, 0.3)',
          }}>
            Packaged Commodities Rules, 2011
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 14px',
            backgroundColor: 'var(--verdict-fail-bg)',
            border: '1px solid var(--verdict-fail-border)',
            borderRadius: 'var(--radius-sm)',
            color: '#FCA5A5',
            fontSize: '0.85rem',
            marginBottom: 20,
          }}>
            <AlertCircle size={16} color="var(--verdict-fail)" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">
              Officer Username / Email
            </label>
            <div style={{ position: 'relative' }}>
              <User size={16} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 12 }} />
              <input
                id="username"
                type="text"
                className="form-input"
                style={{ paddingLeft: 38 }}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Security Password
            </label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 12 }} />
              <input
                id="password"
                type="password"
                className="form-input"
                style={{ paddingLeft: 38 }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg"
            style={{ width: '100%', marginTop: 8 }}
            disabled={loading}
          >
            {loading ? (
              <span>Authenticating Session...</span>
            ) : (
              <>
                <span>Access Inspection Console</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Quick Credentials Helper */}
        <div style={{
          marginTop: 24,
          paddingTop: 18,
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.78rem',
          color: 'var(--text-muted)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--text-secondary)' }}>
            Demo Officer Profiles:
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={() => setDemoCredentials('inspector@metrixa.gov.in', 'Inspector@123')}
              className="btn btn-outline btn-sm"
              style={{ fontSize: '0.75rem', flex: 1 }}
            >
              Field Officer
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('admin@metrixa.gov.in', 'Admin@123')}
              className="btn btn-outline btn-sm"
              style={{ fontSize: '0.75rem', flex: 1 }}
            >
              Senior Admin
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
