import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        backgroundColor: 'var(--bg-canvas)',
        color: 'var(--accent-cyan)',
        fontFamily: 'var(--font-mono)',
        fontSize: '1.1rem'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: 16 }}>INITIALIZING METRIXA SESSION...</div>
          <div style={{
            width: 48,
            height: 48,
            border: '3px solid var(--border-muted)',
            borderTopColor: 'var(--accent-cyan)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto'
          }} />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};
