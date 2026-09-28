import React from 'react';
import { ShieldCheck, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header style={{
      height: 'var(--navbar-height)',
      backgroundColor: 'var(--bg-surface-primary)',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 34,
          height: 34,
          borderRadius: 8,
          background: 'linear-gradient(135deg, var(--primary-500) 0%, var(--accent-cyan) 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'var(--shadow-cyan-glow)'
        }}>
          <ShieldCheck size={20} color="#FFFFFF" />
        </div>
        <div>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontWeight: 700,
            fontSize: '1.2rem',
            letterSpacing: '0.04em',
            color: 'var(--text-main)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            METRIXA
            <span style={{
              fontSize: '0.65rem',
              padding: '2px 6px',
              borderRadius: 4,
              backgroundColor: 'rgba(99, 102, 241, 0.2)',
              color: 'var(--primary-500)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              fontFamily: 'var(--font-mono)',
            }}>
              PCR 2011
            </span>
          </div>
          <div style={{
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            letterSpacing: '0.02em',
            marginTop: -2,
          }}>
            Legal Metrology Inspection Platform
          </div>
        </div>
      </div>

      {/* User Information & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 12px',
              borderRadius: 20,
              backgroundColor: 'var(--bg-surface-secondary)',
              border: '1px solid var(--border-muted)',
            }}>
              <UserIcon size={14} color="var(--accent-cyan)" />
              <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                {user.full_name || user.username}
              </span>
              <span style={{
                fontSize: '0.7rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--accent-cyan)',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                padding: '2px 6px',
                borderRadius: 4,
              }}>
                {user.role}
              </span>
            </div>

            <button
              onClick={logout}
              className="btn btn-outline btn-sm"
              style={{ gap: 6 }}
              title="Sign Out"
            >
              <LogOut size={14} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
